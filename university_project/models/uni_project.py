# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class UniProject(models.Model):
    """Graduation Project — inherits all base fields from ``uni.course``
    (prototype inheritance) and extends the model with project-specific
    concerns: project type, theme, source proposal, multi-team support,
    supervisors, execution artifacts (timeline / milestones / deliverables
    / meetings / progress reports), defense & evaluation tracking, and
    publication linkage.

    The inherited ``uni.course`` fields (name, code, university_id,
    college_id, department_id, credit_hours, description, objectives,
    coordinator_id, ...) are reused for the project record so that a
    project can be linked into the curriculum hierarchy exactly like a
    course while carrying its own project workflow state.
    """
    _name = 'uni.project'
    _inherit = 'uni.course'
    _description = 'Graduation Project'
    _order = 'start_date desc'

    # ------------------------------------------------------------------
    # Project classification
    # ------------------------------------------------------------------
    project_type = fields.Selection([
        ('graduation', 'Graduation Project'),
        ('capstone', 'Capstone Project'),
        ('research', 'Research Project'),
        ('industry', 'Industry Project'),
        ('innovation', 'Innovation Project'),
    ], string='Project Type', default='graduation', tracking=True)

    theme_id = fields.Many2one('uni.project.theme', string='Theme',
                               ondelete='restrict', tracking=True)
    proposal_id = fields.Many2one('uni.project.proposal', string='Source Proposal',
                                  ondelete='set null', tracking=True)

    # ------------------------------------------------------------------
    # Team support (KEY FEATURE)
    # ------------------------------------------------------------------
    team_ids = fields.One2many('uni.project.team', 'project_id', string='Teams')
    team_count = fields.Integer(compute='_compute_team_stats', string='Teams')
    total_members = fields.Integer(compute='_compute_team_stats', string='Total Members')
    is_group_project = fields.Boolean(compute='_compute_is_group',
                                      string='Group Project', store=True)
    max_team_size = fields.Integer(string='Max Team Size', default=5, tracking=True)

    # ------------------------------------------------------------------
    # Supervisors
    # ------------------------------------------------------------------
    supervisor_ids = fields.One2many('uni.project.supervisor', 'project_id',
                                     string='Supervisors')

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------
    timeline_id = fields.Many2one('uni.project.timeline', string='Timeline',
                                  ondelete='set null')
    milestone_ids = fields.One2many('uni.project.milestone', 'project_id',
                                    string='Milestones')
    deliverable_ids = fields.One2many('uni.project.deliverable', 'project_id',
                                      string='Deliverables')
    meeting_ids = fields.One2many('uni.project.meeting', 'project_id',
                                  string='Meetings')
    progress_ids = fields.One2many('uni.project.progress', 'project_id',
                                   string='Progress Reports')

    # ------------------------------------------------------------------
    # Defense & Evaluation
    # ------------------------------------------------------------------
    defense_ids = fields.One2many('uni.project.defense', 'project_id',
                                  string='Defenses')
    committee_ids = fields.One2many('uni.project.committee', 'project_id',
                                    string='Committees')
    evaluation_ids = fields.One2many('uni.project.evaluation', 'project_id',
                                     string='Evaluations')
    publication_ids = fields.One2many('uni.project.publication', 'project_id',
                                      string='Publications')

    # ------------------------------------------------------------------
    # Project schedule & budget
    # ------------------------------------------------------------------
    start_date = fields.Date(string='Start Date', tracking=True)
    expected_end_date = fields.Date(string='Expected End Date', tracking=True)
    actual_end_date = fields.Date(string='Actual End Date', tracking=True)

    budget = fields.Float(string='Total Budget', digits=(12, 2), tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)
    sponsor = fields.Char(string='Sponsor', tracking=True)
    sponsor_logo = fields.Image(string='Sponsor Logo')

    abstract = fields.Text(string='Abstract')
    keywords = fields.Char(string='Keywords',
                           help='Comma-separated keywords')

    # ------------------------------------------------------------------
    # Lifecycle state (overrides inherited course state with a richer set)
    # ------------------------------------------------------------------
    state = fields.Selection([
        ('planning', 'Planning'),
        ('active', 'Active'),
        ('on_hold', 'On Hold'),
        ('completed', 'Completed'),
        ('defended', 'Defended'),
        ('published', 'Published'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='planning', tracking=True,
        group_expand='_group_expand_states')

    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('check_max_team_size', 'check(max_team_size > 0)',
         'Max team size must be positive!'),
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
            rec.is_group_project = rec.total_members > 1

    # ------------------------------------------------------------------
    # Workflow actions (override / extend inherited course actions)
    # ------------------------------------------------------------------
    def action_activate(self):
        for rec in self:
            rec.state = 'active'

    def action_hold(self):
        for rec in self:
            rec.state = 'on_hold'

    def action_complete(self):
        for rec in self:
            rec.write({'state': 'completed',
                       'actual_end_date': fields.Date.context_today(self)})

    def action_defended(self):
        for rec in self:
            rec.state = 'defended'

    def action_publish(self):
        for rec in self:
            rec.state = 'published'

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'

    def action_plan(self):
        for rec in self:
            rec.state = 'planning'

    # ------------------------------------------------------------------
    # Smart-button: open teams of this project
    # ------------------------------------------------------------------
    def action_view_teams(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Teams'),
            'res_model': 'uni.project.team',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }
