# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class UniInternshipTrainingEntity(models.Model):
    _name = 'uni.internship.training.entity'
    _inherit = 'res.partner'
    _description = 'Training Entity (Company/Organization)'
    _order = 'name'

    # Inherited from res.partner: name, phone, email, website, street, city,
    # country_id, etc.

    entity_code = fields.Char(
        string='Entity Code', required=True, copy=False, index=True, tracking=True)
    entity_type = fields.Selection([
        ('private', 'Private Company'),
        ('government', 'Government Entity'),
        ('non_profit', 'Non-Profit Organization'),
        ('educational', 'Educational Institution'),
        ('research', 'Research Institute'),
        ('other', 'Other'),
    ], string='Entity Type', default='private', required=True, tracking=True)

    industry_sector = fields.Char(
        string='Industry Sector', tracking=True,
        help='e.g., IT, Healthcare, Finance, Manufacturing')
    is_approved = fields.Boolean(
        string='Approved', default=False, tracking=True,
        help='Whether this entity is approved for internship placements.')
    approval_date = fields.Date(
        string='Approval Date', readonly=True, tracking=True)
    approved_by = fields.Many2one(
        'res.users', string='Approved By', readonly=True, tracking=True)

    partnership_start_date = fields.Date(
        string='Partnership Start Date', tracking=True)
    partnership_end_date = fields.Date(
        string='Partnership End Date', tracking=True)

    department_ids = fields.Many2many(
        'uni.department', string='Related Departments',
        help='University departments this entity accepts interns from.')

    contact_person = fields.Char(string='Contact Person', tracking=True)
    contact_position = fields.Char(string='Contact Position', tracking=True)
    contact_phone = fields.Char(string='Contact Phone', tracking=True)
    contact_email = fields.Char(string='Contact Email', tracking=True)

    max_interns_per_term = fields.Integer(
        string='Max Interns per Term', default=5, tracking=True)
    total_interns_hosted = fields.Integer(
        compute='_compute_interns', string='Total Hosted')

    rating = fields.Selection([
        ('0', 'No Rating'),
        ('1', 'Poor'),
        ('2', 'Fair'),
        ('3', 'Good'),
        ('4', 'Very Good'),
        ('5', 'Excellent'),
    ], string='Rating', default='0', tracking=True)

    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_entity_code', 'unique(entity_code)',
         'Entity code must be unique!'),
    ]

    @api.depends('name')
    def _compute_interns(self):
        # Count accepted applications whose opportunity belongs to this entity.
        Application = self.env['uni.internship.application']
        for rec in self:
            apps = Application.search([
                ('entity_id', '=', rec.id),
                ('status', '=', 'accepted'),
            ])
            rec.total_interns_hosted = len(apps)

    def action_approve(self):
        for rec in self:
            rec.write({
                'is_approved': True,
                'approval_date': fields.Date.context_today(self),
                'approved_by': self.env.uid,
            })

    def action_revoke(self):
        for rec in self:
            rec.write({
                'is_approved': False,
                'approval_date': False,
                'approved_by': False,
            })
