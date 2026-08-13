# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniLmsProgress(models.Model):
    """تقدم الطالب في المقرر الإلكتروني.

    يلخّص نسبة الإنجاز، الدرجات، الوقت المستغرق، والحالة العامة
    لكل طالب في كل مقرر إلكتروني.
    """
    _name = 'uni.lms.progress'
    _description = 'LMS Student Progress'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'lms_course_id, student_code, id'
    _rec_name = 'lms_course_id'

    name = fields.Char(string='Reference', required=True, copy=False, tracking=True,
                       default=lambda self: _('New'), index=True)
    lms_course_id = fields.Many2one('uni.lms.course', string='LMS Course',
                                    required=True, ondelete='cascade', tracking=True, index=True)
    student_name = fields.Char(
        string='Student Name', required=True, tracking=True, index=True,
        help='Free-text student name (the LMS module does not depend on '
             'university_student, so the student is recorded as a string).')
    student_code = fields.Char(
        string='Student Code', copy=False, tracking=True, index=True,
        help='Optional student code/identifier (e.g. university student ID).')
    user_id = fields.Many2one(
        'res.users', string='Owning User',
        ondelete='set null', tracking=True, index=True,
        default=lambda self: self.env.user,
        help='Odoo user who owns this progress record (used by the website '
             'controllers to identify the user\'s progress records even when '
             'university_student is not installed).')
    enrollment_date = fields.Datetime(string='Enrollment Date',
                                      default=fields.Datetime.now, required=True, tracking=True)
    last_access = fields.Datetime(string='Last Access', tracking=True)
    completion_percentage = fields.Float(string='Completion %', default=0.0,
                                         tracking=True,
                                         help='Percentage of required content completed.')
    content_completed = fields.Integer(string='Content Completed', default=0,
                                       help='Count of completed required content items.')
    content_total = fields.Integer(string='Content Total', default=0,
                                   compute='_compute_content_total', store=True,
                                   help='Total required content items in the course.')
    assignments_completed = fields.Integer(string='Assignments Completed', default=0,
                                           tracking=True)
    quizzes_completed = fields.Integer(string='Quizzes Completed', default=0,
                                       tracking=True)
    average_score = fields.Float(string='Average Score', default=0.0, tracking=True,
                                 help='Average percentage across assignments and quizzes.')
    time_spent_hours = fields.Float(string='Time Spent (hours)', default=0.0, tracking=True)
    last_activity = fields.Datetime(string='Last Activity', tracking=True)
    state = fields.Selection([
        ('enrolled', 'Enrolled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('dropped', 'Dropped'),
    ], string='Status', default='enrolled', tracking=True, group_expand='_group_expand_states')
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('unique_lms_course_student_code',
         'unique(lms_course_id, student_code)',
         'A progress record already exists for this student code on this LMS course!'),
        ('unique_lms_course_user',
         'unique(lms_course_id, user_id)',
         'A progress record already exists for this user on this LMS course!'),
        ('check_completion_range',
         'check(completion_percentage >= 0 and completion_percentage <= 100)',
         'Completion percentage must be between 0 and 100!'),
        ('check_counts_positive',
         'check(content_completed >= 0 and content_total >= 0 and '
         'assignments_completed >= 0 and quizzes_completed >= 0)',
         'Counts cannot be negative!'),
        ('check_time_positive',
         'check(time_spent_hours >= 0)',
         'Time spent cannot be negative!'),
    ]

    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in states]

    @api.depends('lms_course_id', 'lms_course_id.content_ids',
                 'lms_course_id.content_ids.is_required',
                 'lms_course_id.content_ids.state')
    def _compute_content_total(self):
        """إجمالي عناصر المحتوى المطلوبة والمنشورة في المقرر."""
        for rec in self:
            required_content = rec.lms_course_id.content_ids.filtered(
                lambda c: c.is_required and c.state == 'published')
            rec.content_total = len(required_content)

    @api.model_create_multi
    def create(self, vals_list):
        """إنشاء تسلسل تلقائي LMP/... عند إنشاء سجل تقدم جديد."""
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.lms.progress') or _('New')
        return super().create(vals_list)

    @api.constrains('completion_percentage')
    def _check_completion(self):
        for rec in self:
            if rec.completion_percentage < 0 or rec.completion_percentage > 100:
                raise ValidationError(_(
                    'Completion percentage for %s must be between 0 and 100.',
                    rec.display_name))

    @api.constrains('content_completed', 'content_total')
    def _check_content_counts(self):
        """لا يمكن أن يتجاوز المحتوى المُنجز إجمالي المحتوى المطلوب."""
        for rec in self:
            if rec.content_completed > rec.content_total and rec.content_total > 0:
                raise ValidationError(_(
                    'Completed content (%s) cannot exceed total content (%s) for %s.',
                    rec.content_completed, rec.content_total, rec.display_name))

    def action_drop(self):
        """تسجيل أن الطالب ترك المقرر."""
        for rec in self:
            rec.state = 'dropped'

    def action_complete(self):
        """تمييز التقدم كمكتمل (يضبط نسبة الإنجاز إلى 100%)."""
        for rec in self:
            rec.completion_percentage = 100.0
            rec.state = 'completed'

    def action_reactivate(self):
        """إعادة تفعيل طالب ترك المقرر."""
        for rec in self:
            rec.state = 'in_progress'

    def action_enroll(self):
        """تسجيل طالب في المقرر (إذا كان في حالة مسودة أو لم يُسجَّل بعد)."""
        for rec in self:
            rec.state = 'enrolled'
            if not rec.enrollment_date:
                rec.enrollment_date = fields.Datetime.now()

    def update_progress(self, content_completed=None, assignments_completed=None,
                        quizzes_completed=None, average_score=None,
                        time_spent_hours=None, last_activity=None):
        """تحديث سجل التقدم بشكل تراكمي (يُستدعى من controllers/النماذج الأخرى).

        - القيم المُمرَّرة تُضاف للقيم الحالية (للعدد والوقت)
        - ``average_score`` يُستبدل تماماً عند توفيره
        - يتم إعادة حساب نسبة الإنجاز تلقائياً
        """
        for rec in self:
            vals = {}
            if content_completed is not None:
                vals['content_completed'] = (rec.content_completed or 0) + content_completed
            if assignments_completed is not None:
                vals['assignments_completed'] = (rec.assignments_completed or 0) + assignments_completed
            if quizzes_completed is not None:
                vals['quizzes_completed'] = (rec.quizzes_completed or 0) + quizzes_completed
            if time_spent_hours is not None:
                vals['time_spent_hours'] = (rec.time_spent_hours or 0.0) + time_spent_hours
            if average_score is not None:
                vals['average_score'] = average_score
            if last_activity is not None:
                vals['last_activity'] = last_activity
            # Recompute completion percentage
            total = rec.content_total or 0
            completed = vals.get('content_completed', rec.content_completed or 0)
            if total > 0:
                vals['completion_percentage'] = min(100.0, (completed / total) * 100.0)
            else:
                vals['completion_percentage'] = 0.0
            # Update state to in_progress if previously only enrolled
            if rec.state == 'enrolled':
                vals['state'] = 'in_progress'
            vals['last_access'] = fields.Datetime.now()
            rec.write(vals)
        return True
