# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniAdmissionDecision(models.Model):
    """قرار القبول — القرار الرسمي الصادر بحق طلب القبول.

    يمكن أن يكون: قبول / قبول مشروط / رفض / قائمة انتظار.
    يدعم المنح الدراسية والشروط والموعد النهائي للتسجيل، ويُحرَّر
    في البداية كمسودة ثم يُنهى (finalized) ليُجمَّد ولا يُعدَّل.
    """
    _name = 'uni.admission.decision'
    _description = 'Admission Decision'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'decision_date desc, name'

    name = fields.Char(
        string='Decision Reference', copy=False, readonly=True, index=True,
        default=lambda self: _('New'), tracking=True)
    application_id = fields.Many2one(
        'uni.admission.application', string='Application',
        required=True, ondelete='restrict', tracking=True, index=True)
    applicant_name = fields.Char(
        related='application_id.applicant_name', store=True, index=True)
    program_id = fields.Many2one(
        'uni.program', string='Program',
        related='application_id.program_id', store=True)
    university_id = fields.Many2one(
        'uni.university', string='University',
        related='application_id.university_id', store=True, index=True)

    decision_type = fields.Selection([
        ('accept', 'Accept'),
        ('conditional_accept', 'Conditional Accept'),
        ('reject', 'Reject'),
        ('waitlist', 'Waitlist'),
    ], string='Decision', required=True, default='accept', tracking=True,
        index=True)
    decision_date = fields.Datetime(
        string='Decision Date', default=fields.Datetime.now, tracking=True)
    decided_by = fields.Many2one(
        'res.users', string='Decided By',
        default=lambda self: self.env.user, required=True, tracking=True)

    conditions = fields.Text(
        string='Conditions',
        help='Conditions the applicant must meet (relevant for conditional accept).')
    scholarship_offered = fields.Boolean(
        string='Scholarship Offered', default=False, tracking=True)
    scholarship_amount = fields.Float(
        string='Scholarship Amount', digits=(10, 2), default=0.0, tracking=True)
    scholarship_currency_id = fields.Many2one(
        'res.currency', string='Scholarship Currency',
        default=lambda self: self.env.company.currency_id, tracking=True)
    enrollment_deadline = fields.Date(
        string='Enrollment Deadline', tracking=True,
        help='Last date by which the applicant must complete enrollment.')

    notes = fields.Text(string='Notes')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('finalized', 'Finalized'),
    ], string='State', default='draft', tracking=True, index=True,
        group_expand='_group_expand_states')
    finalized_by = fields.Many2one(
        'res.users', string='Finalized By', readonly=True, copy=False)
    finalized_date = fields.Datetime(
        string='Finalized Date', readonly=True, copy=False)
    color = fields.Integer(string='Color Index')

    _sql_constraints = [
        ('unique_decision_name', 'unique(name)',
         'Decision reference must be unique!'),
        ('unique_decision_per_application',
         'unique(application_id)',
         'An application can have only one decision record!'),
    ]

    # ------------------------------------------------------------------
    # Group expansion
    # ------------------------------------------------------------------
    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in self._fields['state'].selection]

    # ------------------------------------------------------------------
    # Create — auto-sequence
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.admission.decision') or _('DEC-NEW')
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Onchange
    # ------------------------------------------------------------------
    @api.onchange('decision_type')
    def _onchange_decision_type(self):
        """Suggest a sensible default scholarship/conditions behaviour."""
        if self.decision_type == 'reject':
            self.scholarship_offered = False
            self.scholarship_amount = 0.0
        elif self.decision_type == 'conditional_accept' and not self.conditions:
            self.conditions = _('Applicant must submit the missing required documents.')

    @api.onchange('scholarship_offered')
    def _onchange_scholarship_offered(self):
        if not self.scholarship_offered:
            self.scholarship_amount = 0.0

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def action_finalize(self):
        """Freeze the decision and propagate it to the application."""
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError(_(
                    "Only draft decisions can be finalized (current: %(s)s "
                    "for %(n)s).") % {'s': rec.state, 'n': rec.display_name})
            if rec.decision_type == 'conditional_accept' and not rec.conditions:
                raise ValidationError(_(
                    "A conditional accept decision must list its conditions "
                    "(decision %s).") % rec.display_name)
            if rec.scholarship_offered and rec.scholarship_amount <= 0:
                raise ValidationError(_(
                    "Scholarship amount must be greater than zero when a "
                    "scholarship is offered (decision %s).")
                    % rec.display_name)
            rec.write({
                'state': 'finalized',
                'finalized_by': self.env.user.id,
                'finalized_date': fields.Datetime.now(),
            })
            # Propagate to the linked application.
            application = rec.application_id
            if application:
                application.write({'decision_id': rec.id})
                if rec.decision_type in ('accept', 'conditional_accept'):
                    application.action_accept()
                elif rec.decision_type == 'reject':
                    application.action_reject()
                elif rec.decision_type == 'waitlist':
                    application.action_waitlist()
                rec.message_post(body=_(
                    "Decision finalized as '%(dt)s' and propagated to "
                    "application %(ref)s.") % {
                    'dt': dict(self._fields['decision_type']
                               .selection).get(rec.decision_type, rec.decision_type),
                    'ref': application.display_name})

    def action_back_to_draft(self):
        """Reopen a finalized decision (manager override)."""
        for rec in self:
            if rec.state != 'finalized':
                continue
            rec.write({
                'state': 'draft',
                'finalized_by': False,
                'finalized_date': False,
            })
            rec.message_post(body=_("Decision reopened to draft."))

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('scholarship_offered', 'scholarship_amount')
    def _check_scholarship_amount(self):
        for rec in self:
            if rec.scholarship_offered and rec.scholarship_amount <= 0:
                raise ValidationError(_(
                    "Scholarship amount must be greater than zero when a "
                    "scholarship is offered (decision %s).")
                    % rec.display_name)
            if not rec.scholarship_offered and rec.scholarship_amount > 0:
                raise ValidationError(_(
                    "Scholarship amount is set but the scholarship flag is off "
                    "(decision %s).") % rec.display_name)

    @api.constrains('decision_type', 'conditions')
    def _check_conditional_accept_conditions(self):
        for rec in self:
            if rec.decision_type == 'conditional_accept' and not rec.conditions:
                raise ValidationError(_(
                    "A conditional accept decision requires explicit conditions "
                    "(decision %s).") % rec.display_name)
