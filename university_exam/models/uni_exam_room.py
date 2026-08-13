# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniExamRoom(models.Model):
    """قاعة الامتحان — قاعة مخصصة لإجراء الامتحانات.

    تختلف عن ``uni.classroom`` (التابعة لوحدة الجداول) في أن قاعات الامتحانات
    قد تكون قاعات رياضية أو مسارح أو قاعات كبيرة مخصصة للامتحانات فقط، مع
    متطلبات خاصة مثل المراقبة، الساعات، التكييف، والتجهيزات الإضافية.

    لا تعتمد هذه الوحدة على ``university_timetable``، لذلك لا يوجد ربط مباشر
    بـ ``uni.classroom`` — تُستخدم حقول ``building`` و ``floor`` النصية.
    """
    _name = 'uni.exam.room'
    _description = 'Exam Room'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'university_id, code'

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Name', required=True, translate=True, tracking=True,
        help='Display name of the exam room.')
    code = fields.Char(
        string='Code', required=True, copy=False, index=True, tracking=True,
        help='Unique code identifying the exam room within the university.')
    active = fields.Boolean(string='Active', default=True)

    # ------------------------------------------------------------------
    # Location
    # ------------------------------------------------------------------
    university_id = fields.Many2one(
        'uni.university', string='University', required=True,
        ondelete='restrict', tracking=True, index=True)
    branch_id = fields.Many2one(
        'uni.branch', string='Branch', ondelete='restrict', tracking=True)
    building = fields.Char(string='Building', tracking=True)
    floor = fields.Char(string='Floor', tracking=True)

    # ------------------------------------------------------------------
    # Capacity & facilities
    # ------------------------------------------------------------------
    capacity = fields.Integer(
        string='Capacity', default=30, tracking=True,
        help='Maximum number of students the room can accommodate for an exam.')
    has_surveillance = fields.Boolean(
        string='Surveillance Cameras', default=False, tracking=True,
        help='Check if the room has surveillance cameras.')
    has_clock = fields.Boolean(
        string='Clock', default=True, tracking=True,
        help='Check if the room has a visible wall clock.')
    has_ac = fields.Boolean(
        string='Air Conditioning', default=False, tracking=True,
        help='Check if the room is air-conditioned.')
    facilities = fields.Text(
        string='Facilities', translate=True,
        help='Additional facilities available in the room.')

    # ------------------------------------------------------------------
    # State & relations
    # ------------------------------------------------------------------
    state = fields.Selection([
        ('available', 'Available'),
        ('maintenance', 'Under Maintenance'),
        ('occupied', 'Occupied'),
    ], string='State', default='available', tracking=True, index=True,
        group_expand='_group_expand_states')
    exam_ids = fields.Many2many(
        'uni.exam', string='Assigned Exams',
        help='Exams scheduled to use this room.')
    exam_count = fields.Integer(
        compute='_compute_exam_count', string='Exams Count')

    _sql_constraints = [
        ('unique_university_code', 'unique(university_id, code)',
         'Exam room code must be unique per university!'),
        ('check_capacity', 'check(capacity >= 0)',
         'Capacity cannot be negative!'),
    ]

    # ------------------------------------------------------------------
    # Group expansion helper
    # ------------------------------------------------------------------
    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in self._fields['state'].selection]

    # ------------------------------------------------------------------
    # Computed
    # ------------------------------------------------------------------
    @api.depends('exam_ids')
    def _compute_exam_count(self):
        for rec in self:
            rec.exam_count = len(rec.exam_ids)

    # ------------------------------------------------------------------
    # Onchange — keep hierarchy consistent
    # ------------------------------------------------------------------
    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        if self.branch_id and self.branch_id.university_id:
            self.university_id = self.branch_id.university_id

    # ------------------------------------------------------------------
    # Smart-button action
    # ------------------------------------------------------------------
    def action_open_exams(self):
        self.ensure_one()
        return {
            'name': _('Assigned Exams'),
            'type': 'ir.actions.act_window',
            'res_model': 'uni.exam',
            'view_mode': 'list,form',
            'domain': [('room_ids', 'in', self.id)],
            'context': {'default_room_ids': [(6, 0, [self.id])]},
        }

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_maintenance(self):
        """Mark the room as under maintenance."""
        for rec in self:
            if rec.state == 'occupied':
                raise ValidationError(_(
                    "Cannot put room '%s' under maintenance while it is occupied "
                    "by an ongoing exam.") % rec.display_name)
            rec.state = 'maintenance'

    def action_available(self):
        """Mark the room as available."""
        for rec in self:
            rec.state = 'available'

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('capacity')
    def _check_capacity(self):
        for rec in self:
            if rec.capacity < 0:
                raise ValidationError(_(
                    "Capacity cannot be negative for exam room '%s'.")
                    % rec.display_name)
