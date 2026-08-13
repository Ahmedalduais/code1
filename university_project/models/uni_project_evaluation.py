# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniProjectEvaluation(models.Model):
    """Project Evaluation — grades a project either as a team, an individual
    member, or a mix of both.

    Evaluation types:
        * ``team``       — applies ``team_score`` to the entire team.
        * ``individual`` — applies ``individual_score`` to a single member.
        * ``mixed``      — averages ``team_score`` and ``individual_score``.

    A 4-state lifecycle (draft → completed → appealed → finalized) and a
    computed ``is_passing`` flag (default 60% threshold) drive the workflow
    buttons in the form view.
    """
    _name = 'uni.project.evaluation'
    _description = 'Project Evaluation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'project_id, evaluation_date desc'

    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True,
        default=lambda self: _('New'), index=True)
    project_id = fields.Many2one(
        'uni.project', string='Project', required=True,
        ondelete='cascade', tracking=True, index=True)

    # Can evaluate team as a whole, individual member, or mixed
    team_id = fields.Many2one(
        'uni.project.team', string='Team',
        ondelete='cascade', tracking=True, index=True)
    member_id = fields.Many2one(
        'uni.project.team.member', string='Team Member',
        ondelete='cascade', tracking=True, index=True)

    evaluation_type = fields.Selection([
        ('team', 'Team Evaluation'),
        ('individual', 'Individual Evaluation'),
        ('mixed', 'Mixed Evaluation'),
    ], string='Evaluation Type', required=True, default='team', tracking=True)

    evaluation_date = fields.Datetime(
        string='Evaluation Date', default=fields.Datetime.now, tracking=True)
    evaluated_by = fields.Many2one(
        'res.users', string='Evaluated By', required=True,
        default=lambda self: self.env.user, tracking=True)

    evaluation_criteria = fields.Text(string='Evaluation Criteria')

    # Scores
    team_score = fields.Float(
        string='Team Score', digits=(5, 2), default=0.0, tracking=True,
        help='Score for the entire team (applies to all members).')
    individual_score = fields.Float(
        string='Individual Score', digits=(5, 2), default=0.0, tracking=True,
        help='Score specific to the individual member.')
    total_score = fields.Float(
        compute='_compute_total_score', string='Total Score',
        digits=(5, 2), store=True)

    max_score = fields.Float(
        string='Max Score', digits=(5, 2), default=100.0, tracking=True)
    score_percentage = fields.Float(
        compute='_compute_score_percentage', string='Score %', store=True)

    weight = fields.Float(
        string='Weight in Final Grade', digits=(5, 2), default=100.0,
        tracking=True,
        help='Percentage weight of this evaluation in the final grade.')
    grade_letter = fields.Char(string='Grade Letter', tracking=True)
    is_passing = fields.Boolean(
        string='Passing', compute='_compute_passing', store=True)

    comments = fields.Text(string='Comments')
    strengths = fields.Text(string='Strengths')
    weaknesses = fields.Text(string='Weaknesses')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('completed', 'Completed'),
        ('appealed', 'Appealed'),
        ('finalized', 'Finalized'),
    ], string='Status', default='draft', tracking=True,
        group_expand='_group_expand_states')

    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_evaluation_reference', 'unique(name)',
         'Evaluation reference must be unique!'),
        ('check_weight_range', 'check(weight >= 0 AND weight <= 100)',
         'Weight must be between 0 and 100!'),
        ('check_scores_positive',
         'check(team_score >= 0 AND individual_score >= 0)',
         'Scores must be positive!'),
    ]

    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in states]

    @api.depends('team_score', 'individual_score', 'evaluation_type')
    def _compute_total_score(self):
        for rec in self:
            if rec.evaluation_type == 'team':
                rec.total_score = rec.team_score
            elif rec.evaluation_type == 'individual':
                rec.total_score = rec.individual_score
            else:  # mixed
                rec.total_score = (rec.team_score + rec.individual_score) / 2.0

    @api.depends('total_score', 'max_score')
    def _compute_score_percentage(self):
        for rec in self:
            if rec.max_score > 0:
                rec.score_percentage = (rec.total_score / rec.max_score) * 100
            else:
                rec.score_percentage = 0.0

    @api.depends('score_percentage')
    def _compute_passing(self):
        for rec in self:
            rec.is_passing = rec.score_percentage >= 60.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.project.evaluation') or _('New')
        return super().create(vals_list)

    @api.constrains('evaluation_type', 'team_id', 'member_id')
    def _check_evaluation_consistency(self):
        for rec in self:
            if rec.evaluation_type == 'team' and not rec.team_id:
                raise ValidationError(_('Team evaluation requires a team!'))
            if rec.evaluation_type == 'individual' and not rec.member_id:
                raise ValidationError(_(
                    'Individual evaluation requires a team member!'))
            if rec.evaluation_type == 'mixed' and (not rec.team_id or not rec.member_id):
                raise ValidationError(_(
                    'Mixed evaluation requires both a team and a member!'))

    @api.onchange('evaluation_type')
    def _onchange_evaluation_type(self):
        if self.evaluation_type == 'team':
            self.member_id = False
        elif self.evaluation_type == 'individual':
            self.team_id = False

    def action_complete(self):
        for rec in self:
            rec.state = 'completed'

    def action_appeal(self):
        for rec in self:
            rec.state = 'appealed'

    def action_finalize(self):
        for rec in self:
            rec.state = 'finalized'

    def action_draft(self):
        for rec in self:
            rec.state = 'draft'
