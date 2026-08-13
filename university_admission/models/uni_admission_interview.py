# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniAdmissionInterview(models.Model):
    """مقابلة القبول — جلسة تقييم بين المتقدم والمُقابِل.

    يتم جدولتها كجزء من دورة حياة طلب القبول وتسجّل فيها التفاصيل
    اللوجستية (التاريخ، الوقت، المكان أو رابط الاجتماع) ثم تقييم
    المُقابِل وتوصيته النهائية (strong_accept → strong_reject).

    ملاحظة: المُقابِل مخزّن كـ ``Char`` وليس ``Many2one`` إلى ``uni.faculty``
    حتى لا تعتمد الوحدة على ``university_faculty`` (المواصفات تعتمد فقط على
    ``university_core`` و ``university_student``).
    """
    _name = 'uni.admission.interview'
    _description = 'Admission Interview'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'interview_date desc'

    name = fields.Char(
        string='Reference', copy=False, readonly=True, index=True,
        default=lambda self: _('New'), tracking=True)
    application_id = fields.Many2one(
        'uni.admission.application', string='Application',
        required=True, ondelete='cascade', tracking=True, index=True)
    applicant_name = fields.Char(
        related='application_id.applicant_name', store=True, index=True)
    university_id = fields.Many2one(
        'uni.university', string='University',
        related='application_id.university_id', store=True, index=True)
    program_id = fields.Many2one(
        'uni.program', string='Program',
        related='application_id.program_id', store=True)

    interviewer_name = fields.Char(
        string='Interviewer Name', required=True, tracking=True, index=True,
        help='Name of the person conducting the interview. Stored as plain '
             'text to avoid a hard dependency on university_faculty.')
    interview_date = fields.Date(
        string='Interview Date', required=True, tracking=True,
        default=fields.Date.context_today)
    start_time = fields.Float(
        string='Start Time', default=9.0, tracking=True,
        help='Start time in decimal hours (e.g. 9.5 = 09:30).')
    end_time = fields.Float(
        string='End Time', default=10.0, tracking=True,
        help='End time in decimal hours (e.g. 10.5 = 10:30).')

    location = fields.Char(string='Location', tracking=True)
    is_online = fields.Boolean(
        string='Online', default=False, tracking=True,
        help='Check if the interview will be held online.')
    meeting_url = fields.Char(
        string='Meeting URL', tracking=True,
        help='URL of the online meeting (Zoom, Teams, Google Meet...).')

    state = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ], string='State', default='scheduled', tracking=True, index=True,
        group_expand='_group_expand_states')

    score = fields.Float(
        string='Score', digits=(5, 2), default=0.0, tracking=True,
        help='Raw score given by the interviewer.')
    score_max = fields.Float(
        string='Max Score', digits=(5, 2), default=100.0, tracking=True,
        help='Maximum possible score for this interview.')
    score_percentage = fields.Float(
        string='Score %', digits=(5, 2),
        compute='_compute_score_percentage', store=True,
        help='Score expressed as a percentage of the maximum.')

    recommendation = fields.Selection([
        ('strong_accept', 'Strong Accept'),
        ('accept', 'Accept'),
        ('neutral', 'Neutral'),
        ('reject', 'Reject'),
        ('strong_reject', 'Strong Reject'),
    ], string='Recommendation', tracking=True)

    notes = fields.Text(string='Notes')
    color = fields.Integer(string='Color Index')

    _sql_constraints = [
        ('unique_interview_name', 'unique(name)',
         'Interview reference must be unique!'),
    ]

    # ------------------------------------------------------------------
    # Group expansion
    # ------------------------------------------------------------------
    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in self._fields['state'].selection]

    # ------------------------------------------------------------------
    # Computed
    # ------------------------------------------------------------------
    @api.depends('score', 'score_max')
    def _compute_score_percentage(self):
        for rec in self:
            if rec.score_max and rec.score_max > 0:
                rec.score_percentage = (rec.score or 0.0) * 100.0 / rec.score_max
            else:
                rec.score_percentage = 0.0

    # ------------------------------------------------------------------
    # Create — auto-sequence the interview reference
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.admission.interview') or _('INT-NEW')
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Onchange
    # ------------------------------------------------------------------
    @api.onchange('is_online')
    def _onchange_is_online(self):
        """Clear location when switching to online-only (and vice versa)."""
        if self.is_online and not self.meeting_url:
            self.location = False
        elif not self.is_online:
            self.meeting_url = False

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_complete(self):
        """Mark the interview as completed."""
        for rec in self:
            if rec.state != 'scheduled':
                raise ValidationError(_(
                    "Only scheduled interviews can be completed "
                    "(current: %(s)s for %(n)s).") % {
                    's': rec.state, 'n': rec.display_name})
            rec.state = 'completed'
            rec.message_post(body=_(
                "Interview completed. Score: %(score)s/%(max)s (%(pct).2f%%).") % {
                'score': rec.score or 0.0,
                'max': rec.score_max,
                'pct': rec.score_percentage,
            })

    def action_cancel(self):
        """Cancel the interview."""
        for rec in self:
            if rec.state in ('completed',):
                raise ValidationError(_(
                    "Cannot cancel a completed interview (%s).")
                    % rec.display_name)
            rec.state = 'cancelled'
            rec.message_post(body=_("Interview cancelled."))

    def action_no_show(self):
        """Record that the applicant did not show up."""
        for rec in self:
            if rec.state != 'scheduled':
                raise ValidationError(_(
                    "Only scheduled interviews can be marked 'No Show' "
                    "(current: %(s)s for %(n)s).") % {
                    's': rec.state, 'n': rec.display_name})
            rec.state = 'no_show'
            rec.message_post(body=_("Applicant did not show up."))

    def action_reschedule(self):
        """Reset back to Scheduled so the user can edit date/time."""
        for rec in self:
            if rec.state not in ('cancelled', 'no_show'):
                raise ValidationError(_(
                    "Only cancelled or no-show interviews can be rescheduled "
                    "(current: %(s)s for %(n)s).") % {
                    's': rec.state, 'n': rec.display_name})
            rec.state = 'scheduled'
            rec.message_post(body=_("Interview rescheduled."))

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('start_time', 'end_time')
    def _check_times(self):
        for rec in self:
            if not (0.0 <= rec.start_time <= 24.0):
                raise ValidationError(_(
                    "Start time must be between 0 and 24 (got %(t)s for %(n)s).")
                    % {'t': rec.start_time, 'n': rec.display_name})
            if not (0.0 <= rec.end_time <= 24.0):
                raise ValidationError(_(
                    "End time must be between 0 and 24 (got %(t)s for %(n)s).")
                    % {'t': rec.end_time, 'n': rec.display_name})
            if rec.end_time <= rec.start_time:
                raise ValidationError(_(
                    "End time (%(e)s) must be later than start time (%(s)s) "
                    "for interview %(n)s.") % {
                    'e': rec.end_time, 's': rec.start_time,
                    'n': rec.display_name})

    @api.constrains('score', 'score_max')
    def _check_score_range(self):
        for rec in self:
            if rec.score_max <= 0:
                raise ValidationError(_(
                    "Maximum score must be greater than 0 (interview %s).")
                    % rec.display_name)
            if rec.score < 0:
                raise ValidationError(_(
                    "Score cannot be negative (interview %s).")
                    % rec.display_name)
            if rec.score > rec.score_max:
                raise ValidationError(_(
                    "Score (%(s)s) cannot exceed the maximum (%(m)s) for "
                    "interview %(n)s.") % {
                    's': rec.score, 'm': rec.score_max,
                    'n': rec.display_name})

    @api.constrains('is_online', 'meeting_url')
    def _check_online_has_url(self):
        for rec in self:
            if rec.is_online and not rec.meeting_url:
                raise ValidationError(_(
                    "An online interview must have a meeting URL (%s).")
                    % rec.display_name)
