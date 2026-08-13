# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniResearchGrant(models.Model):
    """المنحة البحثية — تموّل واحدًا أو أكثر من المشاريع البحثية.

    سير العمل:
        ``draft`` → ``applied`` → ``awarded`` → ``active`` → ``closed``
                                          ↘ ``rejected``

    يتم احتساب المبلغ المتبقي تلقائيًا بطرح مجموع موازنات المشاريع المرتبطة
    من إجمالي مبلغ المنحة.
    """
    _name = 'uni.research.grant'
    _description = 'Research Grant'
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
        help='Optional funding agency grant code (e.g. NSF-2024-001).')
    title = fields.Char(
        string='Title', required=True, translate=True, tracking=True,
        help='Title of the grant / funded programme.')

    # ------------------------------------------------------------------
    # Funding agency
    # ------------------------------------------------------------------
    funding_agency = fields.Char(
        string='Funding Agency', tracking=True,
        help='Organisation funding the grant (e.g. NSF, DFG, KACST).')
    funding_agency_country_id = fields.Many2one(
        'res.country', string='Funding Country', ondelete='restrict',
        tracking=True)
    grant_type = fields.Selection([
        ('government', 'Government'),
        ('private', 'Private'),
        ('internal', 'Internal'),
        ('international', 'International'),
        ('corporate', 'Corporate'),
    ], string='Grant Type', default='government', tracking=True, index=True)

    # ------------------------------------------------------------------
    # Principal investigator & amounts
    # ------------------------------------------------------------------
    principal_investigator_id = fields.Many2one(
        'uni.faculty', string='Principal Investigator',
        ondelete='restrict', tracking=True, index=True)
    amount = fields.Float(
        string='Grant Amount', required=True, tracking=True,
        digits=(16, 2), help='Total awarded amount of the grant.')
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
        ondelete='restrict', tracking=True, required=True)
    amount_allocated = fields.Float(
        compute='_compute_allocated', string='Allocated Amount',
        digits=(16, 2), store=True,
        help='Sum of budget of linked research projects.')
    amount_remaining = fields.Float(
        compute='_compute_remaining', string='Remaining Amount',
        digits=(16, 2), store=True,
        help='Grant amount minus the allocated amount.')

    # ------------------------------------------------------------------
    # Dates
    # ------------------------------------------------------------------
    application_date = fields.Date(string='Application Date', tracking=True)
    award_date = fields.Date(string='Award Date', tracking=True)
    start_date = fields.Date(string='Start Date', tracking=True)
    end_date = fields.Date(string='End Date', tracking=True)
    duration_months = fields.Integer(
        compute='_compute_duration', string='Duration (Months)',
        store=True, help='Number of months between start and end dates.')

    # ------------------------------------------------------------------
    # Description
    # ------------------------------------------------------------------
    description = fields.Text(string='Description', translate=True)
    conditions = fields.Text(
        string='Conditions', translate=True,
        help='Terms & conditions imposed by the funding agency.')
    notes = fields.Text(string='Notes')

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------
    state = fields.Selection([
        ('draft', 'Draft'),
        ('applied', 'Applied'),
        ('awarded', 'Awarded'),
        ('active', 'Active'),
        ('closed', 'Closed'),
        ('rejected', 'Rejected'),
    ], string='State', default='draft', tracking=True, index=True,
        group_expand='_group_expand_states')

    # ------------------------------------------------------------------
    # Relations
    # ------------------------------------------------------------------
    project_ids = fields.One2many(
        'uni.research.project', 'grant_id', string='Funded Projects')
    project_count = fields.Integer(
        compute='_compute_project_count', string='Projects')

    _sql_constraints = [
        ('unique_grant_name', 'unique(name)',
         'Grant reference must be unique!'),
        ('check_grant_amount_positive', 'check(amount >= 0)',
         'Grant amount cannot be negative!'),
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
                    'uni.research.grant') or _('RSG-NEW')
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Computed — allocated, remaining, duration
    # ------------------------------------------------------------------
    @api.depends('project_ids.budget', 'project_ids.active')
    def _compute_allocated(self):
        for rec in self:
            rec.amount_allocated = sum(
                p.budget for p in rec.project_ids.filtered('active'))

    @api.depends('amount', 'amount_allocated')
    def _compute_remaining(self):
        for rec in self:
            rec.amount_remaining = rec.amount - rec.amount_allocated

    @api.depends('start_date', 'end_date')
    def _compute_duration(self):
        for rec in self:
            if rec.start_date and rec.end_date and rec.end_date >= rec.start_date:
                # Approximate month delta using 30.4375 days per month
                delta_days = (rec.end_date - rec.start_date).days
                rec.duration_months = int(round(delta_days / 30.4375))
            else:
                rec.duration_months = 0

    @api.depends('project_ids')
    def _compute_project_count(self):
        for rec in self:
            rec.project_count = len(rec.project_ids)

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_apply(self):
        """Submit the grant application."""
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError(_(
                    "Only draft grants can be applied (current: %(state)s).")
                    % {'state': rec.state})
            if not rec.application_date:
                rec.application_date = fields.Date.context_today(rec)
            rec.state = 'applied'
            rec.message_post(body=_('Grant application submitted on %s.')
                             % rec.application_date)

    def action_award(self):
        """Mark the grant as awarded by the funding agency."""
        for rec in self:
            if rec.state != 'applied':
                raise ValidationError(_(
                    "Only applied grants can be awarded (current: %(state)s).")
                    % {'state': rec.state})
            if not rec.award_date:
                rec.award_date = fields.Date.context_today(rec)
            rec.state = 'awarded'
            rec.message_post(body=_('Grant awarded on %s.') % rec.award_date)

    def action_activate(self):
        """Activate the awarded grant — usually after signing the agreement."""
        for rec in self:
            if rec.state != 'awarded':
                raise ValidationError(_(
                    "Only awarded grants can be activated (current: %(state)s).")
                    % {'state': rec.state})
            if not rec.start_date:
                rec.start_date = fields.Date.context_today(rec)
            rec.state = 'active'
            rec.message_post(body=_('Grant activated.'))

    def action_close(self):
        """Close the active grant."""
        for rec in self:
            if rec.state != 'active':
                raise ValidationError(_(
                    "Only active grants can be closed (current: %(state)s).")
                    % {'state': rec.state})
            if not rec.end_date:
                rec.end_date = fields.Date.context_today(rec)
            rec.state = 'closed'
            rec.message_post(body=_('Grant closed on %s.') % rec.end_date)

    def action_reject(self):
        """Reject the grant application."""
        for rec in self:
            if rec.state not in ('applied', 'awarded'):
                raise ValidationError(_(
                    "Only applied or awarded grants can be rejected (current: %(state)s).")
                    % {'state': rec.state})
            rec.state = 'rejected'
            rec.message_post(body=_('Grant rejected.'))

    def action_draft(self):
        """Reset a rejected grant back to draft."""
        for rec in self:
            if rec.state != 'rejected':
                raise ValidationError(_(
                    "Only rejected grants can be reset to draft (current: %(state)s).")
                    % {'state': rec.state})
            rec.state = 'draft'
            rec.message_post(body=_('Grant reset to draft.'))

    # ------------------------------------------------------------------
    # Smart button
    # ------------------------------------------------------------------
    def action_view_projects(self):
        """Open the research projects funded by this grant."""
        self.ensure_one()
        return {
            'name': _('Funded Projects'),
            'type': 'ir.actions.act_window',
            'res_model': 'uni.research.project',
            'view_mode': 'list,form',
            'domain': [('grant_id', '=', self.id)],
            'context': {'default_grant_id': self.id,
                        'default_principal_investigator_id': self.principal_investigator_id.id},
        }

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for rec in self:
            if rec.start_date and rec.end_date and rec.end_date < rec.start_date:
                raise ValidationError(_(
                    "Grant end date cannot be earlier than start date (%s).")
                    % rec.display_name)

    @api.constrains('application_date', 'award_date', 'start_date')
    def _check_milestone_dates(self):
        """Award date must not predate application; start date must not predate award."""
        for rec in self:
            if rec.application_date and rec.award_date and \
                    rec.award_date < rec.application_date:
                raise ValidationError(_(
                    "Award date cannot be earlier than application date for grant '%s'.")
                    % rec.display_name)
            if rec.award_date and rec.start_date and \
                    rec.start_date < rec.award_date:
                raise ValidationError(_(
                    "Grant start date cannot be earlier than award date for grant '%s'.")
                    % rec.display_name)

    @api.constrains('amount', 'amount_allocated')
    def _check_allocation_within_amount(self):
        """Warn (not block) — the sum of project budgets may legitimately exceed
        the grant only when extra co-funding exists. We block only when the
        allocated amount clearly exceeds the grant by more than the grant
        itself (i.e. > 200% allocation with no headroom)."""
        for rec in self:
            if rec.amount and rec.amount_allocated > rec.amount * 2:
                raise ValidationError(_(
                    "Allocated amount (%(alloc).2f) for grant '%(g)s' exceeds "
                    "200%% of the grant amount (%(amt).2f). "
                    "Please review the linked projects' budgets.")
                    % {'alloc': rec.amount_allocated,
                       'g': rec.display_name,
                       'amt': rec.amount})
