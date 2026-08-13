# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniProjectTimeline(models.Model):
    _name = 'uni.project.timeline'
    _description = 'Project Timeline'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'project_id'

    name = fields.Char(string='Timeline Name', required=True, tracking=True)
    project_id = fields.Many2one('uni.project', string='Project', required=True,
                                  ondelete='cascade', tracking=True, index=True)

    start_date = fields.Date(string='Start Date', required=True, tracking=True)
    end_date = fields.Date(string='End Date', required=True, tracking=True)
    duration_days = fields.Integer(compute='_compute_duration', string='Duration (Days)', store=True)
    duration_weeks = fields.Float(compute='_compute_duration', string='Duration (Weeks)', store=True)

    description = fields.Text(string='Description')
    milestone_ids = fields.One2many('uni.project.milestone', 'timeline_id', string='Milestones')
    milestone_count = fields.Integer(compute='_compute_milestone_count', string='Milestones')

    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_timeline_project', 'unique(project_id, name)',
         'Timeline name must be unique per project!'),
        ('check_dates', 'check(end_date >= start_date)',
         'End date must be after or equal to start date!'),
    ]

    @api.depends('start_date', 'end_date')
    def _compute_duration(self):
        for rec in self:
            if rec.start_date and rec.end_date:
                delta = (rec.end_date - rec.start_date).days + 1
                rec.duration_days = delta
                rec.duration_weeks = round(delta / 7.0, 1)
            else:
                rec.duration_days = 0
                rec.duration_weeks = 0.0

    @api.depends('milestone_ids')
    def _compute_milestone_count(self):
        for rec in self:
            rec.milestone_count = len(rec.milestone_ids)
