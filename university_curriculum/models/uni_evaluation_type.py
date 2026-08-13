# -*- coding: utf-8 -*-
from odoo import api, fields, models


class UniEvaluationType(models.Model):
    """أنواع التقييم — قائمة بأنواع التقييمات المستخدمة داخل المقررات
    (اختبار نهائي، اختبار نصفي، واجب، اختبار قصير، مشروع... إلخ).
    """
    _name = 'uni.evaluation.type'
    _description = 'Evaluation Type'
    _order = 'sequence, name'

    name = fields.Char(string='Name', required=True, translate=True, index=True)
    code = fields.Char(string='Code', required=True, copy=False, index=True)
    description = fields.Text(string='Description')
    weight_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('points', 'Points'),
    ], string='Weight Type', default='percentage', required=True,
       help='Whether weights are recorded as percentages (out of 100) or as points.')
    default_weight = fields.Float(string='Default Weight', default=0.0,
                                  help='Default weight applied when this evaluation type is '
                                       'added to a course evaluation item.')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_evaluation_type_code',
         'unique(code)',
         'Evaluation type code must be unique!'),
    ]
