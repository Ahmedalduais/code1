# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class UniInternship(models.Model):
    """Internship — inherits all base fields from ``uni.course``
    (prototype inheritance) and extends the model with internship-specific
    concerns: internship type, source opportunity, training entity, academic
    term, multi-team support, supervisors, daily logs, attendance, weekly &
    final reports, evaluations, completion tracking, and a dedicated
    internship lifecycle state.

    The inherited ``uni.course`` fields (name, code, university_id,
    college_id, department_id, credit_hours, description, objectives,
    coordinator_id, ...) are reused for the internship record so that an
    internship can be linked into the curriculum hierarchy exactly like a
    course while carrying its own internship workflow state.
    """
    _name = 'uni.internship'
    _inherit = 'uni.course'
    _description = 'Internship'
    _order = 'start_date desc'

    # ------------------------------------------------------------------
    # Internship classification
    # ------------------------------------------------------------------
    internship_type = fields.Selection([
        ('summer', 'Summer Training'),
        ('semester', 'Semester Internship'),
        ('year_long', 'Year-Long Internship'),
        ('capstone', 'Capstone Internship'),
        ('graduation', 'Graduation Internship'),
    ], string='Internship Type', default='summer', tracking=True)

    training_entity_id = fields.Many2one(
        'uni.internship.training.entity', string='Training Entity',
        ondelete='restrict', tracking=True, index=True)
    opportunity_id = fields.Many2one(
        'uni.internship.opportunity', string='Source Opportunity',
        ondelete='set null', tracking=True)

    academic_term_id = fields.Many2one(
        'uni.academic.term', string='Academic Term',
        ondelete='restrict', tracking=True)

    # ------------------------------------------------------------------
    # Team support (KEY FEATURE)
    # ------------------------------------------------------------------
    team_ids = fields.One2many(
        'uni.internship.team', 'internship_id', string='Teams')
    team_count = fields.Integer(
        compute='_compute_team_stats', string='Teams')
    total_members = fields.Integer(
        compute='_compute_team_stats', string='Total Members')
    is_group_internship = fields.Boolean(
        compute='_compute_is_group', string='Group Internship', store=True)
    max_team_size = fields.Integer(
        string='Max Team Size', default=5, tracking=True)

    # ------------------------------------------------------------------
    # Supervisors
    # ------------------------------------------------------------------
    supervisor_ids = fields.One2many(
        'uni.internship.supervisor', 'internship_id', string='Supervisors')

    # ------------------------------------------------------------------
    # Dates & Hours
    # ------------------------------------------------------------------
    start_date = fields.Date(string='Start Date', tracking=True)
    end_date = fields.Date(string='End Date', tracking=True)
    hours_required = fields.Float(
        string='Required Hours', default=240, tracking=True)
    hours_completed = fields.Float(
        compute='_compute_hours_completed', string='Completed Hours',
        store=True)
    hours_remaining = fields.Float(
        compute='_compute_hours_completed', string='Remaining Hours',
        store=True)
    progress_percentage = fields.Float(
        compute='_compute_progress', string='Progress %', store=True)

    # ------------------------------------------------------------------
    # Related records (resolved lazily by the registry at runtime)
    # ------------------------------------------------------------------
    log_ids = fields.One2many(
        'uni.internship.log', 'internship_id', string='Daily Logs')
    attendance_ids = fields.One2many(
        'uni.internship.attendance', 'internship_id', string='Attendance')
    weekly_report_ids = fields.One2many(
        'uni.internship.weekly.report', 'internship_id',
        string='Weekly Reports')
    report_ids = fields.One2many(
        'uni.internship.report', 'internship_id', string='Reports')
    evaluation_ids = fields.One2many(
        'uni.internship.evaluation', 'internship_id', string='Evaluations')
    completion_ids = fields.One2many(
        'uni.internship.completion', 'internship_id', string='Completions')

    # ------------------------------------------------------------------
    # Grade
    # ------------------------------------------------------------------
    final_grade = fields.Float(
        string='Final Grade', digits=(5, 2), tracking=True)
    grade_letter = fields.Char(string='Grade Letter', tracking=True)

    # ------------------------------------------------------------------
    # Lifecycle state (separate from inherited course state)
    # ------------------------------------------------------------------
    internship_state = fields.Selection([
        ('planning', 'Planning'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ], string='Internship Status', default='planning', tracking=True,
        group_expand='_group_expand_states')

    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('check_max_team_size', 'check(max_team_size > 0)',
         'Max team size must be positive!'),
        ('check_hours_positive', 'check(hours_required >= 0)',
         'Required hours must be positive!'),
    ]

    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in states]

    @api.depends('team_ids', 'team_ids.member_count')
    def _compute_team_stats(self):
        for rec in self:
            rec.team_count = len(rec.team_ids)
            rec.total_members = sum(t.member_count for t in rec.team_ids)

    @api.depends('total_members')
    def _compute_is_group(self):
        for rec in self:
            rec.is_group_internship = rec.total_members > 1

    @api.depends('log_ids', 'attendance_ids')
    def _compute_hours_completed(self):
        for rec in self:
            log_hours = sum(log.hours for log in rec.log_ids)
            att_hours = sum(
                att.hours for att in rec.attendance_ids
                if att.status == 'present'
            )
            rec.hours_completed = max(log_hours, att_hours)
            rec.hours_remaining = max(
                0, rec.hours_required - rec.hours_completed)

    @api.depends('hours_completed', 'hours_required')
    def _compute_progress(self):
        for rec in self:
            if rec.hours_required > 0:
                rec.progress_percentage = (
                    (rec.hours_completed / rec.hours_required) * 100
                )
            else:
                rec.progress_percentage = 0.0

    # ------------------------------------------------------------------
    # Workflow actions (internship lifecycle)
    # ------------------------------------------------------------------
    def action_start(self):
        for rec in self:
            rec.internship_state = 'ongoing'

    def action_complete(self):
        for rec in self:
            rec.write({
                'internship_state': 'completed',
                'end_date': fields.Date.context_today(self),
            })

    def action_fail(self):
        for rec in self:
            rec.internship_state = 'failed'

    def action_cancel(self):
        for rec in self:
            rec.internship_state = 'cancelled'

    def action_planning(self):
        for rec in self:
            rec.internship_state = 'planning'

    # ------------------------------------------------------------------
    # Smart-button: open teams of this internship
    # ------------------------------------------------------------------
    def action_view_teams(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Teams'),
            'res_model': 'uni.internship.team',
            'view_mode': 'list,form',
            'domain': [('internship_id', '=', self.id)],
            'context': {'default_internship_id': self.id},
        }

    def action_view_logs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Daily Logs'),
            'res_model': 'uni.internship.log',
            'view_mode': 'list,form',
            'domain': [('internship_id', '=', self.id)],
            'context': {'default_internship_id': self.id},
        }

    def action_view_reports(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reports'),
            'res_model': 'uni.internship.report',
            'view_mode': 'list,form',
            'domain': [('internship_id', '=', self.id)],
            'context': {'default_internship_id': self.id},
        }

    def action_view_evaluations(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Evaluations'),
            'res_model': 'uni.internship.evaluation',
            'view_mode': 'list,form',
            'domain': [('internship_id', '=', self.id)],
            'context': {'default_internship_id': self.id},
        }
