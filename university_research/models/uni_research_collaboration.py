# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniResearchCollaboration(models.Model):
    """التعاون البحثي — تتبّع تعاون الباحثين الداخليين والشركاء الخارجيين
    على مشروع بحثي محدد.

    يدعم النموذج أنواعًا متعددة من التعاون:
        * داخلي (نفس الجامعة — عبر ``uni.faculty``)
        * خارجي (مؤسسة أخرى — يُسجَّل كـ ``Char`` للاسم/المؤسسة/القسم/...)
        * مؤسسي / دولي / صناعي / حكومي / NGOs

    سير العمل:
        ``draft`` → ``proposed`` → ``active`` → ``completed``
                                 ↘ ``suspended`` ↔ ``active``
                                       ↘ ``terminated`` / ``cancelled``
    """
    _name = 'uni.research.collaboration'
    _description = 'Research Collaboration'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'project_id, start_date desc'

    # ------------------------------------------------------------------
    # Identity & sequence
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True,
        default=lambda self: _('New'), index=True, tracking=True,
        help='Auto-generated reference for the collaboration (RCL/...).')

    # ------------------------------------------------------------------
    # Project link
    # ------------------------------------------------------------------
    project_id = fields.Many2one(
        'uni.research.project', string='Research Project',
        required=True, ondelete='cascade', tracking=True, index=True)
    project_title = fields.Char(
        related='project_id.title', string='Project Title',
        store=True, readonly=True)

    # ------------------------------------------------------------------
    # Internal collaborator (faculty member)
    # ------------------------------------------------------------------
    faculty_id = fields.Many2one(
        'uni.faculty', string='Internal Collaborator',
        ondelete='restrict', tracking=True, index=True,
        help='Internal faculty member representing the collaboration on '
             'our side. Leave empty if the collaboration is purely external.')

    collaborator_type = fields.Selection([
        ('internal', 'Internal (Same University)'),
        ('external', 'External (Other Institution)'),
        ('institutional', 'Institutional Partnership'),
        ('international', 'International Collaboration'),
        ('industry', 'Industry Partner'),
        ('government', 'Government Agency'),
        ('ngo', 'NGO / Non-Profit'),
    ], string='Collaborator Type', required=True, tracking=True,
        default='external', index=True)

    # ------------------------------------------------------------------
    # Collaborator info (Char fields for external collaborators)
    # ------------------------------------------------------------------
    collaborator_name = fields.Char(
        string='Collaborator Name', required=True, tracking=True,
        help='Full name of the collaborator or organization.')
    collaborator_organization = fields.Char(
        string='Organization', tracking=True)
    collaborator_department = fields.Char(
        string='Department', tracking=True)
    collaborator_position = fields.Char(
        string='Position/Title', tracking=True)
    collaborator_email = fields.Char(
        string='Email', tracking=True)
    collaborator_phone = fields.Char(
        string='Phone', tracking=True)
    collaborator_country_id = fields.Many2one(
        'res.country', string='Country', ondelete='restrict', tracking=True)
    collaborator_website = fields.Char(
        string='Website', tracking=True)

    # ------------------------------------------------------------------
    # Collaboration details
    # ------------------------------------------------------------------
    collaboration_role = fields.Selection([
        ('co_investigator', 'Co-Investigator'),
        ('co_author', 'Co-Author'),
        ('consultant', 'Consultant'),
        ('advisor', 'Technical Advisor'),
        ('data_provider', 'Data Provider'),
        ('equipment_provider', 'Equipment Provider'),
        ('funding_provider', 'Funding Provider'),
        ('research_partner', 'Research Partner'),
        ('other', 'Other'),
    ], string='Collaboration Role', required=True, tracking=True,
        default='research_partner', index=True)
    collaboration_scope = fields.Text(
        string='Collaboration Scope',
        help='Description of what the collaboration entails.')
    expected_outcomes = fields.Text(string='Expected Outcomes')
    contributions = fields.Text(
        string='Collaborator Contributions',
        help='What the collaborator brings to the project.')

    # ------------------------------------------------------------------
    # Timeline
    # ------------------------------------------------------------------
    start_date = fields.Date(
        string='Start Date', required=True,
        default=fields.Date.context_today, tracking=True, index=True)
    end_date = fields.Date(string='End Date', tracking=True, index=True)
    is_active = fields.Boolean(
        string='Currently Active', default=True, tracking=True)

    # ------------------------------------------------------------------
    # Agreement
    # ------------------------------------------------------------------
    has_agreement = fields.Boolean(
        string='Has Written Agreement', default=False, tracking=True)
    agreement_type = fields.Selection([
        ('moa', 'Memorandum of Agreement (MOA)'),
        ('mou', 'Memorandum of Understanding (MOU)'),
        ('nda', 'Non-Disclosure Agreement (NDA)'),
        ('contract', 'Research Contract'),
        ('consortium', 'Consortium Agreement'),
        ('informal', 'Informal Agreement'),
    ], string='Agreement Type', tracking=True, index=True)
    agreement_date = fields.Date(string='Agreement Date', tracking=True)
    agreement_file = fields.Binary(
        string='Agreement Document', attachment=True)
    agreement_filename = fields.Char(string='Agreement Filename')

    # ------------------------------------------------------------------
    # Financial
    # ------------------------------------------------------------------
    funding_amount = fields.Float(
        string='Collaborator Funding Amount', digits=(12, 2), tracking=True,
        help='Funding contributed by the collaborator (if any).')
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
        ondelete='restrict')

    # ------------------------------------------------------------------
    # State & notes
    # ------------------------------------------------------------------
    state = fields.Selection([
        ('draft', 'Draft'),
        ('proposed', 'Proposed'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('completed', 'Completed'),
        ('terminated', 'Terminated'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, index=True,
        group_expand='_group_expand_states')
    termination_reason = fields.Text(string='Termination Reason')
    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_collaboration_reference', 'unique(name)',
         'Collaboration reference must be unique!'),
        ('check_dates', 'check(end_date is null or end_date >= start_date)',
         'End date must be after start date!'),
        ('check_funding_positive', 'check(funding_amount >= 0)',
         'Funding amount must be positive!'),
    ]

    # ------------------------------------------------------------------
    # Group expand helper
    # ------------------------------------------------------------------
    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in self._fields['state'].selection]

    # ------------------------------------------------------------------
    # Create — auto-generate reference from ir.sequence
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.research.collaboration') or _('RCL-NEW')
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_propose(self):
        """Move the collaboration from draft to proposed."""
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError(_(
                    "Only draft collaborations can be proposed (current: %(state)s).")
                    % {'state': rec.state})
            rec.state = 'proposed'
            rec.message_post(body=_('Collaboration proposed.'))

    def action_activate(self):
        """Activate the collaboration."""
        for rec in self:
            if rec.state not in ('proposed', 'suspended'):
                raise ValidationError(_(
                    "Only proposed or suspended collaborations can be activated "
                    "(current: %(state)s).") % {'state': rec.state})
            rec.write({
                'state': 'active',
                'is_active': True,
            })
            rec.message_post(body=_('Collaboration activated.'))

    def action_suspend(self):
        """Suspend an active collaboration."""
        for rec in self:
            if rec.state != 'active':
                raise ValidationError(_(
                    "Only active collaborations can be suspended (current: %(state)s).")
                    % {'state': rec.state})
            rec.write({
                'state': 'suspended',
                'is_active': False,
            })
            rec.message_post(body=_('Collaboration suspended.'))

    def action_complete(self):
        """Mark the collaboration as completed — sets end_date if missing."""
        for rec in self:
            if rec.state not in ('active', 'suspended'):
                raise ValidationError(_(
                    "Only active or suspended collaborations can be completed "
                    "(current: %(state)s).") % {'state': rec.state})
            rec.write({
                'state': 'completed',
                'is_active': False,
                'end_date': rec.end_date or fields.Date.context_today(self),
            })
            rec.message_post(body=_('Collaboration completed.'))

    def action_terminate(self):
        """Terminate the collaboration — requires a termination reason."""
        for rec in self:
            if rec.state not in ('active', 'suspended'):
                raise ValidationError(_(
                    "Only active or suspended collaborations can be terminated "
                    "(current: %(state)s).") % {'state': rec.state})
            if not rec.termination_reason:
                raise ValidationError(_(
                    "Cannot terminate collaboration '%s' without a termination reason.")
                    % rec.display_name)
            rec.write({
                'state': 'terminated',
                'is_active': False,
                'end_date': rec.end_date or fields.Date.context_today(self),
            })
            rec.message_post(body=_('Collaboration terminated.'))

    def action_cancel(self):
        """Cancel the collaboration (before activation)."""
        for rec in self:
            if rec.state in ('completed', 'terminated', 'cancelled'):
                raise ValidationError(_(
                    "Cannot cancel a collaboration that is already %(state)s.")
                    % {'state': rec.state})
            rec.write({
                'state': 'cancelled',
                'is_active': False,
            })
            rec.message_post(body=_('Collaboration cancelled.'))

    def action_reset_to_draft(self):
        """Reset a cancelled collaboration back to draft."""
        for rec in self:
            if rec.state != 'cancelled':
                raise ValidationError(_(
                    "Only cancelled collaborations can be reset to draft."))
            rec.state = 'draft'
            rec.message_post(body=_('Collaboration reset to draft.'))

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        """End date must not predate start date."""
        for rec in self:
            if rec.start_date and rec.end_date and rec.end_date < rec.start_date:
                raise ValidationError(_(
                    "Collaboration end date cannot be earlier than start date (%s).")
                    % rec.display_name)

    @api.constrains('has_agreement', 'agreement_type')
    def _check_agreement_type(self):
        """If a written agreement exists, an agreement type should be set."""
        for rec in self:
            if rec.has_agreement and not rec.agreement_type:
                raise ValidationError(_(
                    "Collaboration '%s' has a written agreement but no agreement type.")
                    % rec.display_name)

    @api.constrains('collaborator_type', 'faculty_id')
    def _check_internal_collaborator(self):
        """Internal collaborations should reference a faculty member."""
        for rec in self:
            if rec.collaborator_type == 'internal' and not rec.faculty_id:
                raise ValidationError(_(
                    "Internal collaboration '%s' must reference a faculty member.")
                    % rec.display_name)
