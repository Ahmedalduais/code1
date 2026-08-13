# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniCommitteeMember(models.Model):
    """عضو اللجنة — يربط عضو هيئة التدريس بلجنة بدور محدد
    (رئيس/نائب رئيس/سكرتير/عضو) وتواريخ الانضمام والمغادرة.
    """
    _name = 'uni.committee.member'
    _description = 'Committee Member'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'committee_id, role, join_date'

    name = fields.Char(string='Reference', compute='_compute_name', store=True, index=True)
    committee_id = fields.Many2one(
        'uni.committee', string='Committee', required=True,
        ondelete='cascade', tracking=True, index=True)
    faculty_id = fields.Many2one(
        'uni.faculty', string='Faculty Member', required=True,
        ondelete='restrict', tracking=True, index=True)
    university_id = fields.Many2one(
        related='committee_id.university_id', store=True, string='University', index=True)
    role = fields.Selection([
        ('chair', 'Chairperson'),
        ('vice_chair', 'Vice Chairperson'),
        ('secretary', 'Secretary'),
        ('member', 'Member'),
    ], string='Role', default='member', tracking=True, index=True, required=True)
    join_date = fields.Date(string='Join Date', default=fields.Date.context_today,
                            tracking=True, required=True)
    leave_date = fields.Date(string='Leave Date', tracking=True)
    is_active = fields.Boolean(string='Active Member', default=True, tracking=True)
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('unique_committee_faculty', 'unique(committee_id, faculty_id)',
         'A faculty member can only be added once to a committee!'),
    ]

    # ------------------------------------------------------------------
    # Computed
    # ------------------------------------------------------------------
    @api.depends('committee_id.name', 'faculty_id.name')
    def _compute_name(self):
        for rec in self:
            committee_name = rec.committee_id.name or _('Draft')
            faculty_name = rec.faculty_id.name or _('Unknown')
            rec.name = _('%(committee)s — %(faculty)s') % {
                'committee': committee_name,
                'faculty': faculty_name,
            }

    # ------------------------------------------------------------------
    # Onchange — auto-set is_active based on dates
    # ------------------------------------------------------------------
    @api.onchange('leave_date')
    def _onchange_leave_date(self):
        if self.leave_date:
            self.is_active = False

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('join_date', 'leave_date')
    def _check_dates(self):
        for rec in self:
            if rec.join_date and rec.leave_date and rec.leave_date < rec.join_date:
                raise ValidationError(_(
                    "Leave date cannot be earlier than join date for member %s.")
                    % rec.display_name)

    @api.constrains('committee_id', 'role')
    def _check_single_chair(self):
        """Ensure only one active chair per committee."""
        for rec in self:
            if rec.role == 'chair' and rec.is_active and rec.committee_id:
                existing = self.search([
                    ('committee_id', '=', rec.committee_id.id),
                    ('role', '=', 'chair'),
                    ('is_active', '=', True),
                    ('id', '!=', rec.id),
                ], limit=1)
                if existing:
                    raise ValidationError(_(
                        "Committee %s already has an active chair (%s).")
                        % (rec.committee_id.display_name, existing.display_name))
