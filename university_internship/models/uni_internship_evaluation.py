from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniInternshipEvaluation(models.Model):
    _name = 'uni.internship.evaluation'
    _description = 'Internship Evaluation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'evaluation_date desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True,
                       default=lambda self: _('New'), index=True)
    internship_id = fields.Many2one('uni.internship', string='Internship', required=True,
                                     ondelete='cascade', tracking=True, index=True)

    team_id = fields.Many2one('uni.internship.team', string='Team', ondelete='cascade', tracking=True)
    member_id = fields.Many2one('uni.internship.team.member', string='Team Member',
                                 ondelete='cascade', tracking=True)

    evaluation_type = fields.Selection([
        ('team', 'Team Evaluation'),
        ('individual', 'Individual Evaluation'),
        ('mixed', 'Mixed Evaluation'),
    ], string='Evaluation Type', required=True, default='individual', tracking=True)

    evaluator_type = fields.Selection([
        ('academic', 'Academic Supervisor'),
        ('field', 'Field Supervisor'),
        ('committee', 'Evaluation Committee'),
        ('self', 'Self Evaluation'),
    ], string='Evaluator Type', default='academic', required=True, tracking=True)

    evaluator_id = fields.Many2one('res.users', string='Evaluator', required=True,
                                    default=lambda self: self.env.user, tracking=True)
    faculty_id = fields.Many2one('uni.faculty', string='Faculty Evaluator', ondelete='set null')
    entity_supervisor_id = fields.Many2one('uni.internship.entity.supervisor', string='Field Evaluator',
                                            ondelete='set null')

    evaluation_date = fields.Datetime(string='Evaluation Date', default=fields.Datetime.now, tracking=True)

    criteria_scores = fields.Text(string='Criteria Scores (JSON)',
                                   help='JSON mapping of criteria_id to score.')

    team_score = fields.Float(string='Team Score', digits=(5, 2), default=0.0, tracking=True)
    individual_score = fields.Float(string='Individual Score', digits=(5, 2), default=0.0, tracking=True)
    total_score = fields.Float(compute='_compute_total_score', string='Total Score', digits=(5, 2), store=True)

    max_score = fields.Float(string='Max Score', digits=(5, 2), default=100.0, tracking=True)
    score_percentage = fields.Float(compute='_compute_score_percentage', string='Score %', store=True)

    grade = fields.Selection([
        ('excellent', 'Excellent'),
        ('very_good', 'Very Good'),
        ('good', 'Good'),
        ('pass', 'Pass'),
        ('fail', 'Fail'),
    ], string='Grade', tracking=True)
    is_passing = fields.Boolean(compute='_compute_passing', string='Passing', store=True)
    is_final = fields.Boolean(string='Is Final Evaluation', default=False, tracking=True)

    comments = fields.Text(string='Comments')
    strengths = fields.Text(string='Strengths')
    areas_for_improvement = fields.Text(string='Areas for Improvement')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('completed', 'Completed'),
        ('appealed', 'Appealed'),
        ('finalized', 'Finalized'),
    ], string='Status', default='draft', tracking=True, group_expand='_group_expand_states')

    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_evaluation_reference', 'unique(name)', 'Evaluation reference must be unique!'),
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
            else:
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
                vals['name'] = self.env['ir.sequence'].next_by_code('uni.internship.evaluation') or _('New')
        return super().create(vals_list)

    @api.constrains('evaluation_type', 'team_id', 'member_id')
    def _check_evaluation_consistency(self):
        for rec in self:
            if rec.evaluation_type == 'team' and not rec.team_id:
                raise ValidationError(_('Team evaluation requires a team!'))
            if rec.evaluation_type == 'individual' and not rec.member_id:
                raise ValidationError(_('Individual evaluation requires a team member!'))
            if rec.evaluation_type == 'mixed' and (not rec.team_id or not rec.member_id):
                raise ValidationError(_('Mixed evaluation requires both team and member!'))

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
