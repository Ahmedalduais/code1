# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniProjectDefense(models.Model):
    """Project Defense — formal defense session for a graduation project
    (proposal / midterm / final).

    Captures scheduling (date, location, online meeting URL), committee
    assignment, presentation file, attendance, grading (raw grade +
    max_grade + computed percentage + letter), feedback / recommendations,
    final decision (pass / conditional_pass / fail / defer), and a 4-state
    lifecycle (scheduled → ongoing → completed / cancelled).

    On ``action_complete`` with a pass / conditional_pass decision, the
    linked project is automatically transitioned to the ``defended`` state.
    """
    _name = 'uni.project.defense'
    _description = 'Project Defense'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'

    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True,
        default=lambda self: _('New'), index=True)
    project_id = fields.Many2one(
        'uni.project', string='Project', required=True,
        ondelete='cascade', tracking=True, index=True)

    defense_type = fields.Selection([
        ('proposal', 'Proposal Defense'),
        ('midterm', 'Midterm Defense'),
        ('final', 'Final Defense'),
    ], string='Defense Type', default='final', required=True, tracking=True)

    date = fields.Datetime(string='Date & Time', required=True, tracking=True)
    start_time = fields.Float(string='Start Time', widget='float_time')
    end_time = fields.Float(string='End Time', widget='float_time')
    duration = fields.Float(
        compute='_compute_duration', string='Duration (hours)', store=True)

    location = fields.Char(string='Location')
    is_online = fields.Boolean(string='Online', default=False)
    meeting_url = fields.Char(string='Meeting URL')

    committee_ids = fields.Many2many(
        'uni.project.committee', string='Committees')
    chairperson_id = fields.Many2one(
        'uni.faculty', string='Chairperson',
        ondelete='restrict', tracking=True)

    presentation_file = fields.Binary(string='Presentation File')
    presentation_filename = fields.Char(string='Presentation Filename')

    attendance = fields.Text(string='Attendance')
    is_public = fields.Boolean(
        string='Public Defense', default=False, tracking=True)

    grade = fields.Float(string='Grade', digits=(5, 2), tracking=True)
    max_grade = fields.Float(
        string='Max Grade', digits=(5, 2), default=100.0, tracking=True)
    grade_percentage = fields.Float(
        compute='_compute_grade_percentage', string='Grade %', store=True)
    grade_letter = fields.Char(string='Grade Letter', tracking=True)

    feedback = fields.Text(string='Feedback')
    recommendations = fields.Text(string='Recommendations')

    decision = fields.Selection([
        ('pass', 'Pass'),
        ('conditional_pass', 'Conditional Pass'),
        ('fail', 'Fail'),
        ('defer', 'Deferred'),
    ], string='Decision', tracking=True)
    conditions = fields.Text(string='Conditions')

    state = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='scheduled', tracking=True,
        group_expand='_group_expand_states')

    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_defense_reference', 'unique(name)',
         'Defense reference must be unique!'),
        ('check_grade_range', 'check(grade >= 0 AND grade <= max_grade)',
         'Grade must be between 0 and max grade!'),
    ]

    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in states]

    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for rec in self:
            if rec.start_time is not None and rec.end_time is not None \
                    and rec.end_time >= rec.start_time:
                rec.duration = rec.end_time - rec.start_time
            else:
                rec.duration = 0.0

    @api.depends('grade', 'max_grade')
    def _compute_grade_percentage(self):
        for rec in self:
            if rec.max_grade > 0:
                rec.grade_percentage = (rec.grade / rec.max_grade) * 100
            else:
                rec.grade_percentage = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.project.defense') or _('New')
        return super().create(vals_list)

    def action_start(self):
        for rec in self:
            rec.state = 'ongoing'

    def action_complete(self):
        for rec in self:
            rec.state = 'completed'
            # Also update the project state
            if rec.project_id and rec.decision in ('pass', 'conditional_pass'):
                rec.project_id.action_defended()

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'
