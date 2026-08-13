# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class UniProjectProgress(models.Model):
    """Project Progress Report — captures periodic status updates for a
    graduation project, including completion percentage, completed/upcoming
    tasks, challenges, risks, budget consumption, and on-track flags.

    Used by supervisors and coordinators to monitor project health between
    milestones. Reference is auto-generated via the ``uni.project.progress``
    sequence (prefix PPG/%(year)s/).
    """
    _name = 'uni.project.progress'
    _description = 'Project Progress Report'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'report_date desc'

    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True,
        default=lambda self: _('New'), index=True)
    project_id = fields.Many2one(
        'uni.project', string='Project', required=True,
        ondelete='cascade', tracking=True, index=True)

    report_date = fields.Date(
        string='Report Date', required=True,
        default=fields.Date.context_today, tracking=True)
    reported_by = fields.Many2one(
        'res.users', string='Reported By', required=True,
        default=lambda self: self.env.user, tracking=True)

    progress_percentage = fields.Float(
        string='Progress %', digits=(5, 2), default=0.0,
        tracking=True, help='Overall completion percentage (0-100).')

    completed_tasks = fields.Text(string='Completed Tasks')
    upcoming_tasks = fields.Text(string='Upcoming Tasks')
    challenges = fields.Text(string='Challenges')
    risks = fields.Text(string='Risks & Issues')

    budget_used = fields.Float(
        string='Budget Used', digits=(12, 2), tracking=True)
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id)

    is_on_track = fields.Boolean(
        string='On Track', default=True, tracking=True)
    needs_attention = fields.Boolean(
        string='Needs Attention', default=False, tracking=True)

    notes = fields.Text(string='Notes')
    file = fields.Binary(string='Report File')
    filename = fields.Char(string='Filename')

    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_progress_reference', 'unique(name)',
         'Progress reference must be unique!'),
        ('check_percentage',
         'check(progress_percentage >= 0 AND progress_percentage <= 100)',
         'Progress percentage must be between 0 and 100!'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.project.progress') or _('New')
        return super().create(vals_list)

    @api.onchange('needs_attention')
    def _onchange_needs_attention(self):
        if self.needs_attention:
            self.is_on_track = False
