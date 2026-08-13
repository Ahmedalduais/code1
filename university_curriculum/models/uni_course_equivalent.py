# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class UniCourseEquivalent(models.Model):
    """المقررات المعادلة — مقررات من برامج/كليات أخرى تُعادل المقرر الحالي
    كلياً أو جزئياً، وتُستخدم عند التحويل بين البرامج.
    """
    _name = 'uni.course.equivalent'
    _description = 'Course Equivalent'
    _order = 'course_id, equivalence_type, id'
    _rec_name = 'equivalent_course_id'

    course_id = fields.Many2one('uni.course', string='Course',
                                required=True, ondelete='cascade', index=True)
    equivalent_course_id = fields.Many2one('uni.course', string='Equivalent Course',
                                           required=True, ondelete='restrict', index=True)
    equivalent_course_code = fields.Char(related='equivalent_course_id.code',
                                         string='Equivalent Code', store=True)
    equivalence_type = fields.Selection([
        ('full', 'Full'),
        ('partial', 'Partial'),
    ], string='Equivalence Type', default='full', required=True, tracking=True)
    equivalent_credit_hours = fields.Float(string='Equivalent Credit Hours',
                                           help='Number of credit hours granted from the '
                                                'equivalent course when transferred.')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(default=True)
    note = fields.Text(string='Note')

    _sql_constraints = [
        ('unique_equivalent',
         'unique(course_id, equivalent_course_id)',
         'The same equivalent course cannot be added twice to a course!'),
        ('check_credit_hours_positive',
         'check(equivalent_credit_hours >= 0)',
         'Equivalent credit hours must be positive or zero!'),
    ]

    @api.constrains('course_id', 'equivalent_course_id')
    def _check_not_self(self):
        """لا يمكن للمقرر أن يكون معادلاً لنفسه."""
        for rec in self:
            if rec.course_id.id == rec.equivalent_course_id.id:
                raise ValidationError(_(
                    'A course cannot be equivalent to itself.'))
