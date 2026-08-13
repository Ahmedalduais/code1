# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class UniCourse(models.Model):
    """المقرر الدراسي — الكيان الأساسي للمناهج.

    يمثل مقرراً دراسياً مرتبطاً بكلية وقسم، وله حالة دورة حياة،
    ونواتج تعلم، وتوصيف، ومتطلبات سابقة، ومقررات معادلة.
    """
    _name = 'uni.course'
    _description = 'Course'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'college_id, code'

    name = fields.Char(string='Course Name', required=True, tracking=True, translate=True, index=True)
    code = fields.Char(string='Course Code', required=True, copy=False, tracking=True, index=True,
                       help='Unique code per college for this course.')
    university_id = fields.Many2one('uni.university', string='University',
                                    required=True, ondelete='restrict', tracking=True, index=True)
    college_id = fields.Many2one('uni.college', string='College',
                                 required=True, ondelete='restrict', tracking=True, index=True)
    department_id = fields.Many2one('uni.department', string='Department',
                                    ondelete='restrict', tracking=True, index=True)
    branch_id = fields.Many2one('uni.branch', string='Branch',
                                related='college_id.branch_id', store=True, tracking=True)
    credit_hours = fields.Float(string='Credit Hours', default=3.0, tracking=True,
                                help='Number of credit hours awarded for completing this course.')
    contact_hours = fields.Float(string='Contact Hours', default=3.0, tracking=True,
                                 help='Total contact hours per term (lecture + lab + tutorial).')
    course_type = fields.Selection([
        ('mandatory', 'Mandatory'),
        ('elective', 'Elective'),
        ('free_elective', 'Free Elective'),
    ], string='Course Type', default='mandatory', tracking=True, index=True)
    course_type_id = fields.Many2one('uni.course.type', string='Course Nature Type',
                                     ondelete='restrict', tracking=True, index=True,
                                     help='Classifies the course by nature (theoretical, '
                                          'practical, hybrid, etc.) — distinct from the '
                                          'mandatory/elective Course Type field above.')
    delivery_id = fields.Many2one('uni.course.delivery', string='Delivery Mode',
                                  ondelete='restrict', tracking=True, index=True,
                                  help='How the course is delivered (on-campus, online, '
                                       'hybrid, etc.)')
    level = fields.Selection([
        ('undergraduate', 'Undergraduate'),
        ('postgraduate', 'Postgraduate'),
    ], string='Level', default='undergraduate', tracking=True, index=True)
    description = fields.Html(string='Description')
    objectives = fields.Html(string='Objectives')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('closed', 'Closed'),
    ], string='Status', default='draft', tracking=True, group_expand='_group_expand_states')
    coordinator_id = fields.Many2one('res.partner', string='Course Coordinator', tracking=True)
    notes = fields.Text(string='Notes')

    # One2many relations
    prerequisite_ids = fields.One2many('uni.course.prerequisite', 'course_id', string='Prerequisites')
    equivalent_ids = fields.One2many('uni.course.equivalent', 'course_id', string='Equivalents')
    outcome_ids = fields.One2many('uni.course.outcome', 'course_id', string='Learning Outcomes')
    syllabus_ids = fields.One2many('uni.course.syllabus', 'course_id', string='Syllabus')
    program_course_ids = fields.One2many('uni.program.course', 'course_id', string='Program Links')
    evaluation_ids = fields.One2many('uni.course.evaluation', 'course_id', string='Evaluations')

    # Computed helpers
    program_count = fields.Integer(compute='_compute_program_count', string='Programs')
    total_syllabus_hours = fields.Float(compute='_compute_total_syllabus_hours',
                                        string='Total Syllabus Hours')

    _sql_constraints = [
        ('unique_course_code_college', 'unique(college_id, code)',
         'Course code must be unique per college!'),
        ('check_credit_hours_positive', 'check(credit_hours >= 0)',
         'Credit hours must be positive or zero!'),
        ('check_contact_hours_positive', 'check(contact_hours >= 0)',
         'Contact hours must be positive or zero!'),
    ]

    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in states]

    @api.depends('program_course_ids')
    def _compute_program_count(self):
        for rec in self:
            rec.program_count = len(rec.program_course_ids)

    @api.depends('syllabus_ids.hours')
    def _compute_total_syllabus_hours(self):
        for rec in self:
            rec.total_syllabus_hours = sum(rec.syllabus_ids.mapped('hours'))

    @api.onchange('college_id')
    def _onchange_college_id(self):
        """عند اختيار الكلية، يُحدَّد الذراع الجامعي تلقائياً."""
        if self.college_id:
            self.university_id = self.college_id.university_id

    @api.onchange('department_id')
    def _onchange_department_id(self):
        """عند اختيار القسم، تُحدَّد الكلية والجامعة تلقائياً."""
        if self.department_id:
            self.college_id = self.department_id.college_id
            self.university_id = self.department_id.university_id

    @api.constrains('prerequisite_ids')
    def _check_prerequisites_not_self(self):
        """لا يُسمح بأن يكون المقرر متطلباً سابقاً لنفسه."""
        for rec in self:
            for prereq in rec.prerequisite_ids:
                if prereq.prerequisite_course_id.id == rec.id:
                    raise ValidationError(_(
                        'A course cannot be a prerequisite of itself (course: %s).',
                        rec.display_name))

    @api.constrains('equivalent_ids')
    def _check_equivalents_not_self(self):
        """لا يُسمح بأن يكون المقرر معادلاً لنفسه."""
        for rec in self:
            for equiv in rec.equivalent_ids:
                if equiv.equivalent_course_id.id == rec.id:
                    raise ValidationError(_(
                        'A course cannot be equivalent to itself (course: %s).',
                        rec.display_name))

    @api.constrains('credit_hours', 'contact_hours')
    def _check_hours_consistency(self):
        """ساعات الاتصال يجب ألا تقل عن ساعات الائتمان (قاعدة مرنة)."""
        for rec in self:
            if rec.contact_hours and rec.credit_hours and rec.contact_hours < rec.credit_hours:
                raise ValidationError(_(
                    'Contact hours (%s) cannot be less than credit hours (%s) for course %s.',
                    rec.contact_hours, rec.credit_hours, rec.display_name))

    def action_activate(self):
        """تفعيل المقرر."""
        for rec in self:
            rec.state = 'active'

    def action_suspend(self):
        """تعليق المقرر مؤقتاً."""
        for rec in self:
            rec.state = 'suspended'

    def action_close(self):
        """إغلاق المقرر نهائياً."""
        for rec in self:
            rec.state = 'closed'

    def action_draft(self):
        """إعادة المقرر إلى حالة المسودة."""
        for rec in self:
            rec.state = 'draft'

    def action_view_program_links(self):
        """فتح سجل ربط المقرر بالبرامج."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Program Links'),
            'res_model': 'uni.program.course',
            'view_mode': 'list,form',
            'domain': [('course_id', '=', self.id)],
            'context': {'default_course_id': self.id,
                        'default_university_id': self.university_id.id,
                        'default_college_id': self.college_id.id},
        }
