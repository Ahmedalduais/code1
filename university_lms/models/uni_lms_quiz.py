# -*- coding: utf-8 -*-
import json
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniLmsQuiz(models.Model):
    """الاختبار الإلكتروني — بنك أسئلة ومحاولات لكل طالب.

    يدعم أنواع الاختبارات (تدريبي/مُقيَّم/قبلي/بعدي/استبيان)،
    إعدادات الخلط وحدود الوقت وعدد المحاولات.
    """
    _name = 'uni.lms.quiz'
    _description = 'LMS Quiz'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'lms_course_id, start_date, id'

    name = fields.Char(string='Reference', required=True, copy=False, tracking=True,
                       default=lambda self: _('New'), index=True)
    code = fields.Char(string='Code', copy=False, tracking=True, index=True)
    lms_course_id = fields.Many2one('uni.lms.course', string='LMS Course',
                                    required=True, ondelete='cascade', tracking=True, index=True)
    title = fields.Char(string='Title', required=True, tracking=True, translate=True)
    description = fields.Text(string='Description')
    quiz_type = fields.Selection([
        ('practice', 'Practice'),
        ('graded', 'Graded'),
        ('pre_test', 'Pre-Test'),
        ('post_test', 'Post-Test'),
        ('survey', 'Survey'),
    ], string='Quiz Type', default='graded', required=True, tracking=True, index=True)
    max_score = fields.Float(string='Max Score', default=100.0, tracking=True)
    weight = fields.Float(string='Weight (%)', default=5.0, tracking=True,
                          help='Weight percentage in the final course grade.')
    time_limit_minutes = fields.Integer(string='Time Limit (min)', default=0,
                                        help='Set to 0 for no time limit.')
    attempts_allowed = fields.Integer(string='Attempts Allowed', default=1,
                                      help='Number of attempts per student (0 = unlimited).')
    shuffle_questions = fields.Boolean(string='Shuffle Questions', default=False)
    shuffle_options = fields.Boolean(string='Shuffle Options', default=False)
    show_answers_after = fields.Selection([
        ('never', 'Never'),
        ('immediately', 'Immediately after submission'),
        ('after_deadline', 'After Deadline'),
        ('after_grading', 'After Grading'),
    ], string='Show Answers', default='after_grading', required=True, tracking=True)
    start_date = fields.Datetime(string='Start Date', tracking=True)
    end_date = fields.Datetime(string='End Date', tracking=True)
    question_ids = fields.One2many('uni.lms.quiz.question', 'quiz_id', string='Questions')
    attempt_ids = fields.One2many('uni.lms.quiz.attempt', 'quiz_id', string='Attempts')
    question_count = fields.Integer(compute='_compute_question_count', string='Questions')
    attempt_count = fields.Integer(compute='_compute_attempt_count', string='Attempts')
    total_points = fields.Float(compute='_compute_total_points', string='Total Points',
                                help='Sum of question points.')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('closed', 'Closed'),
    ], string='Status', default='draft', tracking=True, group_expand='_group_expand_states')
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('check_max_score_positive',
         'check(max_score > 0)',
         'Max score must be greater than zero!'),
        ('check_weight_positive',
         'check(weight >= 0)',
         'Weight cannot be negative!'),
        ('check_time_limit_positive',
         'check(time_limit_minutes >= 0)',
         'Time limit cannot be negative!'),
        ('check_attempts_positive',
         'check(attempts_allowed >= 0)',
         'Attempts allowed cannot be negative!'),
    ]

    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in states]

    @api.depends('question_ids')
    def _compute_question_count(self):
        for rec in self:
            rec.question_count = len(rec.question_ids)

    @api.depends('attempt_ids')
    def _compute_attempt_count(self):
        for rec in self:
            rec.attempt_count = len(rec.attempt_ids)

    @api.depends('question_ids.points')
    def _compute_total_points(self):
        for rec in self:
            rec.total_points = sum(rec.question_ids.mapped('points'))

    @api.model_create_multi
    def create(self, vals_list):
        """إنشاء تسلسل تلقائي LMQ/... عند إنشاء اختبار جديد."""
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.lms.quiz') or _('New')
        return super().create(vals_list)

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        """تاريخ النهاية يجب أن يكون بعد تاريخ البداية (إن وُجدا)."""
        for rec in self:
            if rec.start_date and rec.end_date and rec.start_date > rec.end_date:
                raise ValidationError(_(
                    'Quiz end date (%s) must be after start date (%s) for %s.',
                    rec.end_date, rec.start_date, rec.display_name))

    def action_publish(self):
        """نشر الاختبار ليصبح متاحاً للمحاولات."""
        for rec in self:
            if not rec.question_ids:
                raise ValidationError(_(
                    'Cannot publish quiz %s without questions.', rec.display_name))
            rec.state = 'published'

    def action_close(self):
        """إغلاق الاختبار ومنع المحاولات الإضافية."""
        for rec in self:
            rec.state = 'closed'

    def action_draft(self):
        """إعادة الاختبار إلى حالة المسودة."""
        for rec in self:
            rec.state = 'draft'

    def action_view_questions(self):
        """فتح سجل أسئلة الاختبار."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Quiz Questions'),
            'res_model': 'uni.lms.quiz.question',
            'view_mode': 'list,form',
            'domain': [('quiz_id', '=', self.id)],
            'context': {'default_quiz_id': self.id},
        }

    def action_view_attempts(self):
        """فتح سجل محاولات الاختبار."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Quiz Attempts'),
            'res_model': 'uni.lms.quiz.attempt',
            'view_mode': 'list,form',
            'domain': [('quiz_id', '=', self.id)],
            'context': {'default_quiz_id': self.id},
        }


class UniLmsQuizQuestion(models.Model):
    """سؤال داخل اختبار — يدعم أنواعاً متعددة (اختيار/صح-خطأ/مقالي/...)."""
    _name = 'uni.lms.quiz.question'
    _description = 'LMS Quiz Question'
    _order = 'quiz_id, sequence, id'
    _rec_name = 'text'

    quiz_id = fields.Many2one('uni.lms.quiz', string='Quiz',
                              required=True, ondelete='cascade', tracking=True, index=True)
    question_type = fields.Selection([
        ('multiple_choice', 'Multiple Choice'),
        ('true_false', 'True / False'),
        ('short_answer', 'Short Answer'),
        ('essay', 'Essay'),
        ('fill_blank', 'Fill in the Blank'),
        ('matching', 'Matching'),
    ], string='Question Type', default='multiple_choice', required=True, tracking=True)
    text = fields.Text(string='Question Text', required=True, translate=True)
    points = fields.Float(string='Points', default=1.0, tracking=True,
                          help='Points awarded for a correct answer.')
    explanation = fields.Text(string='Explanation',
                              help='Shown to student after grading (depending on quiz settings).')
    attachment = fields.Binary(string='Attachment', attachment=True)
    sequence = fields.Integer(string='Sequence', default=10)
    options_data = fields.Text(string='Options (JSON)',
                               help='JSON-encoded list of answer options for '
                                    'multiple_choice / true_false / matching questions.')
    correct_answer = fields.Text(string='Correct Answer',
                                 help='Correct answer for short_answer / fill_blank / essay.')

    _sql_constraints = [
        ('check_points_positive',
         'check(points >= 0)',
         'Points cannot be negative!'),
    ]

    @api.constrains('question_type', 'options_data', 'correct_answer')
    def _check_payload(self):
        """كل نوع سؤال يحتاج إلى نوع البيانات المناسب."""
        for rec in self:
            if rec.question_type in ('multiple_choice', 'true_false', 'matching'):
                if not rec.options_data:
                    raise ValidationError(_(
                        'Question "%s" of type "%s" must have options data (JSON).',
                        rec.display_name, rec.question_type))
                try:
                    data = json.loads(rec.options_data)
                    if not isinstance(data, list):
                        raise ValueError('options_data must be a JSON list')
                except (ValueError, TypeError) as exc:
                    raise ValidationError(_(
                        'Invalid JSON in options_data for question "%s": %s',
                        rec.display_name, exc)) from exc
            if rec.question_type in ('short_answer', 'fill_blank', 'essay'):
                if not rec.correct_answer:
                    raise ValidationError(_(
                        'Question "%s" of type "%s" must have a correct answer.',
                        rec.display_name, rec.question_type))


class UniLmsQuizAttempt(models.Model):
    """محاولة طالب على اختبار — تحفظ الإجابات والنتيجة والحالة."""
    _name = 'uni.lms.quiz.attempt'
    _description = 'LMS Quiz Attempt'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'quiz_id, student_code, attempt_number, id'
    _rec_name = 'quiz_id'

    quiz_id = fields.Many2one('uni.lms.quiz', string='Quiz',
                              required=True, ondelete='cascade', tracking=True, index=True)
    student_name = fields.Char(
        string='Student Name', required=True, tracking=True, index=True,
        help='Free-text student name (the LMS module does not depend on '
             'university_student, so the student is recorded as a string).')
    student_code = fields.Char(
        string='Student Code', copy=False, tracking=True, index=True,
        help='Optional student code/identifier (e.g. university student ID).')
    user_id = fields.Many2one(
        'res.users', string='Attempting User',
        ondelete='set null', tracking=True, index=True,
        default=lambda self: self.env.user,
        help='Odoo user who attempted the quiz (used by website controllers).')
    attempt_number = fields.Integer(string='Attempt #', default=1, required=True, tracking=True)
    start_time = fields.Datetime(string='Start Time', default=fields.Datetime.now,
                                 required=True, tracking=True)
    end_time = fields.Datetime(string='End Time', tracking=True)
    score = fields.Float(string='Score', default=0.0, tracking=True,
                         help='Raw score achieved on this attempt.')
    max_score = fields.Float(string='Max Score', default=100.0, tracking=True)
    percentage = fields.Float(string='Percentage', default=0.0, tracking=True,
                              help='Score / max_score * 100.')
    grade_letter = fields.Char(
        string='Grade Letter', copy=False, tracking=True,
        help='Free-text grade letter (e.g. A, B+, C). Auto-suggested from '
             'the score percentage using a built-in mapping; can be edited '
             'manually. The LMS module does not depend on university_grading.')
    state = fields.Selection([
        ('in_progress', 'In Progress'),
        ('submitted', 'Submitted'),
        ('graded', 'Graded'),
        ('abandoned', 'Abandoned'),
    ], string='Status', default='in_progress', tracking=True, group_expand='_group_expand_states')
    answers_data = fields.Text(string='Answers (JSON)', copy=False,
                               help='JSON-encoded dictionary of student answers keyed by '
                                    'question ID.')
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('unique_attempt_quiz_student_code_number',
         'unique(quiz_id, student_code, attempt_number)',
         'Duplicate attempt number for this student code on this quiz!'),
        ('check_score_range',
         'check(score >= 0 and score <= max_score)',
         'Score must be between 0 and max score!'),
        ('check_attempt_positive',
         'check(attempt_number > 0)',
         'Attempt number must be greater than zero!'),
    ]

    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in states]

    @api.constrains('answers_data')
    def _check_answers_json(self):
        """التحقق من صحة JSON عند توفير ``answers_data``."""
        for rec in self:
            if rec.answers_data:
                try:
                    data = json.loads(rec.answers_data)
                    if not isinstance(data, dict):
                        raise ValueError('answers_data must be a JSON object')
                except (ValueError, TypeError) as exc:
                    raise ValidationError(_(
                        'Invalid JSON in answers_data for attempt %s: %s',
                        rec.display_name, exc)) from exc

    def action_submit(self):
        """تسليم المحاولة — حساب النسبة المئوية وتمهيد التقييم."""
        for rec in self:
            rec.end_time = fields.Datetime.now()
            if rec.max_score > 0:
                rec.percentage = (rec.score / rec.max_score) * 100.0
            else:
                rec.percentage = 0.0
            rec.state = 'submitted'

    def action_grade(self):
        """تقييم المحاولة — اقتراح التقدير الحرفي تلقائياً."""
        for rec in self:
            if rec.max_score > 0:
                rec.percentage = (rec.score / rec.max_score) * 100.0
            rec.grade_letter = self._grade_letter_from_percentage(rec.percentage or 0.0)
            rec.state = 'graded'

    @staticmethod
    def _grade_letter_from_percentage(percentage):
        """خريطة التقديرات الافتراضية المدمجة (لا تعتمد على university_grading)."""
        if percentage >= 90:
            return 'A'
        if percentage >= 85:
            return 'B+'
        if percentage >= 80:
            return 'B'
        if percentage >= 75:
            return 'C+'
        if percentage >= 70:
            return 'C'
        if percentage >= 65:
            return 'D+'
        if percentage >= 60:
            return 'D'
        return 'F'

    def action_abandon(self):
        """التخلي عن المحاولة (تنتهي كملغاة)."""
        for rec in self:
            rec.end_time = fields.Datetime.now()
            rec.state = 'abandoned'

    def action_resume(self):
        """استئناف محاولة تم التخلي عنها."""
        for rec in self:
            rec.end_time = False
            rec.state = 'in_progress'
