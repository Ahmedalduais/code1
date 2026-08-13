# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class UniStudentStatus(models.Model):
    """حالة الطالب الأكاديمية.

    تصنيف مرن لحالات الطالب مع مؤشرات منطقية تُمكّن باقي الوحدات من
    التمييز بين الحالة "نشطة" (is_active_status)، والحالة "متخرج"
    (is_graduated_status)، والحالة "محظورة" (is_blocked_status) دون
    ربط الكود بنص الحالة.

    أمثلة للاستخدام:
        * Active     → is_active_status=True
        * Graduated  → is_graduated_status=True
        * Suspended  → is_blocked_status=True
        * Withdrawn  → is_blocked_status=True
        * On Leave   → (no flag, status归类 منفصل)
        * Prospective → is_active_status=False (مرشح قبل القبول)
    """
    _name = 'uni.student.status'
    _description = 'Student Status'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'sequence, name'

    name = fields.Char(string='Status Name', required=True, translate=True, tracking=True,
                       help='Display name of the student status (e.g. Active, Suspended).')
    code = fields.Char(string='Code', required=True, copy=False, index=True,
                       help='Short unique code identifying the status (e.g. ACTIVE, GRAD).')
    sequence = fields.Integer(string='Sequence', default=10,
                              help='Used to order statuses in listings and selections.')
    description = fields.Text(string='Description')
    color = fields.Integer(string='Color Index', default=0,
                           help='Color used for kanban/list decoration.')

    # ------------------------------------------------------------------
    # Logical flags consumed by business logic across modules
    # ------------------------------------------------------------------
    is_active_status = fields.Boolean(
        string='Active Status', default=False, tracking=True,
        help='Check if this status represents an "active" student (currently enrolled).')
    is_graduated_status = fields.Boolean(
        string='Graduated Status', default=False, tracking=True,
        help='Check if this status represents a student who has graduated.')
    is_blocked_status = fields.Boolean(
        string='Blocked Status', default=False, tracking=True,
        help='Check if this status blocks the student from enrollment '
             '(e.g. suspended, withdrawn).')

    # ------------------------------------------------------------------
    # Relations
    # ------------------------------------------------------------------
    student_ids = fields.One2many('uni.student', 'status_id', string='Students')
    student_count = fields.Integer(compute='_compute_student_count', string='Students')

    _sql_constraints = [
        ('unique_student_status_code', 'unique(code)',
         'Student status code must be unique!'),
    ]

    @api.depends('student_ids')
    def _compute_student_count(self):
        for rec in self:
            rec.student_count = len(rec.student_ids)

    def action_open_students(self):
        """Smart-button: open the students currently holding this status."""
        self.ensure_one()
        return {
            'name': _('Students'),
            'type': 'ir.actions.act_window',
            'res_model': 'uni.student',
            'view_mode': 'list,form',
            'domain': [('status_id', '=', self.id)],
            'context': {'default_status_id': self.id},
        }

    def action_toggle_active(self):
        """Toggle the active (archivable) state of the status."""
        for rec in self:
            rec.active = not rec.active
