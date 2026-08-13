# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniLmsCourse(models.Model):
    """المقرر الإلكتروني — نسخة LMS من المقرر الأكاديمي.

    يربط المقرر الدراسي (uni.course) بمحتوى التعلم الإلكتروني:
    وحدات المحتوى، الواجبات، الاختبارات، المنتديات، وتقدم الطلاب.
    """
    _name = 'uni.lms.course'
    _description = 'LMS Course'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'academic_term_id desc, code, id'

    name = fields.Char(string='Reference', required=True, copy=False, tracking=True,
                       default=lambda self: _('New'), index=True,
                       help='Auto-generated sequence reference (LMS/...).')
    code = fields.Char(string='LMS Code', copy=False, tracking=True, index=True,
                       help='Optional human-friendly short code for the LMS course.')
    course_id = fields.Many2one('uni.course', string='Academic Course',
                                required=True, ondelete='restrict', tracking=True, index=True)
    academic_term_id = fields.Many2one('uni.academic.term', string='Academic Term',
                                       ondelete='restrict', tracking=True, index=True)
    faculty_name = fields.Char(
        string='Instructor Name', copy=False, tracking=True, index=True,
        help='Free-text instructor name (the LMS module does not depend on '
             'university_faculty, so the instructor is recorded as a string).')
    university_id = fields.Many2one('uni.university', string='University',
                                    related='course_id.university_id', store=True, index=True)
    college_id = fields.Many2one('uni.college', string='College',
                                 related='course_id.college_id', store=True, index=True)
    department_id = fields.Many2one('uni.department', string='Department',
                                    related='course_id.department_id', store=True, index=True)
    branch_id = fields.Many2one('uni.branch', string='Branch',
                                related='course_id.branch_id', store=True)
    description = fields.Text(string='Short Description')
    cover_image = fields.Image(string='Cover Image', max_width=1280, max_height=720)
    introduction = fields.Html(string='Introduction')
    objectives = fields.Text(string='Objectives')
    prerequisites = fields.Text(string='Prerequisites',
                                help='Free-text description of required prior knowledge.')
    start_date = fields.Date(string='Start Date', tracking=True)
    end_date = fields.Date(string='End Date', tracking=True)
    enrollment_open = fields.Boolean(string='Open for Enrollment', default=True, tracking=True)
    max_students = fields.Integer(string='Maximum Students', default=0,
                                  help='Set to 0 for unlimited enrollment.')

    content_ids = fields.One2many('uni.lms.content', 'lms_course_id', string='Content')
    assignment_ids = fields.One2many('uni.lms.assignment', 'lms_course_id', string='Assignments')
    quiz_ids = fields.One2many('uni.lms.quiz', 'lms_course_id', string='Quizzes')
    forum_ids = fields.One2many('uni.lms.forum', 'lms_course_id', string='Forums')
    progress_ids = fields.One2many('uni.lms.progress', 'lms_course_id', string='Student Progress')

    content_count = fields.Integer(compute='_compute_content_count', string='Contents')
    assignment_count = fields.Integer(compute='_compute_assignment_count', string='Assignments')
    quiz_count = fields.Integer(compute='_compute_quiz_count', string='Quizzes')
    forum_count = fields.Integer(compute='_compute_forum_count', string='Forums')
    enrolled_count = fields.Integer(compute='_compute_enrolled', string='Enrolled',
                                    help='Number of active student progress records.')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ], string='Status', default='draft', tracking=True, group_expand='_group_expand_states')
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('unique_lms_course_term',
         'unique(course_id, academic_term_id)',
         'An LMS course already exists for this academic course in this term!'),
    ]

    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in states]

    @api.depends('content_ids')
    def _compute_content_count(self):
        for rec in self:
            rec.content_count = len(rec.content_ids)

    @api.depends('assignment_ids')
    def _compute_assignment_count(self):
        for rec in self:
            rec.assignment_count = len(rec.assignment_ids)

    @api.depends('quiz_ids')
    def _compute_quiz_count(self):
        for rec in self:
            rec.quiz_count = len(rec.quiz_ids)

    @api.depends('forum_ids')
    def _compute_forum_count(self):
        for rec in self:
            rec.forum_count = len(rec.forum_ids)

    @api.depends('progress_ids', 'progress_ids.state')
    def _compute_enrolled(self):
        """عدد الطلاب المسجلين (غير المُسقطين) في المقرر الإلكتروني."""
        for rec in self:
            rec.enrolled_count = len(rec.progress_ids.filtered(
                lambda p: p.state in ('enrolled', 'in_progress', 'completed')))

    @api.model_create_multi
    def create(self, vals_list):
        """إنشاء تسلسل تلقائي LMS/... عند إنشاء مقرر إلكتروني جديد."""
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.lms.course') or _('New')
        return super().create(vals_list)

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        """تاريخ النهاية يجب أن يكون بعد تاريخ البداية (إن وُجدا)."""
        for rec in self:
            if rec.start_date and rec.end_date and rec.start_date > rec.end_date:
                raise ValidationError(_(
                    'End date (%s) must be after start date (%s) for LMS course %s.',
                    rec.end_date, rec.start_date, rec.display_name))

    @api.constrains('max_students')
    def _check_max_students(self):
        """الحد الأقصى للطلاب لا يمكن أن يكون سالباً."""
        for rec in self:
            if rec.max_students < 0:
                raise ValidationError(_(
                    'Maximum students cannot be negative for LMS course %s.',
                    rec.display_name))

    @api.constrains('enrolled_count', 'max_students', 'enrollment_open')
    def _check_enrollment_capacity(self):
        """لا يُسمح بفتح التسجيل تجاوزاً للسعة القصوى (عند تفعيلها)."""
        for rec in self:
            if rec.max_students > 0 and rec.enrolled_count > rec.max_students:
                raise ValidationError(_(
                    'LMS course %s is full (%s/%s students).',
                    rec.display_name, rec.enrolled_count, rec.max_students))

    def action_publish(self):
        """نشر المقرر الإلكتروني ليصبح متاحاً للطلاب."""
        for rec in self:
            if not rec.course_id:
                raise ValidationError(_(
                    'Cannot publish LMS course %s without a linked academic course.',
                    rec.display_name))
            rec.state = 'published'

    def action_archive(self):
        """أرشفة المقرر الإلكتروني (يصبح مخفياً من البحث الافتراضي وللقراءة فقط).

        يتم تحديث الحالة إلى ``archived`` مع تطبيق سلوك الأرشفة القياسي
        من ``uni.mixin.archivable`` (تعيين ``active=False`` وتسجيل
        التاريخ والمستخدم).
        """
        res = super().action_archive()
        for rec in self:
            rec.state = 'archived'
        return res

    def action_unarchive(self):
        """إلغاء أرشفة المقرر الإلكتروني — يعيده إلى حالة المسودة."""
        res = super().action_unarchive()
        for rec in self:
            if rec.state == 'archived':
                rec.state = 'draft'
        return res

    def action_draft(self):
        """إعادة المقرر إلى حالة المسودة."""
        for rec in self:
            rec.state = 'draft'

    def action_view_contents(self):
        """فتح سجل محتوى المقرر."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Course Content'),
            'res_model': 'uni.lms.content',
            'view_mode': 'list,form',
            'domain': [('lms_course_id', '=', self.id)],
            'context': {'default_lms_course_id': self.id},
        }

    def action_view_assignments(self):
        """فتح سجل واجبات المقرر."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Course Assignments'),
            'res_model': 'uni.lms.assignment',
            'view_mode': 'list,form',
            'domain': [('lms_course_id', '=', self.id)],
            'context': {'default_lms_course_id': self.id},
        }

    def action_view_quizzes(self):
        """فتح سجل اختبارات المقرر."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Course Quizzes'),
            'res_model': 'uni.lms.quiz',
            'view_mode': 'list,form',
            'domain': [('lms_course_id', '=', self.id)],
            'context': {'default_lms_course_id': self.id},
        }

    def action_view_forums(self):
        """فتح سجل منتديات المقرر."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Course Forums'),
            'res_model': 'uni.lms.forum',
            'view_mode': 'list,form',
            'domain': [('lms_course_id', '=', self.id)],
            'context': {'default_lms_course_id': self.id},
        }

    def action_view_progress(self):
        """فتح سجل تقدم الطلاب في المقرر."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Enrolled Students'),
            'res_model': 'uni.lms.progress',
            'view_mode': 'list,form',
            'domain': [('lms_course_id', '=', self.id)],
            'context': {'default_lms_course_id': self.id},
        }
