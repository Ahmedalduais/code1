# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class UniProjectMilestone(models.Model):
    _name = 'uni.project.milestone'
    _description = 'Project Milestone'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'project_id, sequence'

    name = fields.Char(string='Milestone Name', required=True, tracking=True)
    project_id = fields.Many2one('uni.project', string='Project', required=True,
                                  ondelete='cascade', tracking=True, index=True)
    timeline_id = fields.Many2one('uni.project.timeline', string='Timeline',
                                   ondelete='set null', index=True)

    sequence = fields.Integer(string='Sequence', default=10)

    milestone_type = fields.Selection([
        ('proposal', 'Proposal'),
        ('requirements', 'Requirements Analysis'),
        ('design', 'Design'),
        ('prototype', 'Prototype'),
        ('implementation', 'Implementation'),
        ('testing', 'Testing'),
        ('documentation', 'Documentation'),
        ('deployment', 'Deployment'),
        ('defense', 'Defense'),
        ('other', 'Other'),
    ], string='Milestone Type', default='implementation', required=True, tracking=True)

    planned_date = fields.Date(string='Planned Date', required=True, tracking=True)
    actual_date = fields.Date(string='Actual Date', tracking=True)

    is_completed = fields.Boolean(string='Completed', compute='_compute_completed',
                                   store=True, tracking=True)
    completed_date = fields.Date(string='Completed Date', tracking=True)

    description = fields.Text(string='Description')
    deliverable_ids = fields.One2many('uni.project.deliverable', 'milestone_id', string='Deliverables')
    deliverable_count = fields.Integer(compute='_compute_deliverable_count', string='Deliverables')

    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    @api.depends('completed_date')
    def _compute_completed(self):
        for rec in self:
            rec.is_completed = bool(rec.completed_date)

    @api.depends('deliverable_ids')
    def _compute_deliverable_count(self):
        for rec in self:
            rec.deliverable_count = len(rec.deliverable_ids)

    def action_complete(self):
        for rec in self:
            rec.write({
                'is_completed': True,
                'completed_date': fields.Date.context_today(self),
                'actual_date': rec.actual_date or fields.Date.context_today(self),
            })

    def action_reset(self):
        for rec in self:
            rec.write({'is_completed': False, 'completed_date': False})
