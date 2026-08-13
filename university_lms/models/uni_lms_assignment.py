# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniLmsAssignment(models.Model):
    """الواجب الدراسي داخل المقرر الإلكتروني.

    يدعم أنواع الواجبات الفردية والجماعية، مع تسليمات متعددة الصيغ
    (ملف/نص/رابط/كليهما)، وقواعد تقديم متأخر بعقوبة مئوية.
    """
    _name = 'uni.lms.assignment'
    _description = 'LMS Assignment'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'lms_course_id, due_date, id'

    name = fields.Char(string='Reference', required=True, copy=False, tracking=True,
                       default=lambda self: _('New'), index=True)
    code = fields.Char(string='Code', copy=False, tracking=True, index=True)
    lms_course_id = fields.Many2one('uni.lms.course', string='LMS Course',
                                    required=True, ondelete='cascade', tracking=True, index=True)
    title = fields.Char(string='Title', required=True, tracking=True, translate=True)
    description = fields.Html(string='Description', required=True)
    assignment_type = fields.Selection([
        ('individual', 'Individual'),
        ('group', 'Group'),
    ], string='Assignment Type', default='individual', required=True, tracking=True)
    max_score = fields.Float(string='Max Score', default=100.0, tracking=True,
                             help='Maximum raw score before weighting.')
    weight = fields.Float(string='Weight (%)', default=10.0, tracking=True,
                          help='Weight percentage in the final course grade.')
    due_date = fields.Datetime(string='Due Date', required=True, tracking=True)
    allow_late_submission = fields.Boolean(string='Allow Late Submission', default=False)
    late_penalty_percentage = fields.Float(string='Late Penalty (%)', default=10.0,
                                           help='Percentage deducted from late submissions.')
    submission_format = fields.Selection([
        ('file', 'File Upload'),
        ('text', 'Text Entry'),
        ('both', 'File or Text'),
        ('url', 'URL'),
    ], string='Submission Format', default='file', required=True, tracking=True)
    instructions = fields.Html(string='Instructions')
    attachment = fields.Binary(string='Attachment', attachment=True)
    attachment_filename = fields.Char(string='Attachment Filename')
    submission_ids = fields.One2many('uni.lms.assignment.submission', 'assignment_id',
                                     string='Submissions')
    submission_count = fields.Integer(compute='_compute_submission_count', string='Submissions')
    graded_count = fields.Integer(compute='_compute_graded_count', string='Graded')
    pending_count = fields.Integer(compute='_compute_pending_count', string='Pending')
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
        ('check_late_penalty_range',
         'check(late_penalty_percentage >= 0 and late_penalty_percentage <= 100)',
         'Late penalty percentage must be between 0 and 100!'),
    ]

    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in states]

    @api.depends('submission_ids')
    def _compute_submission_count(self):
        for rec in self:
            rec.submission_count = len(rec.submission_ids)

    @api.depends('submission_ids.state')
    def _compute_graded_count(self):
        for rec in self:
            rec.graded_count = len(rec.submission_ids.filtered(
                lambda s: s.state == 'graded'))

    @api.depends('submission_ids.state')
    def _compute_pending_count(self):
        """الطلبات المعلقة = المُسلَّمة لكن غير المُقيَّمة."""
        for rec in self:
            rec.pending_count = len(rec.submission_ids.filtered(
                lambda s: s.state == 'submitted'))

    @api.model_create_multi
    def create(self, vals_list):
        """إنشاء تسلسل تلقائي LMA/... عند إنشاء واجب جديد."""
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.lms.assignment') or _('New')
        return super().create(vals_list)

    @api.constrains('max_score', 'weight')
    def _check_scores(self):
        for rec in self:
            if rec.max_score <= 0:
                raise ValidationError(_(
                    'Max score for assignment %s must be greater than zero.',
                    rec.display_name))
            if rec.weight < 0:
                raise ValidationError(_(
                    'Weight for assignment %s cannot be negative.',
                    rec.display_name))

    def action_publish(self):
        """نشر الواجب ليصبح متاحاً للتسليم."""
        for rec in self:
            if not rec.due_date:
                raise ValidationError(_(
                    'Cannot publish assignment %s without a due date.',
                    rec.display_name))
            rec.state = 'published'

    def action_close(self):
        """إغلاق الواجب ومنع التسليمات الإضافية."""
        for rec in self:
            rec.state = 'closed'

    def action_draft(self):
        """إعادة الواجب إلى حالة المسودة."""
        for rec in self:
            rec.state = 'draft'

    def action_view_submissions(self):
        """فتح سجل تسليمات الواجب."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Submissions'),
            'res_model': 'uni.lms.assignment.submission',
            'view_mode': 'list,form',
            'domain': [('assignment_id', '=', self.id)],
            'context': {'default_assignment_id': self.id,
                        'default_lms_course_id': self.lms_course_id.id},
        }


class UniLmsAssignmentSubmission(models.Model):
    """تسليم طالب لواجب — يحتوي على الملف/النص/الرابط والدرجة والتغذية الراجعة."""
    _name = 'uni.lms.assignment.submission'
    _description = 'LMS Assignment Submission'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'assignment_id, submission_date desc, id'
    _rec_name = 'assignment_id'

    assignment_id = fields.Many2one('uni.lms.assignment', string='Assignment',
                                    required=True, ondelete='cascade', tracking=True, index=True)
    lms_course_id = fields.Many2one('uni.lms.course', string='LMS Course',
                                    related='assignment_id.lms_course_id', store=True, index=True)
    student_name = fields.Char(
        string='Student Name', required=True, tracking=True, index=True,
        help='Free-text student name (the LMS module does not depend on '
             'university_student, so the student is recorded as a string).')
    student_code = fields.Char(
        string='Student Code', copy=False, tracking=True, index=True,
        help='Optional student code/identifier (e.g. university student ID).')
    user_id = fields.Many2one(
        'res.users', string='Submitting User',
        ondelete='set null', tracking=True, index=True,
        default=lambda self: self.env.user,
        help='Odoo user who submitted (used by the website controllers to '
             'identify the ownership of the submission).')
    submission_date = fields.Datetime(string='Submission Date', default=fields.Datetime.now,
                                      tracking=True)
    file = fields.Binary(string='Submitted File', attachment=True)
    filename = fields.Char(string='Filename')
    text_submission = fields.Text(string='Text Submission')
    url_submission = fields.Char(string='URL Submission')
    score = fields.Float(string='Score', default=0.0, tracking=True,
                         help='Raw score (0 to max_score).')
    grade_letter = fields.Char(
        string='Grade Letter', copy=False, tracking=True,
        help='Free-text grade letter (e.g. A, B+, C). Auto-suggested from '
             'the score percentage using a built-in mapping; can be edited '
             'manually. The LMS module does not depend on university_grading.')
    feedback = fields.Text(string='Feedback', tracking=True)
    submitted_late = fields.Boolean(string='Submitted Late', copy=False, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('graded', 'Graded'),
        ('resubmit', 'Needs Resubmission'),
    ], string='Status', default='draft', tracking=True, group_expand='_group_expand_states')
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('unique_submission_assignment_student_code',
         'unique(assignment_id, student_code)',
         'A submission already exists for this student code on this assignment!'),
        ('check_score_positive',
         'check(score >= 0)',
         'Score cannot be negative!'),
    ]

    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in states]

    @api.onchange('assignment_id')
    def _onchange_assignment_id(self):
        """عند اختيار الواجب، يُملأ المقرر الإلكتروني تلقائياً."""
        if self.assignment_id:
            self.lms_course_id = self.assignment_id.lms_course_id

    @api.constrains('score', 'assignment_id')
    def _check_score_range(self):
        """الدرجة يجب أن تكون بين 0 و max_score للواجب."""
        for rec in self:
            if rec.assignment_id and rec.score > rec.assignment_id.max_score:
                raise ValidationError(_(
                    'Score (%s) cannot exceed max score (%s) for assignment %s.',
                    rec.score, rec.assignment_id.max_score, rec.display_name))

    @api.constrains('file', 'text_submission', 'url_submission', 'assignment_id')
    def _check_submission_payload(self):
        """صيغة التسليم يجب أن تتطابق مع المطلوب في الواجب."""
        for rec in self:
            if not rec.assignment_id:
                continue
            fmt = rec.assignment_id.submission_format
            if fmt == 'file' and not rec.file:
                raise ValidationError(_(
                    'Submission for "%s" must include a file.', rec.display_name))
            if fmt == 'text' and not rec.text_submission:
                raise ValidationError(_(
                    'Submission for "%s" must include text content.', rec.display_name))
            if fmt == 'url' and not rec.url_submission:
                raise ValidationError(_(
                    'Submission for "%s" must include a URL.', rec.display_name))
            if fmt == 'both' and not (rec.file or rec.text_submission):
                raise ValidationError(_(
                    'Submission for "%s" must include a file or text content.',
                    rec.display_name))

    def action_submit(self):
        """تسليم الواجب — يحدد حالة «مُسلَّم» ويحسب التأخر تلقائياً."""
        for rec in self:
            if rec.assignment_id and rec.assignment_id.due_date:
                now = fields.Datetime.now()
                rec.submitted_late = now > rec.assignment_id.due_date
                if rec.submitted_late and not rec.assignment_id.allow_late_submission:
                    raise ValidationError(_(
                        'Late submission is not allowed for assignment %s.',
                        rec.assignment_id.display_name))
            rec.submission_date = fields.Datetime.now()
            rec.state = 'submitted'

    def action_grade(self):
        """تقييم التسليم — تطبيق عقوبة التأخر إن وُجدت وتمهيد للتقدير."""
        for rec in self:
            score = rec.score or 0.0
            # Auto-apply late penalty
            if rec.submitted_late and rec.assignment_id.late_penalty_percentage > 0:
                penalty = score * (rec.assignment_id.late_penalty_percentage / 100.0)
                score = max(0.0, score - penalty)
            rec.score = score
            # Auto-suggest grade letter from percentage (built-in mapping)
            if rec.assignment_id and rec.assignment_id.max_score > 0:
                percentage = (rec.score / rec.assignment_id.max_score) * 100.0
                rec.grade_letter = self._grade_letter_from_percentage(percentage)
            rec.state = 'graded'

    def action_request_resubmission(self):
        """طلب إعادة تسليم من الطالب."""
        for rec in self:
            rec.state = 'resubmit'

    def action_reset_to_draft(self):
        """إعادة التسليم إلى حالة المسودة."""
        for rec in self:
            rec.state = 'draft'

    @api.onchange('score', 'assignment_id')
    def _onchange_suggest_grade_letter(self):
        """اقتراح التقدير الحرفي تلقائياً بناء على نسبة الدرجة.

        يستخدم خريطة تقديرات افتراضية مدمجة (لا تعتمد على university_grading):
            A   : 90-100
            B+  : 85-89.99
            B   : 80-84.99
            C+  : 75-79.99
            C   : 70-74.99
            D+  : 65-69.99
            D   : 60-64.99
            F   : أقل من 60
        """
        if self.score and self.assignment_id and self.assignment_id.max_score:
            percentage = (self.score / self.assignment_id.max_score) * 100.0
            self.grade_letter = self._grade_letter_from_percentage(percentage)
        else:
            self.grade_letter = False

    @staticmethod
    def _grade_letter_from_percentage(percentage):
        """خريطة التقديرات الافتراضية المدمجة."""
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
