# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniProjectSupervisor(models.Model):
    _name = 'uni.project.supervisor'
    _description = 'Project Supervisor'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'project_id, sequence'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True,
                       default=lambda self: _('New'), index=True)
    project_id = fields.Many2one('uni.project', string='Project', required=True,
                                  ondelete='cascade', tracking=True, index=True)

    faculty_id = fields.Many2one('uni.faculty', string='Faculty Member', required=True,
                                  ondelete='restrict', tracking=True, index=True)
    faculty_name = fields.Char(related='faculty_id.name', string='Faculty Name',
                                store=True, readonly=True)

    supervisor_role = fields.Selection([
        ('primary', 'Primary Supervisor'),
        ('co_supervisor', 'Co-Supervisor'),
        ('external', 'External Supervisor'),
        ('advisor', 'Technical Advisor'),
    ], string='Role', default='primary', required=True, tracking=True)

    sequence = fields.Integer(string='Sequence', default=10)
    start_date = fields.Date(string='Start Date', default=fields.Date.context_today, tracking=True)
    end_date = fields.Date(string='End Date', tracking=True)
    is_active = fields.Boolean(string='Active', default=True, tracking=True)

    workload_hours = fields.Float(string='Workload (Hours/Week)', default=6, tracking=True)
    expertise_area = fields.Char(string='Expertise Area', tracking=True)

    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_supervisor_reference', 'unique(name)', 'Supervisor reference must be unique!'),
        ('unique_faculty_per_project', 'unique(project_id, faculty_id)',
         'Faculty can only supervise a project once!'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('uni.project.supervisor') or _('New')
        return super().create(vals_list)

    @api.constrains('end_date', 'start_date')
    def _check_dates(self):
        for rec in self:
            if rec.end_date and rec.start_date and rec.end_date < rec.start_date:
                raise ValidationError(_('End date must be after start date!'))

    @api.constrains('is_active', 'end_date')
    def _check_active_consistency(self):
        for rec in self:
            if rec.end_date and rec.is_active:
                raise ValidationError(_('A supervisor with an end date cannot be active!'))

    def action_end_supervision(self):
        for rec in self:
            rec.write({'is_active': False, 'end_date': fields.Date.context_today(self)})

    def action_reactivate(self):
        for rec in self:
            rec.write({'is_active': True, 'end_date': False})
