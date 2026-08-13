# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniProjectMeeting(models.Model):
    _name = 'uni.project.meeting'
    _description = 'Project Meeting'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True,
                       default=lambda self: _('New'), index=True)
    project_id = fields.Many2one('uni.project', string='Project', required=True,
                                  ondelete='cascade', tracking=True, index=True)

    meeting_type = fields.Selection([
        ('kickoff', 'Kickoff Meeting'),
        ('progress', 'Progress Meeting'),
        ('review', 'Review Meeting'),
        ('supervisor', 'Supervisor Meeting'),
        ('committee', 'Committee Meeting'),
        ('emergency', 'Emergency Meeting'),
        ('other', 'Other'),
    ], string='Meeting Type', default='progress', required=True, tracking=True)

    title = fields.Char(string='Title', required=True, tracking=True)
    date = fields.Datetime(string='Date & Time', required=True, tracking=True)
    start_time = fields.Float(string='Start Time', widget='float_time')
    end_time = fields.Float(string='End Time', widget='float_time')
    duration = fields.Float(compute='_compute_duration', string='Duration (hours)', store=True)

    location = fields.Char(string='Location')
    is_online = fields.Boolean(string='Online Meeting', default=False)
    meeting_url = fields.Char(string='Meeting URL')

    chairperson_id = fields.Many2one('uni.faculty', string='Chairperson',
                                      ondelete='restrict', tracking=True)
    attendees = fields.Text(string='Attendees')

    agenda = fields.Text(string='Agenda')
    minutes = fields.Html(string='Minutes of Meeting')
    decisions = fields.Text(string='Decisions')
    action_items = fields.Text(string='Action Items')

    file = fields.Binary(string='Meeting Document')
    filename = fields.Char(string='Filename')

    state = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='scheduled', tracking=True, group_expand='_group_expand_states')

    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_meeting_reference', 'unique(name)', 'Meeting reference must be unique!'),
    ]

    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in states]

    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for rec in self:
            if rec.start_time is not None and rec.end_time is not None and rec.end_time >= rec.start_time:
                rec.duration = rec.end_time - rec.start_time
            else:
                rec.duration = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('uni.project.meeting') or _('New')
        return super().create(vals_list)

    def action_start(self):
        for rec in self:
            rec.state = 'ongoing'

    def action_complete(self):
        for rec in self:
            rec.state = 'completed'

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'
