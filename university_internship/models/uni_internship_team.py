# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniInternshipTeam(models.Model):
    """Internship Team — a group of students collaborating on a single
    internship placement.

    An internship (``uni.internship``) can host one or more teams, each with
    its own leader, formation/dissolution dates, and membership roster.
    Team leaders must be active members of their team.
    """
    _name = 'uni.internship.team'
    _description = 'Internship Team'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'internship_id, formation_date'

    name = fields.Char(string='Team Name', required=True, tracking=True)
    internship_id = fields.Many2one(
        'uni.internship', string='Internship', required=True,
        ondelete='cascade', tracking=True, index=True)

    member_ids = fields.One2many(
        'uni.internship.team.member', 'team_id', string='Members')
    member_count = fields.Integer(
        compute='_compute_member_count', string='Members', store=True)

    team_leader_id = fields.Many2one(
        'uni.student', string='Team Leader',
        ondelete='restrict', tracking=True)
    team_leader_name = fields.Char(
        related='team_leader_id.name', string='Leader Name',
        store=True, readonly=True)

    formation_date = fields.Date(
        string='Formation Date', default=fields.Date.context_today,
        tracking=True)
    dissolution_date = fields.Date(
        string='Dissolution Date', tracking=True)

    status = fields.Selection([
        ('active', 'Active'),
        ('dissolved', 'Dissolved'),
    ], string='Status', default='active', tracking=True)

    description = fields.Text(string='Description')
    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_team_name_internship', 'unique(internship_id, name)',
         'Team name must be unique per internship!'),
    ]

    @api.depends('member_ids', 'member_ids.is_active')
    def _compute_member_count(self):
        for rec in self:
            rec.member_count = len(rec.member_ids.filtered(lambda m: m.is_active))

    @api.constrains('team_leader_id', 'member_ids')
    def _check_leader_is_member(self):
        for rec in self:
            if rec.team_leader_id:
                active_members = rec.member_ids.filtered(lambda m: m.is_active)
                if rec.team_leader_id not in active_members.mapped('student_id'):
                    raise ValidationError(_(
                        'Team leader must be an active member of the team!'
                    ))

    @api.constrains('member_count', 'internship_id')
    def _check_max_members(self):
        """Enforce the internship's max_team_size constraint."""
        for rec in self:
            if rec.internship_id and rec.internship_id.max_team_size \
                    and rec.member_count > rec.internship_id.max_team_size:
                raise ValidationError(_(
                    'Team "%s" has %d members, but the maximum allowed is %d!'
                ) % (rec.name, rec.member_count, rec.internship_id.max_team_size))

    def action_dissolve(self):
        for rec in self:
            rec.write({
                'status': 'dissolved',
                'dissolution_date': fields.Date.context_today(self),
            })

    def action_reactivate(self):
        for rec in self:
            rec.write({'status': 'active', 'dissolution_date': False})
