# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class UniInternshipOpportunity(models.Model):
    _name = 'uni.internship.opportunity'
    _description = 'Internship Opportunity'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_date desc'

    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True,
        default=lambda self: _('New'), index=True)
    title = fields.Char(
        string='Opportunity Title', required=True, tracking=True)
    entity_id = fields.Many2one(
        'uni.internship.training.entity', string='Training Entity',
        required=True, ondelete='restrict', tracking=True, index=True)

    university_id = fields.Many2one(
        'uni.university', string='University', required=True,
        ondelete='restrict', tracking=True)
    college_id = fields.Many2one(
        'uni.college', string='College', ondelete='restrict', tracking=True)
    department_id = fields.Many2one(
        'uni.department', string='Target Department',
        ondelete='restrict', tracking=True)
    program_id = fields.Many2one(
        'uni.program', string='Target Program', ondelete='restrict')

    description = fields.Text(string='Description', required=True)
    requirements = fields.Text(string='Requirements')
    responsibilities = fields.Text(string='Responsibilities')
    learning_outcomes = fields.Text(string='Learning Outcomes')

    start_date = fields.Date(string='Start Date', required=True, tracking=True)
    end_date = fields.Date(string='End Date', required=True, tracking=True)
    duration_weeks = fields.Integer(
        compute='_compute_duration', string='Duration (Weeks)', store=True)

    hours_required = fields.Integer(
        string='Required Hours', default=240, tracking=True)
    hours_per_week = fields.Integer(
        string='Hours per Week', default=20, tracking=True)

    max_students = fields.Integer(
        string='Max Students', default=5, tracking=True)
    min_students = fields.Integer(
        string='Min Students', default=1, tracking=True)
    current_applications = fields.Integer(
        compute='_compute_applications', string='Applications')
    accepted_count = fields.Integer(
        compute='_compute_applications', string='Accepted')

    is_paid = fields.Boolean(
        string='Paid Internship', default=False, tracking=True)
    monthly_stipend = fields.Float(
        string='Monthly Stipend', digits=(12, 2), tracking=True)
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id)

    location = fields.Char(string='Location')
    is_remote = fields.Boolean(
        string='Remote/Online', default=False, tracking=True)

    skill_ids = fields.One2many(
        'uni.internship.opportunity.skill', 'opportunity_id',
        string='Required Skills')

    application_deadline = fields.Date(
        string='Application Deadline', tracking=True)

    status = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Open for Applications'),
        ('closed', 'Applications Closed'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True,
        group_expand='_group_expand_states')

    is_active = fields.Boolean(string='Active', default=True, tracking=True)
    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_opportunity_reference', 'unique(name)',
         'Opportunity reference must be unique!'),
        ('check_dates', 'check(end_date >= start_date)',
         'End date must be after start date!'),
        ('check_max_min', 'check(max_students >= min_students)',
         'Max must be >= min students!'),
    ]

    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in states]

    @api.depends('start_date', 'end_date')
    def _compute_duration(self):
        for rec in self:
            if rec.start_date and rec.end_date:
                rec.duration_weeks = max(
                    1, (rec.end_date - rec.start_date).days // 7)
            else:
                rec.duration_weeks = 0

    @api.depends('name')
    def _compute_applications(self):
        Application = self.env['uni.internship.application']
        for rec in self:
            apps = Application.search([('opportunity_id', '=', rec.id)])
            rec.current_applications = len(apps)
            rec.accepted_count = len(
                apps.filtered(lambda a: a.status == 'accepted'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.internship.opportunity') or _('New')
        return super().create(vals_list)

    def action_open(self):
        for rec in self:
            rec.status = 'open'

    def action_close(self):
        for rec in self:
            rec.status = 'closed'

    def action_ongoing(self):
        for rec in self:
            rec.status = 'ongoing'

    def action_complete(self):
        for rec in self:
            rec.status = 'completed'

    def action_cancel(self):
        for rec in self:
            rec.status = 'cancelled'

    def action_draft(self):
        for rec in self:
            rec.status = 'draft'
