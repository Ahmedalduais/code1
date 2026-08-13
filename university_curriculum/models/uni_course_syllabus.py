# -*- coding: utf-8 -*-
from odoo import api, fields, models


class UniCourseSyllabus(models.Model):
    """توصيف المقرر الأسبوعي — يفصّل محتوى المقرر حسب الأسابيع."""
    _name = 'uni.course.syllabus'
    _description = 'Course Syllabus'
    _order = 'course_id, week_number, sequence'
    _rec_name = 'name'

    course_id = fields.Many2one('uni.course', string='Course',
                                required=True, ondelete='cascade', index=True)
    name = fields.Char(string='Topic Title', required=True, translate=True)
    week_number = fields.Integer(string='Week', default=1,
                                 help='Week number within the term.')
    topic = fields.Text(string='Topic Summary')
    content = fields.Html(string='Detailed Content')
    teaching_methods = fields.Text(string='Teaching Methods',
                                   help='e.g. lecture, lab, case study, flipped classroom.')
    assessment_methods = fields.Text(string='Assessment Methods',
                                     help='e.g. quiz, assignment, midterm, project.')
    hours = fields.Float(string='Contact Hours', default=2.0,
                         help='Contact hours allocated to this week.')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('check_week_number_positive',
         'check(week_number > 0)',
         'Week number must be greater than zero!'),
        ('check_hours_positive',
         'check(hours >= 0)',
         'Contact hours must be positive or zero!'),
    ]
