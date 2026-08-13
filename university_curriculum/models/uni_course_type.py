# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class UniCourseType(models.Model):
    """Course Type (Nature) — classifies a course by its pedagogical nature
    (theoretical, practical, hybrid, clinical, laboratory, etc.).

    This is distinct from the `course_type` Selection field on uni.course,
    which classifies the mandatory/elective dimension.
    """
    _name = 'uni.course.type'
    _description = 'Course Type (Nature)'
    _order = 'sequence, name'

    name = fields.Char(string='Type Name', required=True, translate=True)
    code = fields.Char(string='Code', required=True, copy=False, index=True)
    sequence = fields.Integer(string='Sequence', default=10)

    course_nature = fields.Selection([
        ('theoretical', 'Theoretical'),
        ('practical', 'Practical'),
        ('hybrid', 'Hybrid (Theory + Practice)'),
        ('clinical', 'Clinical'),
        ('laboratory', 'Laboratory'),
        ('field_work', 'Field Work'),
        ('seminar', 'Seminar'),
        ('research', 'Research'),
        ('project', 'Project'),
    ], string='Course Nature', required=True, tracking=True)

    default_credit_hours = fields.Integer(string='Default Credit Hours', default=3)
    default_contact_hours = fields.Integer(string='Default Contact Hours', default=45)
    default_weeks = fields.Integer(string='Default Weeks', default=16)

    has_lab = fields.Boolean(string='Has Lab Component', default=False)
    has_clinical = fields.Boolean(string='Has Clinical Component', default=False)
    has_field_work = fields.Boolean(string='Has Field Work Component', default=False)
    has_research = fields.Boolean(string='Has Research Component', default=False)

    lab_hours = fields.Integer(string='Lab Hours', default=0)
    theory_hours = fields.Integer(string='Theory Hours', default=0)
    practice_hours = fields.Integer(string='Practice Hours', default=0)

    grading_weight = fields.Float(string='Grading Weight', default=1.0,
                                   help='Weight multiplier for GPA calculation '
                                        '(e.g., lab courses may weigh differently).')

    description = fields.Text(string='Description')
    color = fields.Integer(string='Color Index', default=0)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_course_type_code', 'unique(code)',
         'Course type code must be unique!'),
    ]

    def action_apply_defaults_to_courses(self):
        """Apply the default credit/contact hours to all courses of this type.

        Useful when configuring a new course type and wanting to backfill
        existing courses that share the same nature.
        """
        for rec in self:
            courses = self.env['uni.course'].search([('course_type_id', '=', rec.id)])
            for course in courses:
                if not course.credit_hours:
                    course.credit_hours = rec.default_credit_hours
                if not course.contact_hours:
                    course.contact_hours = rec.default_contact_hours
        return True
