# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class UniInternshipEntitySupervisor(models.Model):
    _name = 'uni.internship.entity.supervisor'
    _description = 'Entity Supervisor (Field Supervisor)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'entity_id, name'

    name = fields.Char(
        string='Supervisor Name', required=True, tracking=True)
    entity_id = fields.Many2one(
        'uni.internship.training.entity', string='Training Entity',
        required=True, ondelete='cascade', tracking=True, index=True)

    employee_id = fields.Many2one(
        'hr.employee', string='Linked Employee',
        ondelete='set null', tracking=True)

    position = fields.Char(string='Position/Title', tracking=True)
    department = fields.Char(string='Department in Entity', tracking=True)
    phone = fields.Char(string='Phone', tracking=True)
    email = fields.Char(string='Email', tracking=True)

    is_primary_contact = fields.Boolean(
        string='Primary Contact', default=False, tracking=True)
    is_active = fields.Boolean(string='Active', default=True, tracking=True)

    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_supervisor_per_entity', 'unique(entity_id, name)',
         'Supervisor name must be unique per entity!'),
    ]
