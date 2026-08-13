# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniExamType(models.Model):
    """نوع الامتحان — يحدد الخصائص الافتراضية للامتحانات.

    يُستخدم هذا النموذج كقالب افتراضي عند إنشاء امتحان جديد: المدة، الدرجة
    العظمى، الوزن في المعدل، نسبة النجاح، طبيعة الامتحان (تحريري/شفهي/عملي...).

    كما يوفّر مؤشّرين منطقيّين ``is_final`` و ``is_midterm`` لتبسيط الفلترة
    في التقارير وقوائم الامتحانات.
    """
    _name = 'uni.exam.type'
    _description = 'Exam Type'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Name', required=True, translate=True, tracking=True,
        help='Display name of the exam type, e.g. "Final Exam".')
    code = fields.Char(
        string='Code', required=True, copy=False, index=True, tracking=True,
        help='Short unique code identifying the exam type.')
    description = fields.Text(string='Description', translate=True)
    sequence = fields.Integer(string='Sequence', default=10, index=True)
    active = fields.Boolean(string='Active', default=True)

    # ------------------------------------------------------------------
    # Exam nature & defaults
    # ------------------------------------------------------------------
    exam_nature = fields.Selection([
        ('written', 'Written'),
        ('oral', 'Oral'),
        ('practical', 'Practical'),
        ('online', 'Online'),
        ('mixed', 'Mixed'),
    ], string='Exam Nature', default='written', required=True, tracking=True,
        help='Delivery mode of the exam.')
    default_duration = fields.Float(
        string='Default Duration', default=2.0,
        widget='float_time', tracking=True,
        help='Default duration in hours (e.g. 2.0 = 2 hours, 1.5 = 1h30).')
    default_max_score = fields.Float(
        string='Default Max Score', default=100.0, tracking=True,
        help='Default maximum score for exams of this type.')
    weight_percentage = fields.Float(
        string='Weight (%)', default=30.0, tracking=True,
        help='Default weight of this exam type in the course final grade (percentage).')
    passing_percentage = fields.Float(
        string='Passing (%)', default=50.0, tracking=True,
        help='Default minimum percentage required to pass an exam of this type.')

    # ------------------------------------------------------------------
    # Type flags
    # ------------------------------------------------------------------
    is_final = fields.Boolean(
        string='Is Final', default=False, tracking=True,
        help='Check if exams of this type are considered final exams.')
    is_midterm = fields.Boolean(
        string='Is Midterm', default=False, tracking=True,
        help='Check if exams of this type are considered midterm exams.')

    # ------------------------------------------------------------------
    # Relations
    # ------------------------------------------------------------------
    exam_ids = fields.One2many(
        'uni.exam', 'exam_type_id', string='Exams')
    exam_count = fields.Integer(
        compute='_compute_exam_count', string='Exams Count')

    _sql_constraints = [
        ('unique_code', 'unique(code)',
         'Exam type code must be unique!'),
        ('check_default_duration', 'check(default_duration >= 0)',
         'Default duration cannot be negative!'),
        ('check_default_max_score', 'check(default_max_score >= 0)',
         'Default max score cannot be negative!'),
        ('check_weight_percentage', 'check(weight_percentage >= 0 AND weight_percentage <= 100)',
         'Weight percentage must be between 0 and 100!'),
        ('check_passing_percentage', 'check(passing_percentage >= 0 AND passing_percentage <= 100)',
         'Passing percentage must be between 0 and 100!'),
    ]

    # ------------------------------------------------------------------
    # Computed
    # ------------------------------------------------------------------
    @api.depends('exam_ids')
    def _compute_exam_count(self):
        for rec in self:
            rec.exam_count = len(rec.exam_ids)

    # ------------------------------------------------------------------
    # Smart-button action
    # ------------------------------------------------------------------
    def action_open_exams(self):
        self.ensure_one()
        return {
            'name': _('Exams'),
            'type': 'ir.actions.act_window',
            'res_model': 'uni.exam',
            'view_mode': 'list,form',
            'domain': [('exam_type_id', '=', self.id)],
            'context': {'default_exam_type_id': self.id},
        }

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('is_final', 'is_midterm')
    def _check_final_xor_midterm(self):
        """An exam type cannot be both final and midterm at the same time."""
        for rec in self:
            if rec.is_final and rec.is_midterm:
                raise ValidationError(_(
                    "Exam type '%s' cannot be both Final and Midterm at the same time.")
                    % rec.display_name)
