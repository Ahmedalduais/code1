# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class UniInternshipOpportunitySkill(models.Model):
    _name = 'uni.internship.opportunity.skill'
    _description = 'Opportunity Required Skill'
    _order = 'opportunity_id, sequence'

    opportunity_id = fields.Many2one(
        'uni.internship.opportunity', string='Opportunity',
        required=True, ondelete='cascade', index=True)
    name = fields.Char(
        string='Skill Name', required=True, tracking=True)
    level = fields.Selection([
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('expert', 'Expert'),
    ], string='Required Level', default='intermediate',
        required=True, tracking=True)
    is_mandatory = fields.Boolean(
        string='Mandatory', default=True, tracking=True)
    description = fields.Text(string='Description')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(default=True)
