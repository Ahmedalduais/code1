# -*- coding: utf-8 -*-
from odoo import api, fields, models


class UniGradeLetter(models.Model):
    """التقديرات الحرفية (A+, A, B+...)."""
    _name = 'uni.grade.letter'
    _description = 'Grade Letter'
    _order = 'sequence, gpa_value desc'

    name = fields.Char(string='Grade Letter', required=True, translate=True, index=True)
    code = fields.Char(string='Code', required=True, copy=False, index=True)
    sequence = fields.Integer(string='Sequence', default=10)
    gpa_value = fields.Float(string='GPA Value', required=True, digits=(4, 2),
                             help='The GPA point value for this grade (e.g. 4.0 for A).')
    percentage_min = fields.Float(string='Min %', digits=(5, 2),
                                  help='Minimum percentage for this grade.')
    percentage_max = fields.Float(string='Max %', digits=(5, 2),
                                  help='Maximum percentage for this grade.')
    description = fields.Text(string='Description')
    color = fields.Integer(string='Color Index', default=0)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_grade_letter_code', 'unique(code)', 'Grade letter code must be unique!'),
        ('check_gpa_value_positive', 'check(gpa_value >= 0)',
         'GPA value must be positive or zero!'),
        ('check_percentage_range', 'check(percentage_max >= percentage_min)',
         'Max percentage must be greater than or equal to min percentage!'),
    ]

    @api.model
    def get_grade_for_percentage(self, percentage, system_id=False):
        """الحصول على التقدير المناسب لنسبة معينة."""
        domain = [
            ('percentage_min', '<=', percentage),
            ('percentage_max', '>=', percentage),
            ('active', '=', True),
        ]
        if system_id:
            domain.append(('grading_system_ids', 'in', system_id))
        return self.search(domain, limit=1, order='gpa_value desc')
