# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniProjectCommittee(models.Model):
    """Project Committee — a group of faculty members assigned to a project
    for a specific role (supervisory, examination, defense, review).

    Each committee has a chairperson who must be one of its members, a
    formation / dissolution date, and an ``is_active`` flag managed by the
    ``action_dissolve`` / ``action_reactivate`` workflow buttons.
    Committees can be linked to one or more defense sessions through the
    ``committee_ids`` M2m on ``uni.project.defense``.
    """
    _name = 'uni.project.committee'
    _description = 'Project Committee'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'project_id, formation_date'

    name = fields.Char(string='Committee Name', required=True, tracking=True)
    project_id = fields.Many2one(
        'uni.project', string='Project', required=True,
        ondelete='cascade', tracking=True, index=True)

    committee_type = fields.Selection([
        ('supervisory', 'Supervisory Committee'),
        ('examination', 'Examination Committee'),
        ('defense', 'Defense Committee'),
        ('review', 'Review Committee'),
    ], string='Committee Type', default='defense', required=True, tracking=True)

    member_ids = fields.Many2many(
        'uni.faculty', string='Committee Members',
        relation='uni_project_committee_member_rel')
    member_count = fields.Integer(
        compute='_compute_member_count', string='Members')

    chairperson_id = fields.Many2one(
        'uni.faculty', string='Chairperson',
        ondelete='restrict', tracking=True)

    formation_date = fields.Date(
        string='Formation Date', default=fields.Date.context_today, tracking=True)
    dissolution_date = fields.Date(string='Dissolution Date', tracking=True)
    is_active = fields.Boolean(
        string='Active', default=True, tracking=True)

    description = fields.Text(string='Description')
    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_committee_project', 'unique(project_id, name)',
         'Committee name must be unique per project!'),
    ]

    @api.depends('member_ids')
    def _compute_member_count(self):
        for rec in self:
            rec.member_count = len(rec.member_ids)

    @api.constrains('chairperson_id', 'member_ids')
    def _check_chairperson_is_member(self):
        for rec in self:
            if rec.chairperson_id and rec.chairperson_id not in rec.member_ids:
                raise ValidationError(_(
                    'Chairperson must be a member of the committee!'))

    def action_dissolve(self):
        for rec in self:
            rec.write({
                'is_active': False,
                'dissolution_date': fields.Date.context_today(self),
            })

    def action_reactivate(self):
        for rec in self:
            rec.write({'is_active': True, 'dissolution_date': False})
