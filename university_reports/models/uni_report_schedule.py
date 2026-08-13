# -*- coding: utf-8 -*-
import logging
from datetime import timedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)

# Mapping of frequency → relativedelta kwargs (used to advance next_run_date)
_FREQUENCY_DELTAS = {
    'daily': {'days': 1},
    'weekly': {'days': 7},
    'monthly': {'months': 1},
    'quarterly': {'months': 3},
    'annual': {'years': 1},
}


class UniReportSchedule(models.Model):
    """جدولة التقارير — تشغيل منشئ التقارير بشكل دوري.

    سير العمل:
        draft → active → paused
                  ↘ cancelled

    عند ``action_activate()`` يتم:
        * حساب ``next_run_date`` (الآن إذا لم يكن مُعيناً)
        * ربط ``is_scheduled=True`` على الـ builder المرتبط
        * تحويل الحالة إلى ``active``

    الكرون ``uni.report.schedule._scheduler_cron`` يستدعى يومياً من
    ``data/cron_data.xml`` ويبحث عن كل الجداول النشطة التي حان موعد تشغيلها،
    ينفّذ ``builder.action_run()`` ثم يُرسل البريد ويحدّث ``next_run_date``.
    """
    _name = 'uni.report.schedule'
    _description = 'University Report Schedule'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'next_run_date, id'

    # ------------------------------------------------------------------
    # Identity / sequence
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Reference', copy=False, readonly=True, index=True,
        default='New', tracking=True,
        help='Auto-generated reference identifying this schedule.')
    code = fields.Char(
        string='Code', copy=False, tracking=True, index=True,
        help='Optional human-friendly code for this schedule.')

    # ------------------------------------------------------------------
    # Links
    # ------------------------------------------------------------------
    report_builder_id = fields.Many2one(
        'uni.report.builder', string='Report Builder',
        required=True, ondelete='cascade', tracking=True, index=True)

    # ------------------------------------------------------------------
    # Schedule
    # ------------------------------------------------------------------
    frequency = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annual', 'Annual'),
        ('custom', 'Custom'),
    ], string='Frequency', required=True, default='monthly',
        tracking=True, index=True, group_expand='_group_expand_frequencies')
    custom_cron_expression = fields.Char(
        string='Custom Cron Expression',
        tracking=True,
        help='Optional cron expression (e.g. "0 2 * * 1") used when '
             'frequency is "Custom". Interpreted best-effort.')
    next_run_date = fields.Datetime(
        string='Next Run Date', tracking=True, index=True,
        help='Date and time at which the schedule should next execute.')
    last_run_date = fields.Datetime(
        string='Last Run Date', readonly=True, tracking=True,
        help='Date and time of the last successful execution.')
    run_count = fields.Integer(
        string='Run Count', default=0, readonly=True,
        help='Total number of executions performed by this schedule.')

    # ------------------------------------------------------------------
    # Recipients & email
    # ------------------------------------------------------------------
    recipient_ids = fields.Many2many(
        'res.users', string='Recipients',
        help='Users that should receive the report output by email.')
    email_subject = fields.Char(
        string='Email Subject', tracking=True,
        help='Optional custom subject for the notification email. '
             'Defaults to "<Builder name> — Report".')
    email_body = fields.Text(
        string='Email Body', tracking=True,
        help='Optional custom body for the notification email.')

    # ------------------------------------------------------------------
    # Behaviour flags
    # ------------------------------------------------------------------
    is_active = fields.Boolean(
        string='Active', default=True, tracking=True,
        help='If unchecked, the schedule will be skipped by the cron '
             'even if its ``state`` is ``active``.')
    send_email = fields.Boolean(
        string='Send Email', default=True, tracking=True,
        help='Whether to email the result file to recipients after each run.')
    save_to_file = fields.Boolean(
        string='Save to File', default=True, tracking=True,
        help='Whether to attach the result file to the builder after each run.')

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, index=True,
        group_expand='_group_expand_states')
    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True, tracking=True)

    # ------------------------------------------------------------------
    # Group expand
    # ------------------------------------------------------------------
    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in self._fields['state'].selection]

    def _group_expand_frequencies(self, states, domain, order):
        return [key for key, _ in self._fields['frequency'].selection]

    # ------------------------------------------------------------------
    # Create — auto-generate reference & code
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.report.schedule') or _('RSC-NEW')
            if not vals.get('code'):
                vals['code'] = vals['name']
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    @api.constrains('frequency', 'custom_cron_expression')
    def _check_custom_cron_expression(self):
        for rec in self:
            if rec.frequency == 'custom' and not rec.custom_cron_expression:
                raise ValidationError(_(
                    "Schedule '%s' uses Custom frequency but no cron "
                    "expression was provided.") % rec.display_name)

    @api.constrains('state', 'report_builder_id')
    def _check_builder_for_active(self):
        for rec in self:
            if rec.state == 'active' and not rec.report_builder_id:
                raise ValidationError(_(
                    "Schedule '%s' cannot be activated without a builder.")
                    % rec.display_name)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _compute_next_run(self, base_datetime=None):
        """Compute the next run date based on the frequency.

        For custom cron expressions, advances by 1 day as a safe default
        (full cron parsing is delegated to the cron job itself).
        """
        self.ensure_one()
        base = base_datetime or fields.Datetime.now()
        if self.frequency == 'custom':
            # Best-effort: advance by 1 day when custom cron is used.
            return base + timedelta(days=1)
        delta_kwargs = _FREQUENCY_DELTAS.get(self.frequency, {'days': 1})
        # Use add_deltas via fields.Datetime
        from dateutil.relativedelta import relativedelta
        return base + relativedelta(**delta_kwargs)

    def _send_notification_email(self, attachment_ids=None):
        """Send the notification email to ``recipient_ids``."""
        self.ensure_one()
        if not self.recipient_ids:
            return False
        if not self.send_email:
            return False
        if not self.report_builder_id.saved_result:
            return False
        subject = self.email_subject or _('%s — Report') % \
            (self.report_builder_id.name_custom or
             self.report_builder_id.name)
        body = self.email_body or _(
            "Hello,\n\nPlease find attached the report '%s' generated on %s."
            "\n\nBest regards,\nUniversity Reporting System") % (
            self.report_builder_id.name_custom or self.report_builder_id.name,
            fields.Datetime.now().strftime('%Y-%m-%d %H:%M'),
        )
        # Build attachment record for the saved result
        attachment = self.env['ir.attachment'].create({
            'name': self.report_builder_id.saved_result_filename or 'report.bin',
            'datas': self.report_builder_id.saved_result,
            'res_model': 'uni.report.builder',
            'res_id': self.report_builder_id.id,
        })
        mail_values = {
            'subject': subject,
            'body_html': '<pre>%s</pre>' % body,
            'email_to': ','.join(
                self.recipient_ids.mapped('email_formatted')),
            'attachment_ids': [(6, 0, [attachment.id])],
            'auto_delete': False,
        }
        mail = self.env['mail.mail'].sudo().create(mail_values)
        mail.send()
        return True

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_activate(self):
        """Activate the schedule — compute next_run_date and mark builder."""
        for rec in self:
            if rec.state not in ('draft', 'paused'):
                raise UserError(_(
                    "Schedule '%s' cannot be activated from state '%s'.")
                    % (rec.display_name, rec.state))
            if not rec.report_builder_id:
                raise UserError(_(
                    "Schedule '%s' has no builder to activate.") %
                    rec.display_name)
            if not rec.next_run_date:
                rec.next_run_date = rec._compute_next_run()
            rec.state = 'active'
            rec.is_active = True
            rec.report_builder_id.is_scheduled = True
            rec.report_builder_id.schedule_id = rec.id
            rec.message_post(body=_(
                "Schedule activated by %s. Next run: %s.") % (
                self.env.user.name, rec.next_run_date))

    def action_pause(self):
        """Pause the schedule — keep next_run_date unchanged."""
        for rec in self:
            if rec.state != 'active':
                raise UserError(_(
                    "Only active schedules can be paused (%s).")
                    % rec.display_name)
            rec.state = 'paused'
            if rec.report_builder_id:
                rec.report_builder_id.is_scheduled = False
            rec.message_post(body=_("Schedule paused by %s.")
                             % self.env.user.name)

    def action_cancel(self):
        """Cancel the schedule — requires re-creation to reactivate."""
        for rec in self:
            if rec.state == 'cancelled':
                continue
            rec.state = 'cancelled'
            if rec.report_builder_id:
                rec.report_builder_id.is_scheduled = False
            rec.message_post(body=_("Schedule cancelled by %s.")
                             % self.env.user.name)

    def action_draft(self):
        """Reset the schedule to draft."""
        for rec in self:
            if rec.state == 'active':
                raise UserError(_(
                    "Cannot reset an active schedule to draft (%s). "
                    "Pause or cancel it first.") % rec.display_name)
            rec.state = 'draft'

    def action_run_now(self):
        """Run the builder immediately, ignoring next_run_date."""
        for rec in self:
            if not rec.report_builder_id:
                raise UserError(_(
                    "Schedule '%s' has no builder to run.") %
                    rec.display_name)
            _logger.info("Running schedule %s manually", rec.display_name)
            rec.report_builder_id.action_run()
            rec.last_run_date = fields.Datetime.now()
            rec.run_count = (rec.run_count or 0) + 1
            if rec.send_email:
                rec._send_notification_email()
            if rec.state == 'active':
                rec.next_run_date = rec._compute_next_run()
            rec.message_post(body=_(
                "Manual execution completed — %s row(s). Result file: %s")
                % (rec.report_builder_id.result_count,
                   rec.report_builder_id.saved_result_filename or _('(none)')))
        return True

    # ------------------------------------------------------------------
    # Cron entry-point
    # ------------------------------------------------------------------
    @api.model
    def _scheduler_cron(self):
        """Cron entry-point — find all active schedules whose ``next_run_date``
        has been reached and execute them.

        This is called daily by the cron record defined in
        ``data/cron_data.xml``.
        """
        now = fields.Datetime.now()
        schedules = self.search([
            ('state', '=', 'active'),
            ('is_active', '=', True),
            ('next_run_date', '<=', now),
        ])
        _logger.info("Report scheduler: %d schedule(s) due", len(schedules))
        for sched in schedules:
            try:
                builder = sched.report_builder_id
                if not builder:
                    _logger.warning(
                        "Schedule %s has no builder; skipping.",
                        sched.display_name)
                    continue
                builder.action_run()
                sched.last_run_date = fields.Datetime.now()
                sched.run_count = (sched.run_count or 0) + 1
                if sched.send_email:
                    sched._send_notification_email()
                sched.next_run_date = sched._compute_next_run()
            except Exception as exc:
                _logger.exception(
                    "Schedule %s failed during cron execution: %s",
                    sched.display_name, exc)
                sched.message_post(body=_(
                    "Scheduled execution failed: %s") % exc)
                # Advance next_run_date so the cron doesn't retry
                # the same schedule every minute.
                sched.next_run_date = sched._compute_next_run()
        return True
