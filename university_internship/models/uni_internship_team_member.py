# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniInternshipTeamMember(models.Model):
    """Internship Team Member — a student participating in an internship team.

    Captures the student link, role (leader/member/contributor), join/exit
    dates, active status, and contribution percentage used by evaluation
    models to compute individual grades.
    """
    _name = 'uni.internship.team.member'
    _description = 'Internship Team Member'
    _order = 'team_id, join_date'

    team_id = fields.Many2one(
        'uni.internship.team', string='Team', required=True,
        ondelete='cascade', index=True)
    internship_id = fields.Many2one(
        'uni.internship', related='team_id.internship_id',
        string='Internship', store=True, readonly=True)

    student_id = fields.Many2one(
        'uni.student', string='Student', required=True,
        ondelete='restrict', tracking=True, index=True)
    student_name = fields.Char(
        related='student_id.name', string='Student Name',
        store=True, readonly=True)
    student_code = fields.Char(
        related='student_id.student_code', string='Student Code',
        store=True, readonly=True)

    join_date = fields.Date(
        string='Join Date', required=True,
        default=fields.Date.context_today, tracking=True)
    exit_date = fields.Date(string='Exit Date', tracking=True)
    role = fields.Selection([
        ('leader', 'Team Leader'),
        ('member', 'Team Member'),
        ('contributor', 'Contributor'),
    ], string='Role', default='member', tracking=True)
    is_active = fields.Boolean(
        string='Active Member', default=True, tracking=True)

    contribution_percentage = fields.Float(
        string='Contribution %', digits=(5, 2), default=100.0,
        tracking=True,
        help="Percentage of this member's contribution to the internship.")

    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_member_in_team', 'unique(team_id, student_id)',
         'Student can only be in a team once!'),
        ('check_contribution_range',
         'check(contribution_percentage >= 0 AND contribution_percentage <= 100)',
         'Contribution percentage must be between 0 and 100!'),
    ]

    @api.constrains('exit_date', 'join_date')
    def _check_dates(self):
        for rec in self:
            if rec.exit_date and rec.exit_date < rec.join_date:
                raise ValidationError(_('Exit date must be after join date!'))

    @api.constrains('is_active', 'exit_date')
    def _check_active_consistency(self):
        for rec in self:
            if rec.exit_date and rec.is_active:
                raise ValidationError(_(
                    'A member with an exit date cannot be active!'
                ))

    def action_set_inactive(self):
        for rec in self:
            rec.write({
                'is_active': False,
                'exit_date': fields.Date.context_today(self),
            })

    def action_reactivate(self):
        for rec in self:
            rec.write({'is_active': True, 'exit_date': False})
