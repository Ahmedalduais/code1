# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniExamInvigilator(models.Model):
    """المراقب — الشخص المكلف بمراقبة الامتحانات.

    يمكن أن يكون المراقب موظفاً (``hr.employee``) أو مجرد شخص خارجي
    تُسجل بياناته يدوياً (الاسم، الهاتف، البريد). اسم عضو هيئة التدريس
    يُسجل كنص حر (``faculty_name``) لتجنّب الاعتماد على ``university_faculty``.

    يُربط المراقب بالامتحانات التي يراقبها عبر حقل ``assigned_exam_ids``،
    ويُحمل مؤشر ``is_available`` لتبسيط الفلترة عند توزيع المراقبين.
    """
    _name = 'uni.exam.invigilator'
    _description = 'Exam Invigilator'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Name', required=True, translate=True, tracking=True,
        help='Display name of the invigilator.')
    code = fields.Char(
        string='Code', copy=False, index=True, tracking=True,
        help='Optional code identifying the invigilator.')
    active = fields.Boolean(string='Active', default=True)

    # ------------------------------------------------------------------
    # Affiliation
    # ------------------------------------------------------------------
    faculty_name = fields.Char(
        string='Faculty Name', tracking=True, index=True,
        help='Name of the faculty member acting as invigilator (optional). '
             'Stored as plain text to avoid a hard dependency on '
             'university_faculty.')
    employee_id = fields.Many2one(
        'hr.employee', string='Employee', ondelete='restrict',
        tracking=True, index=True,
        help='Employee acting as invigilator (optional).')

    # ------------------------------------------------------------------
    # Role & contact
    # ------------------------------------------------------------------
    role = fields.Selection([
        ('chief_invigilator', 'Chief Invigilator'),
        ('assistant', 'Assistant'),
        ('observer', 'Observer'),
    ], string='Role', default='assistant', required=True, tracking=True, index=True)
    phone = fields.Char(string='Phone', tracking=True)
    email = fields.Char(string='Email', tracking=True)

    # ------------------------------------------------------------------
    # Availability & relations
    # ------------------------------------------------------------------
    is_available = fields.Boolean(
        string='Available', default=True, tracking=True,
        help='Indicates whether the invigilator is currently available for assignment.')
    assigned_exam_ids = fields.Many2many(
        'uni.exam', string='Assigned Exams',
        help='Exams to which this invigilator has been assigned.')
    assigned_exam_count = fields.Integer(
        compute='_compute_assigned_exam_count', string='Exams Count')

    _sql_constraints = [
        ('unique_code', 'unique(code)',
         'Invigilator code must be unique!'),
    ]

    # ------------------------------------------------------------------
    # Onchange — prefill from employee
    # ------------------------------------------------------------------
    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            if not self.name:
                self.name = self.employee_id.display_name
            if not self.phone and self.employee_id.work_phone:
                self.phone = self.employee_id.work_phone
            if not self.email and self.employee_id.work_email:
                self.email = self.employee_id.work_email

    # ------------------------------------------------------------------
    # Computed
    # ------------------------------------------------------------------
    @api.depends('assigned_exam_ids')
    def _compute_assigned_exam_count(self):
        for rec in self:
            rec.assigned_exam_count = len(rec.assigned_exam_ids)

    # ------------------------------------------------------------------
    # Smart-button action
    # ------------------------------------------------------------------
    def action_open_assigned_exams(self):
        self.ensure_one()
        return {
            'name': _('Assigned Exams'),
            'type': 'ir.actions.act_window',
            'res_model': 'uni.exam',
            'view_mode': 'list,form',
            'domain': [('invigilator_ids', 'in', self.id)],
        }

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    # (Previously a cross-affiliation constraint between faculty_id and
    # employee_id lived here. It was removed because ``faculty_id`` has been
    # converted to the plain-text ``faculty_name`` field to avoid a hard
    # dependency on ``university_faculty``; cross-checking a Char against an
    # ``hr.employee`` is not meaningful.)
