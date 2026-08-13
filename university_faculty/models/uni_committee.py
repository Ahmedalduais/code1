# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniCommittee(models.Model):
    """اللجنة الجامعية — أكاديمية / إدارية / بحثية / تأديبية.

    تُعرف اللجنة بنطاقها (جامعة، كلية، قسم)، رئيسها (عضو هيئة تدريس)،
    وأعضائها عبر ``uni.committee.member``، مع دورة حياة بسيطة.
    """
    _name = 'uni.committee'
    _description = 'University Committee'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'start_date desc, name'

    name = fields.Char(string='Committee Name', required=True, tracking=True, translate=True)
    code = fields.Char(string='Code', required=True, copy=False, index=True, tracking=True)
    committee_type = fields.Selection([
        ('academic', 'Academic'),
        ('administrative', 'Administrative'),
        ('research', 'Research'),
        ('disciplinary', 'Disciplinary'),
    ], string='Committee Type', default='academic', tracking=True, index=True)
    university_id = fields.Many2one(
        'uni.university', string='University',
        ondelete='restrict', tracking=True, index=True)
    college_id = fields.Many2one(
        'uni.college', string='College', ondelete='restrict', tracking=True, index=True)
    department_id = fields.Many2one(
        'uni.department', string='Department', ondelete='restrict', tracking=True, index=True)
    chair_id = fields.Many2one(
        'uni.faculty', string='Chairperson',
        ondelete='restrict', tracking=True, index=True,
        help='Faculty member chairing the committee.')
    start_date = fields.Date(string='Start Date', tracking=True)
    end_date = fields.Date(string='End Date', tracking=True)
    member_ids = fields.One2many(
        'uni.committee.member', 'committee_id', string='Members')
    member_count = fields.Integer(compute='_compute_member_count', string='Members')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('closed', 'Closed'),
    ], string='Status', default='draft', tracking=True, index=True, group_expand='_group_expand_states')
    description = fields.Text(string='Description')

    _sql_constraints = [
        ('unique_committee_code', 'unique(code)',
         'Committee code must be unique!'),
    ]

    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in self._fields['state'].selection]

    # ------------------------------------------------------------------
    # Computed
    # ------------------------------------------------------------------
    @api.depends('member_ids')
    def _compute_member_count(self):
        for rec in self:
            rec.member_count = len(rec.member_ids.filtered(lambda m: m.is_active))

    # ------------------------------------------------------------------
    # Onchange — propagate chair as a member if not already
    # ------------------------------------------------------------------
    @api.onchange('chair_id')
    def _onchange_chair_id(self):
        """When a chair is set, ensure they are also a member with role 'chair'."""
        if self.chair_id and self.chair_id not in self.member_ids.mapped('faculty_id'):
            self.member_ids = [(0, 0, {
                'faculty_id': self.chair_id.id,
                'role': 'chair',
                'is_active': True,
                'join_date': fields.Date.context_today(self),
            })]

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_activate(self):
        for rec in self:
            if not rec.chair_id:
                raise ValidationError(_(
                    "Committee %s must have a chairperson before activation.")
                    % rec.display_name)
            rec.state = 'active'

    def action_close(self):
        for rec in self:
            rec.state = 'closed'
            rec.end_date = rec.end_date or fields.Date.context_today(rec)

    def action_draft(self):
        for rec in self:
            rec.state = 'draft'

    def action_open_members(self):
        """Smart-button: open the members of this committee."""
        self.ensure_one()
        return {
            'name': _('Committee Members'),
            'type': 'ir.actions.act_window',
            'res_model': 'uni.committee.member',
            'view_mode': 'list,form',
            'domain': [('committee_id', '=', self.id)],
            'context': {'default_committee_id': self.id},
        }

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for rec in self:
            if rec.start_date and rec.end_date and rec.end_date < rec.start_date:
                raise ValidationError(_(
                    "Committee end date cannot be earlier than start date (%s).")
                    % rec.display_name)

    @api.constrains('university_id', 'college_id', 'department_id')
    def _check_hierarchy(self):
        for rec in self:
            if rec.department_id and rec.department_id.university_id != rec.university_id:
                raise ValidationError(_(
                    "Committee %s: department does not belong to the selected university.")
                    % rec.display_name)
            if rec.college_id and rec.college_id.university_id != rec.university_id:
                raise ValidationError(_(
                    "Committee %s: college does not belong to the selected university.")
                    % rec.display_name)
            if rec.department_id and rec.college_id and \
                    rec.department_id.college_id != rec.college_id:
                raise ValidationError(_(
                    "Committee %s: department does not belong to the selected college.")
                    % rec.display_name)
