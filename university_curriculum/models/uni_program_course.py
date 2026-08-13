# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class UniProgramCourse(models.Model):
    """ربط المقرر بالبرنامج — يحدد متى يُدرَّس المقرر داخل برنامج معين،
    ومستواه (السنة)، والفصل، وعدد ساعاته الائتمانية، وما إذا كان إجبارياً.
    """
    _name = 'uni.program.course'
    _description = 'Program-Course Link'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'program_id, level, semester, sequence'

    program_id = fields.Many2one('uni.program', string='Program',
                                 required=True, ondelete='restrict', tracking=True, index=True)
    course_id = fields.Many2one('uni.course', string='Course',
                                required=True, ondelete='restrict', tracking=True, index=True)
    university_id = fields.Many2one('uni.university', string='University',
                                    related='program_id.university_id', store=True, index=True)
    college_id = fields.Many2one('uni.college', string='College',
                                 related='program_id.college_id', store=True, index=True)
    department_id = fields.Many2one('uni.department', string='Department',
                                    related='program_id.department_id', store=True, index=True)
    level = fields.Selection([
        ('1', 'Year 1'),
        ('2', 'Year 2'),
        ('3', 'Year 3'),
        ('4', 'Year 4'),
        ('5', 'Year 5'),
        ('6', 'Year 6'),
        ('7', 'Year 7'),
        ('8', 'Year 8'),
    ], string='Year Level', default='1', required=True, tracking=True, index=True)
    semester = fields.Integer(string='Semester (within year)', default=1,
                              help='Semester number within the academic year (1, 2, 3...).')
    credit_hours = fields.Float(string='Credit Hours', default=0.0,
                                help='Override program-level credit hours for this course in '
                                     'this program. Leave 0 to use the course default.')
    effective_credit_hours = fields.Float(string='Effective Credit Hours',
                                          compute='_compute_effective_credit_hours',
                                          store=True,
                                          help='Actual credit hours used (program override or '
                                               'course default).')
    is_mandatory = fields.Boolean(string='Mandatory', default=True, tracking=True,
                                  help='If checked, this course is mandatory in the program; '
                                       'otherwise it is an elective.')
    sequence = fields.Integer(string='Sequence', default=10)
    notes = fields.Text(string='Notes')

    prerequisite_course_ids = fields.Many2many('uni.course',
                                               'uni_program_course_prerequisite_rel',
                                               'program_course_id', 'course_id',
                                               string='Prerequisite Courses',
                                               help='Courses that must be completed before '
                                                    'enrolling in this course within the program.')
    line_ids = fields.One2many('uni.program.course.line', 'program_course_id',
                               string='Lines', copy=True)
    line_count = fields.Integer(compute='_compute_line_count', string='Lines')

    _sql_constraints = [
        ('unique_program_course',
         'unique(program_id, course_id)',
         'The same course cannot be linked twice to the same program!'),
        ('check_semester_positive',
         'check(semester > 0)',
         'Semester must be greater than zero!'),
        ('check_credit_hours_positive',
         'check(credit_hours >= 0)',
         'Credit hours must be positive or zero!'),
    ]

    @api.depends('credit_hours', 'course_id.credit_hours')
    def _compute_effective_credit_hours(self):
        for rec in self:
            rec.effective_credit_hours = rec.credit_hours or (rec.course_id.credit_hours or 0.0)

    @api.depends('line_ids')
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    @api.onchange('course_id')
    def _onchange_course_id(self):
        """عند اختيار المقرر، يُعبَّأ حقل الساعات الائتمانية افتراضياً."""
        if self.course_id and not self.credit_hours:
            self.credit_hours = self.course_id.credit_hours

    @api.constrains('course_id', 'prerequisite_course_ids')
    def _check_prerequisites_not_self(self):
        """لا يمكن أن يكون المقرر متطلباً سابقاً لنفسه ضمن البرنامج."""
        for rec in self:
            if rec.course_id in rec.prerequisite_course_ids:
                raise ValidationError(_(
                    'Course %s cannot be a prerequisite of itself in program %s.',
                    rec.course_id.display_name, rec.program_id.display_name))

    def action_view_lines(self):
        """فتح سجل خطوط ربط المقرر بالبرنامج."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Lines'),
            'res_model': 'uni.program.course.line',
            'view_mode': 'list,form',
            'domain': [('program_course_id', '=', self.id)],
            'context': {'default_program_course_id': self.id},
        }
