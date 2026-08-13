# -*- coding: utf-8 -*-
from odoo import api, fields, models


class UniCourseOutcome(models.Model):
    """نواتج التعلم المتوقعة من المقرر — مرتبطة بمستويات بلوم المعرفية."""
    _name = 'uni.course.outcome'
    _description = 'Course Learning Outcome'
    _order = 'course_id, sequence, id'
    _rec_name = 'name'

    course_id = fields.Many2one('uni.course', string='Course',
                                required=True, ondelete='cascade', index=True)
    name = fields.Char(string='Outcome', required=True, translate=True)
    description = fields.Text(string='Description')
    outcome_type = fields.Selection([
        ('knowledge', 'Knowledge'),
        ('skill', 'Skill'),
        ('attitude', 'Attitude'),
    ], string='Outcome Type', default='knowledge', required=True, index=True)
    bloom_level = fields.Selection([
        ('remember', 'Remember'),
        ('understand', 'Understand'),
        ('apply', 'Apply'),
        ('analyze', 'Analyze'),
        ('evaluate', 'Evaluate'),
        ('create', 'Create'),
    ], string='Bloom Level', default='understand', required=True, index=True,
       help='Bloom\'s taxonomy cognitive level.')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(default=True)
