# -*- coding: utf-8 -*-
from odoo import api, fields, models


class UniGradeConversion(models.Model):
    """جدول التحويل بين أنظمة الدرجات المختلفة."""
    _name = 'uni.grade.conversion'
    _description = 'Grade Conversion'
    _order = 'from_system_id, to_system_id'

    name = fields.Char(string='Conversion Name', compute='_compute_name', store=True)
    from_system_id = fields.Many2one('uni.grading.system', string='From System',
                                     required=True, ondelete='restrict', index=True)
    to_system_id = fields.Many2one('uni.grading.system', string='To System',
                                   required=True, ondelete='restrict', index=True)
    from_grade_letter_id = fields.Many2one('uni.grade.letter', string='From Grade',
                                           required=True, ondelete='restrict', index=True)
    to_grade_letter_id = fields.Many2one('uni.grade.letter', string='To Grade',
                                         required=True, ondelete='restrict', index=True)
    from_value_min = fields.Float(string='From Min', digits=(5, 2))
    from_value_max = fields.Float(string='From Max', digits=(5, 2))
    to_value = fields.Float(string='To Value', digits=(5, 2))
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_conversion',
         'unique(from_system_id, to_system_id, from_grade_letter_id)',
         'Conversion rule already exists for this combination!'),
        ('check_different_systems', 'check(from_system_id != to_system_id)',
         'Source and target systems must be different!'),
    ]

    @api.depends('from_system_id', 'to_system_id', 'from_grade_letter_id')
    def _compute_name(self):
        for rec in self:
            from_name = rec.from_system_id.name or ''
            to_name = rec.to_system_id.name or ''
            grade = rec.from_grade_letter_id.code or ''
            rec.name = f"{from_name} → {to_name} ({grade})"

    @api.model
    def convert_grade(self, from_system_id, to_system_id, grade_letter_id):
        """تحويل تقدير من نظام إلى آخر."""
        conversion = self.search([
            ('from_system_id', '=', from_system_id),
            ('to_system_id', '=', to_system_id),
            ('from_grade_letter_id', '=', grade_letter_id),
            ('active', '=', True),
        ], limit=1)
        return conversion.to_grade_letter_id if conversion else False
