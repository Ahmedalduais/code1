# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class UniInternshipApplicationInterview(models.Model):
    _name = 'uni.internship.application.interview'
    _description = 'Application Interview'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'interview_date desc'

    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True,
        default=lambda self: _('New'), index=True)
    application_id = fields.Many2one(
        'uni.internship.application', string='Application',
        required=True, ondelete='cascade', tracking=True, index=True)
    student_id = fields.Many2one(
        'uni.student', related='application_id.student_id',
        string='Student', store=True, readonly=True)
    opportunity_id = fields.Many2one(
        'uni.internship.opportunity',
        related='application_id.opportunity_id',
        string='Opportunity', store=True, readonly=True)

    interview_date = fields.Datetime(
        string='Interview Date', required=True, tracking=True)
    start_time = fields.Float(string='Start Time', widget='float_time')
    end_time = fields.Float(string='End Time', widget='float_time')
    duration = fields.Float(
        compute='_compute_duration', string='Duration (hours)', store=True)

    interview_type = fields.Selection([
        ('phone', 'Phone Interview'),
        ('video', 'Video Interview'),
        ('in_person', 'In-Person Interview'),
        ('technical', 'Technical Interview'),
        ('panel', 'Panel Interview'),
    ], string='Interview Type', default='in_person',
        required=True, tracking=True)

    location = fields.Char(string='Location')
    meeting_url = fields.Char(string='Meeting URL')

    interviewer_id = fields.Many2one(
        'uni.internship.entity.supervisor', string='Interviewer',
        ondelete='set null', tracking=True)
    interviewer_name = fields.Char(
        related='interviewer_id.name', string='Interviewer Name',
        store=True, readonly=True)

    questions = fields.Text(string='Interview Questions')
    feedback = fields.Text(string='Feedback')

    result = fields.Selection([
        ('pending', 'Pending'),
        ('pass', 'Pass'),
        ('fail', 'Fail'),
        ('hold', 'On Hold'),
    ], string='Result', default='pending', tracking=True)

    score = fields.Float(string='Score', digits=(5, 2), tracking=True)
    max_score = fields.Float(
        string='Max Score', digits=(5, 2), default=100.0, tracking=True)

    state = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ], string='Status', default='scheduled', tracking=True,
        group_expand='_group_expand_states')

    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_interview_reference', 'unique(name)',
         'Interview reference must be unique!'),
    ]

    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in states]

    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for rec in self:
            if (rec.start_time is not None
                    and rec.end_time is not None
                    and rec.end_time >= rec.start_time):
                rec.duration = rec.end_time - rec.start_time
            else:
                rec.duration = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.internship.application.interview') or _('New')
        return super().create(vals_list)

    def action_complete(self):
        for rec in self:
            rec.state = 'completed'

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'

    def action_no_show(self):
        for rec in self:
            rec.state = 'no_show'
