# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class UniInternshipSupervisionPlan(models.Model):
    """Supervision Plan — defines how an internship will be supervised:
    meeting schedule, frequency, objectives, expected outcomes, and the
    assessment methodology used by the supervisor(s).

    Each plan has its own lifecycle (draft → active → completed / cancelled)
    independent from the internship state, and can optionally be linked to
    a specific supervisor assignment or directly to a faculty member.
    """
    _name = 'uni.internship.supervision.plan'
    _description = 'Supervision Plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'internship_id'

    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True,
        default=lambda self: _('New'), index=True)
    internship_id = fields.Many2one(
        'uni.internship', string='Internship', required=True,
        ondelete='cascade', tracking=True, index=True)

    supervisor_id = fields.Many2one(
        'uni.internship.supervisor', string='Supervisor',
        ondelete='set null', tracking=True)
    faculty_id = fields.Many2one(
        'uni.faculty', string='Faculty', ondelete='restrict', tracking=True)

    meeting_schedule = fields.Text(
        string='Meeting Schedule',
        help='e.g., Weekly meetings every Tuesday at 2 PM')
    meeting_frequency = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('bi_weekly', 'Bi-Weekly'),
        ('monthly', 'Monthly'),
        ('as_needed', 'As Needed'),
    ], string='Meeting Frequency', default='weekly', tracking=True)

    objectives = fields.Text(string='Objectives')
    expected_outcomes = fields.Text(string='Expected Outcomes')
    assessment_methodology = fields.Text(string='Assessment Methodology')

    start_date = fields.Date(
        string='Start Date', default=fields.Date.context_today, tracking=True)
    end_date = fields.Date(string='End Date', tracking=True)

    status = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True,
        group_expand='_group_expand_states')

    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_plan_reference', 'unique(name)',
         'Plan reference must be unique!'),
    ]

    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in states]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code(
                        'uni.internship.supervision.plan') or _('New')
                )
        return super().create(vals_list)

    def action_activate(self):
        for rec in self:
            rec.status = 'active'

    def action_complete(self):
        for rec in self:
            rec.status = 'completed'

    def action_cancel(self):
        for rec in self:
            rec.status = 'cancelled'

    def action_draft(self):
        for rec in self:
            rec.status = 'draft'
