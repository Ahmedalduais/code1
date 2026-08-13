# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class UniFacultyContract(models.Model):
    """عقد عضو هيئة التدريس — يدير دورة حياة العقد التعاقدي.

    يشمل أنواع العقود المختلفة (دوام كامل، جزئي، زائر، مسار الترقية،
    متعاقد مستقل...), مع تتبّع الراتب، تكرار الدفع، العبء التدريسي/البحثي/
    الإداري، المزايا، الشروط، الوثائق الموقّعة، وسير عمل الموافقة:
        draft → submitted → approved → active → expired/terminated
                                          ↘ renewed (ينشئ عقداً جديداً)
    """
    _name = 'uni.faculty.contract'
    _description = 'Faculty Contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'faculty_id, start_date desc'

    # ------------------------------------------------------------------
    # Identity & linkage
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Contract Reference', required=True, copy=False, readonly=True,
        default=lambda self: _('New'), index=True)
    faculty_id = fields.Many2one(
        'uni.faculty', string='Faculty Member', required=True,
        ondelete='cascade', tracking=True, index=True)
    faculty_name = fields.Char(
        related='faculty_id.name', string='Faculty Name',
        store=True, readonly=True)

    contract_type = fields.Selection([
        ('full_time', 'Full-Time'),
        ('part_time', 'Part-Time'),
        ('visiting', 'Visiting Professor'),
        ('adjunct', 'Adjunct Professor'),
        ('research', 'Research-Only'),
        ('tenure_track', 'Tenure Track'),
        ('tenured', 'Tenured'),
        ('contractor', 'Independent Contractor'),
        ('exchange', 'Exchange Faculty'),
    ], string='Contract Type', required=True, tracking=True)

    # ------------------------------------------------------------------
    # Organizational context
    # ------------------------------------------------------------------
    university_id = fields.Many2one(
        'uni.university', string='University', required=True,
        ondelete='restrict', tracking=True, index=True)
    college_id = fields.Many2one(
        'uni.college', string='College', ondelete='restrict', tracking=True)
    department_id = fields.Many2one(
        'uni.department', string='Department',
        ondelete='restrict', tracking=True)

    # ------------------------------------------------------------------
    # Dates & duration
    # ------------------------------------------------------------------
    start_date = fields.Date(string='Start Date', required=True, tracking=True)
    end_date = fields.Date(
        string='End Date', tracking=True,
        help='Leave empty for indefinite contracts (e.g., tenured).')
    renewal_date = fields.Date(
        string='Renewal Date', tracking=True,
        help='Date by which the contract must be renewed.')
    notice_period_days = fields.Integer(
        string='Notice Period (Days)', default=30)

    # ------------------------------------------------------------------
    # Compensation
    # ------------------------------------------------------------------
    salary = fields.Float(
        string='Annual Salary', digits=(12, 2), tracking=True)
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id)
    payment_frequency = fields.Selection([
        ('monthly', 'Monthly'),
        ('bi_weekly', 'Bi-Weekly'),
        ('quarterly', 'Quarterly'),
        ('annual', 'Annual'),
        ('per_course', 'Per Course'),
    ], string='Payment Frequency', default='monthly', tracking=True)

    # ------------------------------------------------------------------
    # Workload
    # ------------------------------------------------------------------
    teaching_load_hours = fields.Float(
        string='Teaching Load (Hours/Week)', default=12, tracking=True)
    research_load_hours = fields.Float(
        string='Research Load (Hours/Week)', default=6, tracking=True)
    admin_load_hours = fields.Float(
        string='Admin Load (Hours/Week)', default=2, tracking=True)

    # ------------------------------------------------------------------
    # Terms & documents
    # ------------------------------------------------------------------
    benefits = fields.Text(string='Benefits')
    terms_conditions = fields.Html(string='Terms and Conditions')

    contract_file = fields.Binary(string='Contract Document')
    contract_filename = fields.Char(string='Document Filename')

    # ------------------------------------------------------------------
    # Sign-off workflow
    # ------------------------------------------------------------------
    signed_date = fields.Date(string='Signed Date', tracking=True)
    signed_by = fields.Many2one(
        'res.users', string='Signed By', tracking=True)
    approved_by = fields.Many2one(
        'res.users', string='Approved By', tracking=True)
    approved_date = fields.Date(string='Approved Date', tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('terminated', 'Terminated'),
        ('renewed', 'Renewed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True,
        group_expand='_group_expand_states')

    termination_reason = fields.Text(string='Termination Reason')
    termination_date = fields.Date(string='Termination Date')

    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_contract_reference', 'unique(name)',
         'Contract reference must be unique!'),
        ('check_dates', 'check(end_date is null or end_date >= start_date)',
         'End date must be after start date!'),
        ('check_salary_positive', 'check(salary >= 0)',
         'Salary must be positive!'),
    ]

    # ------------------------------------------------------------------
    # Group expansion helper
    # ------------------------------------------------------------------
    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in states]

    # ------------------------------------------------------------------
    # Create — auto-generate reference via ir.sequence
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.faculty.contract') or _('New')
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_submit(self):
        for rec in self:
            rec.state = 'submitted'

    def action_approve(self):
        for rec in self:
            rec.write({
                'state': 'approved',
                'approved_by': self.env.uid,
                'approved_date': fields.Date.context_today(self),
            })

    def action_activate(self):
        for rec in self:
            rec.state = 'active'

    def action_terminate(self):
        for rec in self:
            rec.write({
                'state': 'terminated',
                'termination_date': fields.Date.context_today(self),
            })

    def action_expire(self):
        for rec in self:
            rec.state = 'expired'

    def action_renew(self):
        """Create a new contract based on this one."""
        self.ensure_one()
        new_contract = self.copy({
            'name': _('New'),
            'state': 'draft',
            'start_date': self.end_date or fields.Date.context_today(self),
            'end_date': False,
            'signed_date': False,
            'signed_by': False,
            'approved_by': False,
            'approved_date': False,
        })
        self.state = 'renewed'
        return {
            'type': 'ir.actions.act_window',
            'name': _('Renewed Contract'),
            'res_model': 'uni.faculty.contract',
            'res_id': new_contract.id,
            'view_mode': 'form',
        }

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'

    # ------------------------------------------------------------------
    # Onchange — pre-fill university/college/department from faculty
    # ------------------------------------------------------------------
    @api.onchange('faculty_id')
    def _onchange_faculty_id(self):
        if self.faculty_id:
            if not self.university_id:
                self.university_id = self.faculty_id.university_id
            if not self.college_id:
                self.college_id = self.faculty_id.college_id
            if not self.department_id:
                self.department_id = self.faculty_id.department_id
