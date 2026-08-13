# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniResearchProject(models.Model):
    """المشروع البحثي — يمثّل مشروعاً علمياً يديره باحث رئيسي (PI).

    سير العمل:
        ``proposal`` → ``submitted`` → ``approved`` → ``active`` → ``completed``
                                   ↘ ``cancelled``
                                       ↘ ``suspended`` ↔ ``active``

    يربط المشروع بعضو هيئة التدريس (PI)، مشاركين مشاركين، منحة بحثية اختيارية،
    طلب اعتماد أخلاقيات اختياري، وقائمة بالمنشورات الناتجة.
    """
    _name = 'uni.research.project'
    _description = 'Research Project'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'start_date desc, name'

    # ------------------------------------------------------------------
    # Identity & sequence
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True, index=True,
        default=lambda self: _('New'), tracking=True)
    code = fields.Char(
        string='Code', copy=False, index=True, tracking=True,
        help='Optional internal code for the project (e.g. PRJ-2024-001).')
    title = fields.Char(
        string='Title', required=True, translate=True, tracking=True,
        help='Full title of the research project.')

    # ------------------------------------------------------------------
    # Investigators
    # ------------------------------------------------------------------
    principal_investigator_id = fields.Many2one(
        'uni.faculty', string='Principal Investigator', required=True,
        ondelete='restrict', tracking=True, index=True)
    co_investigator_ids = fields.Many2many(
        'uni.faculty', string='Co-Investigators',
        relation='uni_research_project_coinvest_rel',
        column1='project_id', column2='faculty_id',
        help='Other faculty members collaborating on the project.')

    # ------------------------------------------------------------------
    # Hierarchy (derived from PI)
    # ------------------------------------------------------------------
    university_id = fields.Many2one(
        related='principal_investigator_id.university_id',
        string='University', store=True, readonly=True, index=True)
    college_id = fields.Many2one(
        related='principal_investigator_id.college_id',
        string='College', store=True, readonly=True, index=True)
    department_id = fields.Many2one(
        related='principal_investigator_id.department_id',
        string='Department', store=True, readonly=True, index=True)

    # ------------------------------------------------------------------
    # Project metadata
    # ------------------------------------------------------------------
    project_type = fields.Selection([
        ('fundamental', 'Fundamental'),
        ('applied', 'Applied'),
        ('developmental', 'Developmental'),
        ('experimental', 'Experimental'),
    ], string='Project Type', default='applied', tracking=True, index=True)
    research_area = fields.Char(
        string='Research Area', tracking=True,
        help='Domain or field of research (e.g. AI in Healthcare).')
    keywords = fields.Char(
        string='Keywords', tracking=True,
        help='Comma-separated keywords describing the research.')

    # ------------------------------------------------------------------
    # Scientific content
    # ------------------------------------------------------------------
    abstract = fields.Text(string='Abstract', translate=True)
    methodology = fields.Text(string='Methodology', translate=True)
    expected_outcomes = fields.Text(string='Expected Outcomes', translate=True)

    # ------------------------------------------------------------------
    # Dates & duration
    # ------------------------------------------------------------------
    start_date = fields.Date(string='Start Date', tracking=True)
    end_date = fields.Date(string='End Date', tracking=True)
    duration_months = fields.Integer(
        compute='_compute_duration', string='Duration (Months)',
        store=True, help='Number of months between start and end dates.')

    # ------------------------------------------------------------------
    # Budget
    # ------------------------------------------------------------------
    budget = fields.Float(
        string='Budget', digits=(16, 2), tracking=True,
        help='Allocated budget for this project (in selected currency).')
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
        ondelete='restrict', tracking=True)

    # ------------------------------------------------------------------
    # Links to grant & ethics
    # ------------------------------------------------------------------
    grant_id = fields.Many2one(
        'uni.research.grant', string='Funding Grant',
        ondelete='restrict', tracking=True, index=True,
        help='Grant funding this project (optional).')
    ethics_approval_id = fields.Many2one(
        'uni.research.ethics', string='Ethics Approval',
        ondelete='restrict', tracking=True, index=True,
        help='Ethics committee approval tied to this project (optional).')

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------
    state = fields.Selection([
        ('proposal', 'Proposal'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('suspended', 'Suspended'),
        ('cancelled', 'Cancelled'),
    ], string='State', default='proposal', tracking=True, index=True,
        group_expand='_group_expand_states')
    notes = fields.Text(string='Notes')

    # ------------------------------------------------------------------
    # Publications
    # ------------------------------------------------------------------
    publication_ids = fields.One2many(
        'uni.research.publication', 'project_id', string='Publications')
    publication_count = fields.Integer(
        compute='_compute_publication_count', string='Publications')

    _sql_constraints = [
        ('unique_project_name', 'unique(name)',
         'Project reference must be unique!'),
        ('check_project_budget_positive', 'check(budget >= 0)',
         'Project budget cannot be negative!'),
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
                    'uni.research.project') or _('RSP-NEW')
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Computed
    # ------------------------------------------------------------------
    @api.depends('start_date', 'end_date')
    def _compute_duration(self):
        for rec in self:
            if rec.start_date and rec.end_date and rec.end_date >= rec.start_date:
                delta_days = (rec.end_date - rec.start_date).days
                rec.duration_months = int(round(delta_days / 30.4375))
            else:
                rec.duration_months = 0

    @api.depends('publication_ids')
    def _compute_publication_count(self):
        for rec in self:
            rec.publication_count = len(rec.publication_ids)

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_submit(self):
        """Submit the project proposal for review."""
        for rec in self:
            if rec.state != 'proposal':
                raise ValidationError(_(
                    "Only proposals can be submitted (current: %(state)s).")
                    % {'state': rec.state})
            if not rec.abstract:
                raise ValidationError(_(
                    "Project '%s' must have an abstract before submission.")
                    % rec.display_name)
            rec.state = 'submitted'
            rec.message_post(body=_('Project proposal submitted.'))

    def action_approve(self):
        """Approve the submitted project."""
        for rec in self:
            if rec.state != 'submitted':
                raise ValidationError(_(
                    "Only submitted projects can be approved (current: %(state)s).")
                    % {'state': rec.state})
            rec.state = 'approved'
            rec.message_post(body=_('Project approved.'))

    def action_start(self):
        """Start an approved project."""
        for rec in self:
            if rec.state != 'approved':
                raise ValidationError(_(
                    "Only approved projects can be started (current: %(state)s).")
                    % {'state': rec.state})
            if not rec.start_date:
                rec.start_date = fields.Date.context_today(rec)
            rec.state = 'active'
            rec.message_post(body=_('Project activated on %s.') % rec.start_date)

    def action_complete(self):
        """Mark the active project as completed."""
        for rec in self:
            if rec.state != 'active':
                raise ValidationError(_(
                    "Only active projects can be completed (current: %(state)s).")
                    % {'state': rec.state})
            if not rec.end_date:
                rec.end_date = fields.Date.context_today(rec)
            rec.state = 'completed'
            rec.message_post(body=_('Project completed on %s.') % rec.end_date)

    def action_suspend(self):
        """Suspend the active project."""
        for rec in self:
            if rec.state != 'active':
                raise ValidationError(_(
                    "Only active projects can be suspended (current: %(state)s).")
                    % {'state': rec.state})
            rec.state = 'suspended'
            rec.message_post(body=_('Project suspended.'))

    def action_resume(self):
        """Resume a suspended project back to active."""
        for rec in self:
            if rec.state != 'suspended':
                raise ValidationError(_(
                    "Only suspended projects can be resumed (current: %(state)s).")
                    % {'state': rec.state})
            rec.state = 'active'
            rec.message_post(body=_('Project resumed.'))

    def action_cancel(self):
        """Cancel the project."""
        for rec in self:
            if rec.state == 'completed':
                raise ValidationError(_(
                    "Cannot cancel a completed project ('%s').") % rec.display_name)
            rec.state = 'cancelled'
            rec.message_post(body=_('Project cancelled.'))

    def action_back_to_proposal(self):
        """Reset a submitted project back to proposal for rework."""
        for rec in self:
            if rec.state != 'submitted':
                raise ValidationError(_(
                    "Only submitted projects can be reset to proposal (current: %(state)s).")
                    % {'state': rec.state})
            rec.state = 'proposal'
            rec.message_post(body=_('Project reset to proposal for rework.'))

    # ------------------------------------------------------------------
    # Smart buttons
    # ------------------------------------------------------------------
    def action_view_publications(self):
        """Open the publications produced by this project."""
        self.ensure_one()
        return {
            'name': _('Publications'),
            'type': 'ir.actions.act_window',
            'res_model': 'uni.research.publication',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id,
                        'default_faculty_id': self.principal_investigator_id.id},
        }

    def action_open_ethics(self):
        """Open the ethics approval linked to this project (if any)."""
        self.ensure_one()
        if not self.ethics_approval_id:
            return {
                'name': _('Ethics Approval'),
                'type': 'ir.actions.act_window',
                'res_model': 'uni.research.ethics',
                'view_mode': 'list,form',
                'domain': [('project_id', '=', self.id)],
                'context': {'default_project_id': self.id},
            }
        return {
            'name': _('Ethics Approval'),
            'type': 'ir.actions.act_window',
            'res_model': 'uni.research.ethics',
            'res_id': self.ethics_approval_id.id,
            'view_mode': 'form',
        }

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for rec in self:
            if rec.start_date and rec.end_date and rec.end_date < rec.start_date:
                raise ValidationError(_(
                    "Project end date cannot be earlier than start date ('%s').")
                    % rec.display_name)

    @api.constrains('principal_investigator_id', 'co_investigator_ids')
    def _check_pi_not_in_co_investigators(self):
        """PI cannot simultaneously be a co-investigator on the same project."""
        for rec in self:
            if rec.principal_investigator_id and \
                    rec.principal_investigator_id in rec.co_investigator_ids:
                raise ValidationError(_(
                    "Principal investigator '%s' cannot also be listed as a "
                    "co-investigator on project '%s'.")
                    % (rec.principal_investigator_id.display_name, rec.display_name))

    @api.constrains('state', 'start_date')
    def _check_active_has_start_date(self):
        """Active or completed projects must have a start date."""
        for rec in self:
            if rec.state in ('active', 'completed', 'suspended') and not rec.start_date:
                raise ValidationError(_(
                    "Project '%s' in state '%s' must have a start date.")
                    % (rec.display_name, rec.state))

    @api.constrains('grant_id', 'principal_investigator_id')
    def _check_grant_pi_consistency(self):
        """If linked to a grant, recommend (soft check) that the PI matches
        the grant's PI. We block only when both are set and differ."""
        for rec in self:
            if rec.grant_id and rec.grant_id.principal_investigator_id and \
                    rec.principal_investigator_id and \
                    rec.grant_id.principal_investigator_id.id != \
                    rec.principal_investigator_id.id:
                raise ValidationError(_(
                    "Project '%(proj)s' is funded by grant '%(grant)s' whose PI "
                    "is '%(g_pi)s' — project PI must match the grant's PI.")
                    % {'proj': rec.display_name,
                       'grant': rec.grant_id.display_name,
                       'g_pi': rec.grant_id.principal_investigator_id.display_name})

    @api.constrains('ethics_approval_id')
    def _check_ethics_project_link(self):
        """Ensure the linked ethics record points back to this project."""
        for rec in self:
            if rec.ethics_approval_id and \
                    rec.ethics_approval_id.project_id.id != rec.id:
                raise ValidationError(_(
                    "Linked ethics approval '%s' does not reference this project.")
                    % rec.ethics_approval_id.display_name)
