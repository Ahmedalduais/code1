# -*- coding: utf-8 -*-
from odoo import fields, models


class UniProgramCourseLine(models.Model):
    """خطوط ربط المقرر بالبرنامج — تفاصيل إضافية لربط المقرر بالبرنامج،
    مثل وحدات فرعية، أنشطة، أو متطلبات خاصة.
    """
    _name = 'uni.program.course.line'
    _description = 'Program Course Line'
    _order = 'program_course_id, sequence, id'
    _rec_name = 'name'

    program_course_id = fields.Many2one('uni.program.course', string='Program-Course',
                                        required=True, ondelete='cascade', index=True)
    program_id = fields.Many2one('uni.program', string='Program',
                                 related='program_course_id.program_id', store=True, index=True)
    course_id = fields.Many2one('uni.course', string='Course',
                                related='program_course_id.course_id', store=True, index=True)
    name = fields.Char(string='Title', required=True, translate=True)
    description = fields.Text(string='Description')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(default=True)
