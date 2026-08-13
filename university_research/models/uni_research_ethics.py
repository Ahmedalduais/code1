# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniResearchEthics(models.Model):
    """طلب اعتماد لجنة الأخلاقيات البحثية.

    يربط كل طلب بمشروع بحثي ويخزّن معلومات حول الأشخاص الخاضعين للبحث،
    المواد البيولوجية، مستوى المخاطر، الإجراءات المتعلقة بالموافقة،
    وأعضاء لجنة المراجعة، إضافة إلى القرار النهائي.

    سير العمل:
        ``draft`` → ``submitted`` → ``under_review`` → ``decided`` → ``closed``
                                              ↘ (approved / conditional_approval / rejected)
    """
    _name = 'uni.research.ethics'
    _description = 'Research Ethics Approval'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'application_date desc, name'

    # ------------------------------------------------------------------
    # Identity & sequence
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True, index=True,
        default=lambda self: _('New'), tracking=True)
    code = fields.Char(
        string='Code', copy=False, index=True, tracking=True,
        help='Optional committee reference code.')

    # ------------------------------------------------------------------
    # Project link
    # ------------------------------------------------------------------
    project_id = fields.Many2one(
        'uni.research.project', string='Research Project', required=True,
        ondelete='restrict', tracking=True, index=True)
    faculty_id = fields.Many2one(
        related='project_id.principal_investigator_id',
        string='Principal Investigator', store=True, readonly=True, index=True)

    # ------------------------------------------------------------------
    # Application timeline
    # ------------------------------------------------------------------
    application_date = fields.Date(
        string='Application Date', default=fields.Date.context_today,
        tracking=True)
    review_date = fields.Date(string='Review Date', tracking=True)
    decision_date = fields.Date(string='Decision Date', tracking=True)
    submission_type = fields.Selection([
        ('new', 'New'),
        ('amendment', 'Amendment'),
        ('renewal', 'Renewal'),
    ], string='Submission Type', default='new', tracking=True, index=True)

    # ------------------------------------------------------------------
    # Research summary
    # ------------------------------------------------------------------
    research_summary = fields.Text(
        string='Research Summary', translate=True,
        help='Short description of the research and methodology used.')

    # ------------------------------------------------------------------
    # Subjects & materials
    # ------------------------------------------------------------------
    human_subjects = fields.Boolean(
        string='Human Subjects', default=False, tracking=True,
        help='True if the research involves human participants.')
    animal_subjects = fields.Boolean(
        string='Animal Subjects', default=False, tracking=True,
        help='True if the research involves animal subjects.')
    biological_materials = fields.Boolean(
        string='Biological Materials', default=False, tracking=True,
        help='True if the research involves biological samples/materials.')

    # ------------------------------------------------------------------
    # Risk & consent
    # ------------------------------------------------------------------
    risk_level = fields.Selection([
        ('minimal', 'Minimal'),
        ('low', 'Low'),
        ('moderate', 'Moderate'),
        ('high', 'High'),
    ], string='Risk Level', default='minimal', tracking=True, index=True)
    risk_description = fields.Text(
        string='Risk Description', translate=True,
        help='Description of the identified risks and mitigation measures.')
    consent_required = fields.Boolean(
        string='Consent Required', default=False, tracking=True,
        help='True if informed consent from participants is required.')
    consent_description = fields.Text(
        string='Consent Description', translate=True,
        help='How informed consent is obtained and documented.')

    # ------------------------------------------------------------------
    # Review committee
    # ------------------------------------------------------------------
    review_committee_members = fields.Many2many(
        'uni.faculty', string='Review Committee Members',
        relation='uni_research_ethics_committee_rel',
        column1='ethics_id', column2='faculty_id',
        help='Faculty members reviewing this ethics application.')
    committee_member_count = fields.Integer(
        compute='_compute_committee_member_count', string='Members')

    # ------------------------------------------------------------------
    # Decision
    # ------------------------------------------------------------------
    decision = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('conditional_approval', 'Conditional Approval'),
        ('rejected', 'Rejected'),
    ], string='Decision', default='pending', tracking=True, index=True)
    conditions = fields.Text(
        string='Conditions', translate=True,
        help='Conditions imposed when decision is conditional approval.')
    approval_expiry_date = fields.Date(
        string='Approval Expiry Date', tracking=True,
        help='Date after which the approval is no longer valid.')

    # ------------------------------------------------------------------
    # Attachment
    # ------------------------------------------------------------------
    file = fields.Binary(string='Attachment', attachment=True)
    filename = fields.Char(string='Filename')

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('decided', 'Decided'),
        ('closed', 'Closed'),
    ], string='State', default='draft', tracking=True, index=True,
        group_expand='_group_expand_states')
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('unique_ethics_name', 'unique(name)',
         'Ethics reference must be unique!'),
    ]

    # ------------------------------------------------------------------
    # Group expand helper
    # ------------------------------------------------------------------
    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in self._fields['state'].selection]

    # ------------------------------------------------------------------
    # Sequence on create
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.research.ethics') or _('RET-NEW')
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Computed
    # ------------------------------------------------------------------
    @api.depends('review_committee_members')
    def _compute_committee_member_count(self):
        for rec in self:
            rec.committee_member_count = len(rec.review_committee_members)

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_submit(self):
        """Submit the ethics application for committee review."""
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError(_(
                    "Only draft ethics applications can be submitted (current: %(state)s).")
                    % {'state': rec.state})
            if not rec.research_summary:
                raise ValidationError(_(
                    "Research summary is required before submitting ethics '%s'.")
                    % rec.display_name)
            rec.state = 'submitted'
            rec.decision = 'pending'
            rec.message_post(body=_('Ethics application submitted.'))

    def action_review(self):
        """Start committee review of the submitted application."""
        for rec in self:
            if rec.state != 'submitted':
                raise ValidationError(_(
                    "Only submitted ethics applications can enter review (current: %(state)s).")
                    % {'state': rec.state})
            if not rec.review_committee_members:
                raise ValidationError(_(
                    "Cannot start review for ethics '%s' without committee members.")
                    % rec.display_name)
            if not rec.review_date:
                rec.review_date = fields.Date.context_today(rec)
            rec.state = 'under_review'
            rec.message_post(body=_('Ethics application is now under review.'))

    def action_approve(self):
        """Issue a full approval decision."""
        for rec in self:
            if rec.state != 'under_review':
                raise ValidationError(_(
                    "Only applications under review can be approved (current: %(state)s).")
                    % {'state': rec.state})
            rec.decision = 'approved'
            rec.decision_date = fields.Date.context_today(rec)
            rec.state = 'decided'
            rec.message_post(body=_('Ethics application fully approved.'))

    def action_conditional_approve(self):
        """Issue a conditional approval — requires conditions text."""
        for rec in self:
            if rec.state != 'under_review':
                raise ValidationError(_(
                    "Only applications under review can be conditionally approved (current: %(state)s).")
                    % {'state': rec.state})
            if not rec.conditions:
                raise ValidationError(_(
                    "Conditional approval requires specifying the conditions for ethics '%s'.")
                    % rec.display_name)
            rec.decision = 'conditional_approval'
            rec.decision_date = fields.Date.context_today(rec)
            rec.state = 'decided'
            rec.message_post(body=_('Ethics application conditionally approved.'))

    def action_reject(self):
        """Reject the ethics application."""
        for rec in self:
            if rec.state != 'under_review':
                raise ValidationError(_(
                    "Only applications under review can be rejected (current: %(state)s).")
                    % {'state': rec.state})
            rec.decision = 'rejected'
            rec.decision_date = fields.Date.context_today(rec)
            rec.state = 'decided'
            rec.message_post(body=_('Ethics application rejected.'))

    def action_close(self):
        """Close the decided ethics case (after project completion/expiry)."""
        for rec in self:
            if rec.state != 'decided':
                raise ValidationError(_(
                    "Only decided ethics applications can be closed (current: %(state)s).")
                    % {'state': rec.state})
            rec.state = 'closed'
            rec.message_post(body=_('Ethics case closed.'))

    def action_back_to_draft(self):
        """Reset a submitted/under_review ethics application back to draft."""
        for rec in self:
            if rec.state not in ('submitted', 'under_review'):
                raise ValidationError(_(
                    "Cannot reset ethics '%s' to draft from state '%s'.")
                    % (rec.display_name, rec.state))
            rec.state = 'draft'
            rec.review_date = False
            rec.message_post(body=_('Ethics application reset to draft.'))

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('consent_required', 'human_subjects')
    def _check_consent_for_human_subjects(self):
        """If human subjects are involved, consent should typically be required."""
        for rec in self:
            if rec.human_subjects and not rec.consent_required:
                raise ValidationError(_(
                    "Consent is required when human subjects are involved "
                    "in ethics application '%s'.") % rec.display_name)

    @api.constrains('risk_level', 'risk_description')
    def _check_high_risk_description(self):
        """High or moderate risk applications must include a risk description."""
        for rec in self:
            if rec.risk_level in ('moderate', 'high') and not rec.risk_description:
                raise ValidationError(_(
                    "A risk description is mandatory for %(lvl)s-risk ethics "
                    "applications ('%(name)s').")
                    % {'lvl': rec.risk_level, 'name': rec.display_name})

    @api.constrains('decision_date', 'application_date')
    def _check_decision_after_application(self):
        """Decision date cannot predate the application date."""
        for rec in self:
            if rec.decision_date and rec.application_date and \
                    rec.decision_date < rec.application_date:
                raise ValidationError(_(
                    "Decision date cannot be earlier than application date for '%s'.")
                    % rec.display_name)

    @api.constrains('approval_expiry_date', 'decision_date')
    def _check_expiry_after_decision(self):
        """Approval expiry date (if set) must be after the decision date."""
        for rec in self:
            if rec.approval_expiry_date and rec.decision_date and \
                    rec.approval_expiry_date < rec.decision_date:
                raise ValidationError(_(
                    "Approval expiry date cannot be earlier than decision date for '%s'.")
                    % rec.display_name)
