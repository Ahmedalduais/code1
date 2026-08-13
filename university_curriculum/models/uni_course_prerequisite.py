# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class UniCoursePrerequisite(models.Model):
    """المتطلبات السابقة للمقرر — مقرر يجب اجتيازه (بتقدير معين أحياناً)
    قبل التسجيل في المقرر الحالي.
    """
    _name = 'uni.course.prerequisite'
    _description = 'Course Prerequisite'
    _order = 'course_id, sequence, id'
    _rec_name = 'prerequisite_course_id'

    course_id = fields.Many2one('uni.course', string='Course',
                                required=True, ondelete='cascade', index=True)
    prerequisite_course_id = fields.Many2one('uni.course', string='Prerequisite Course',
                                             required=True, ondelete='restrict', index=True)
    prerequisite_course_code = fields.Char(related='prerequisite_course_id.code',
                                           string='Prerequisite Code', store=True)
    minimum_grade = fields.Char(
        string='Minimum Grade',
        help='Minimum grade letter required in the prerequisite course '
             '(e.g. C, D, Pass). Leave empty for any passing grade.')
    is_strict = fields.Boolean(string='Strict', default=True,
                               help='If checked, the prerequisite is strictly enforced during '
                                    'registration; otherwise it is a recommendation.')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(default=True)
    note = fields.Text(string='Note')

    _sql_constraints = [
        ('unique_prerequisite',
         'unique(course_id, prerequisite_course_id)',
         'The same prerequisite course cannot be added twice to a course!'),
    ]

    @api.constrains('course_id', 'prerequisite_course_id')
    def _check_not_self(self):
        """لا يمكن للمقرر أن يكون متطلباً سابقاً لنفسه."""
        for rec in self:
            if rec.course_id.id == rec.prerequisite_course_id.id:
                raise ValidationError(_(
                    'A course cannot be a prerequisite of itself.'))
