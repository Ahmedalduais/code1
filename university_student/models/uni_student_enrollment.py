# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniStudentEnrollment(models.Model):
    """التسجيل الأكاديمي للطالب — ربط الطالب بفصل دراسي وبرنامج.

    يمثل هذا النموذج تسجيل الطالب لفصل دراسي معين تحت برنامج محدد،
    ويحمل خطوط تسجيل المقررات (``uni.student.enrollment.line``) التي
    تُفصّل المقررات المسجّلة وحالتها ودرجاتها.

    سير العمل:
        draft → enrolled → completed
                    ↘ cancelled
    """
    _name = 'uni.student.enrollment'
    _description = 'Student Enrollment'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'student_id, academic_term_id desc, id'

    name = fields.Char(
        string='Reference', copy=False, readonly=True, index=True,
        help='Auto-generated reference identifying this enrollment.')
    student_id = fields.Many2one(
        'uni.student', string='Student',
        required=True, ondelete='restrict', tracking=True, index=True)
    academic_term_id = fields.Many2one(
        'uni.academic.term', string='Academic Term',
        required=True, ondelete='restrict', tracking=True, index=True)
    academic_year_id = fields.Many2one(
        'uni.academic.year', string='Academic Year',
        related='academic_term_id.academic_year_id', store=True, index=True)
    program_id = fields.Many2one(
        'uni.program', string='Program',
        ondelete='restrict', tracking=True, index=True,
        help='Program under which the student is enrolling for this term.')
    university_id = fields.Many2one(
        'uni.university', string='University',
        related='academic_term_id.university_id', store=True, index=True)

    enrollment_date = fields.Date(
        string='Enrollment Date', default=fields.Date.context_today, tracking=True)
    enrollment_type = fields.Selection([
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('auditing', 'Auditing'),
    ], string='Enrollment Type', default='full_time', tracking=True, index=True)
    level = fields.Integer(
        string='Level', default=1, tracking=True,
        help='Academic level/year for this enrollment (1, 2, 3...).')
    total_credits = fields.Integer(
        string='Registered Credits', default=0,
        compute='_compute_total_credits', store=True,
        help='Sum of credit hours across all active (non-dropped) enrollment lines.')
    total_credits_earned = fields.Integer(
        string='Credits Earned', default=0,
        compute='_compute_credits_earned', store=True,
        help='Sum of credit hours from completed/passed enrollment lines.')
    cumulative_gpa = fields.Float(
        string='Term GPA', digits=(4, 2), default=0.0,
        compute='_compute_cumulative_gpa', store=True,
        help='Grade Point Average computed from this enrollment\'s lines.')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('enrolled', 'Enrolled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, index=True,
        group_expand='_group_expand_states')

    line_ids = fields.One2many(
        'uni.student.enrollment.line', 'enrollment_id', string='Course Lines', copy=True)
    line_count = fields.Integer(compute='_compute_line_count', string='Lines')

    _sql_constraints = [
        ('unique_enrollment_student_term', 'unique(student_id, academic_term_id)',
         'A student can have only one enrollment per academic term!'),
    ]

    # ------------------------------------------------------------------
    # Group expansion & computed helpers
    # ------------------------------------------------------------------
    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in self._fields['state'].selection]

    @api.depends('line_ids', 'line_ids.state', 'line_ids.credit_hours')
    def _compute_total_credits(self):
        for rec in self:
            active_lines = rec.line_ids.filtered(
                lambda l: l.state in ('enrolled', 'completed'))
            rec.total_credits = int(sum(active_lines.mapped('credit_hours')))

    @api.depends('line_ids.state', 'line_ids.credit_hours')
    def _compute_credits_earned(self):
        for rec in self:
            passed = rec.line_ids.filtered(
                lambda l: l.state == 'completed' and l.final_grade >= 50.0)
            rec.total_credits_earned = int(sum(passed.mapped('credit_hours')))

    @api.depends('line_ids.final_grade', 'line_ids.credit_hours', 'line_ids.state')
    def _compute_cumulative_gpa(self):
        """Compute a simple GPA from final grades on a 4.0 scale.

        Each line's percentage (final_grade) is mapped to a 4.0 point
        scale (>= 90 → 4.0, >= 80 → 3.0, >= 70 → 2.0, >= 60 → 1.0, else 0)
        weighted by credit hours. The gradebook module may override this
        for the official calculation.
        """
        for rec in self:
            completed = rec.line_ids.filtered(lambda l: l.state == 'completed')
            total_credits = 0.0
            total_points = 0.0
            for line in completed:
                grade = line.final_grade or 0.0
                if grade >= 90:
                    pts = 4.0
                elif grade >= 80:
                    pts = 3.0
                elif grade >= 70:
                    pts = 2.0
                elif grade >= 60:
                    pts = 1.0
                else:
                    pts = 0.0
                ch = line.credit_hours or 0.0
                total_credits += ch
                total_points += pts * ch
            rec.cumulative_gpa = (total_points / total_credits) if total_credits else 0.0

    @api.depends('line_ids')
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    # ------------------------------------------------------------------
    # Onchange helpers — propagate context defaults
    # ------------------------------------------------------------------
    @api.onchange('student_id')
    def _onchange_student_id(self):
        if self.student_id:
            if not self.program_id:
                self.program_id = self.student_id.program_id
            if not self.level:
                self.level = self.student_id.current_level or 1

    # ------------------------------------------------------------------
    # Create — auto-generate reference
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.student.enrollment') or _('ENR-NEW')
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_enroll(self):
        """Confirm the enrollment: move from draft to enrolled."""
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError(_(
                    "Only draft enrollments can be confirmed (%s).") % rec.display_name)
            if not rec.line_ids:
                raise ValidationError(_(
                    "Cannot confirm an enrollment without course lines (%s).") % rec.display_name)
            rec.state = 'enrolled'

    def action_complete(self):
        """Mark the enrollment as completed (term finished)."""
        for rec in self:
            if rec.state != 'enrolled':
                raise ValidationError(_(
                    "Only enrolled records can be completed (%s).") % rec.display_name)
            rec.state = 'completed'

    def action_cancel(self):
        """Cancel the enrollment."""
        for rec in self:
            if rec.state == 'completed':
                raise ValidationError(_(
                    "Cannot cancel a completed enrollment (%s).") % rec.display_name)
            rec.state = 'cancelled'

    def action_draft(self):
        """Reset the enrollment to draft state."""
        for rec in self:
            if rec.state == 'completed':
                raise ValidationError(_(
                    "Cannot reset a completed enrollment to draft (%s).") % rec.display_name)
            rec.state = 'draft'

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('state', 'line_ids')
    def _check_enroll_lines(self):
        for rec in self:
            if rec.state in ('enrolled', 'completed') and not rec.line_ids:
                raise ValidationError(_(
                    "Enrollment %s must have at least one course line in state '%s'.")
                    % (rec.display_name, rec.state))

    @api.constrains('level')
    def _check_level(self):
        for rec in self:
            if rec.level < 0:
                raise ValidationError(_(
                    "Enrollment level cannot be negative for %s.") % rec.display_name)


class UniStudentEnrollmentLine(models.Model):
    """خط تسجيل المقرر — يمثل تسجيل الطالب لمقرر محدد ضمن تسجيل فصلي.

    يحمل الحالة، الدرجة النهائية، التقدير الحرفي (نص حر يُدخل يدوياً أو
    يُستنتج من نسبة الدرجة عبر خريطة افتراضية بسيطة)، وساعات الائتمان
    (related من المقرر).

    ملاحظة: التقدير الحرفي مخزّن كـ ``Char`` وليس ``Many2one`` إلى
    ``uni.grade.letter`` حتى لا تعتمد الوحدة على ``university_grading``.
    وحدة ``university_gradebook`` هي المسؤولة عن التقييم الرسمي للدرجات.
    """
    _name = 'uni.student.enrollment.line'
    _description = 'Student Enrollment Line'
    _order = 'enrollment_id, sequence, id'

    enrollment_id = fields.Many2one(
        'uni.student.enrollment', string='Enrollment',
        required=True, ondelete='cascade', index=True)
    student_id = fields.Many2one(
        'uni.student', string='Student',
        related='enrollment_id.student_id', store=True, index=True)
    academic_term_id = fields.Many2one(
        'uni.academic.term', string='Term',
        related='enrollment_id.academic_term_id', store=True, index=True)
    program_id = fields.Many2one(
        'uni.program', string='Program',
        related='enrollment_id.program_id', store=True, index=True)

    course_id = fields.Many2one(
        'uni.course', string='Course',
        required=True, ondelete='restrict', tracking=True, index=True)
    program_course_id = fields.Many2one(
        'uni.program.course', string='Program-Course Link',
        ondelete='restrict', index=True,
        help='Optional link to the program-course record that defines the course '
             'context within the student\'s program.')
    credit_hours = fields.Float(
        string='Credit Hours',
        related='program_course_id.effective_credit_hours', store=True,
        help='Effective credit hours from the program-course link, '
             'falls back to course.credit_hours when no link is set.')
    university_id = fields.Many2one(
        'uni.university', string='University',
        related='enrollment_id.university_id', store=True, index=True)

    sequence = fields.Integer(string='Sequence', default=10)
    state = fields.Selection([
        ('enrolled', 'Enrolled'),
        ('completed', 'Completed'),
        ('dropped', 'Dropped'),
        ('failed', 'Failed'),
    ], string='Line State', default='enrolled', tracking=True, index=True)
    final_grade = fields.Float(
        string='Final Grade', digits=(5, 2), default=0.0, tracking=True,
        help='Final numeric grade (percentage 0–100).')
    grade_letter = fields.Char(
        string='Grade Letter', tracking=True, index=True,
        help='Letter grade (e.g. A, B+). Stored as plain text to avoid a '
             'hard dependency on university_grading; the official letter '
             'lookup is performed by the university_gradebook module.')

    notes = fields.Text(string='Notes')

    # ------------------------------------------------------------------
    # Onchange helpers
    # ------------------------------------------------------------------
    @api.onchange('program_course_id')
    def _onchange_program_course_id(self):
        if self.program_course_id:
            self.course_id = self.program_course_id.course_id
            self.credit_hours = self.program_course_id.effective_credit_hours

    @api.onchange('course_id')
    def _onchange_course_id(self):
        if self.course_id and not self.program_course_id:
            self.credit_hours = self.course_id.credit_hours

    # ------------------------------------------------------------------
    # Business logic
    # ------------------------------------------------------------------
    @api.onchange('final_grade')
    def _onchange_final_grade(self):
        """Auto-suggest a grade letter based on the final percentage.

        Uses a simple built-in mapping (A/B/C/D/F) so the module does not
        need to depend on ``university_grading``. The official letter-grade
        lookup (with honours, +/- modifiers and configurable scales) is
        performed by the ``university_gradebook`` module.
        """
        if self.final_grade or self.final_grade == 0.0:
            grade = self.final_grade or 0.0
            if grade >= 90:
                self.grade_letter = 'A'
            elif grade >= 80:
                self.grade_letter = 'B'
            elif grade >= 70:
                self.grade_letter = 'C'
            elif grade >= 60:
                self.grade_letter = 'D'
            else:
                self.grade_letter = 'F'

    def action_complete_line(self):
        """Mark the line as completed (course finished with final grade)."""
        for rec in self:
            if rec.state != 'enrolled':
                raise ValidationError(_(
                    "Only enrolled lines can be completed (%s).") % rec.display_name)
            rec.state = 'completed'

    def action_drop(self):
        """Drop the course line."""
        for rec in self:
            if rec.state == 'completed':
                raise ValidationError(_(
                    "Cannot drop a completed course line (%s).") % rec.display_name)
            rec.state = 'dropped'

    def action_fail(self):
        """Mark the line as failed (course not passed)."""
        for rec in self:
            if rec.state == 'enrolled':
                rec.state = 'failed'

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('enrollment_id', 'course_id')
    def _check_unique_course_in_enrollment(self):
        for rec in self:
            duplicates = self.search([
                ('enrollment_id', '=', rec.enrollment_id.id),
                ('course_id', '=', rec.course_id.id),
                ('id', '!=', rec.id),
            ])
            if duplicates:
                raise ValidationError(_(
                    "Course %s is already enrolled in this enrollment.") %
                    rec.course_id.display_name)

    @api.constrains('final_grade')
    def _check_final_grade(self):
        for rec in self:
            if rec.final_grade < 0 or rec.final_grade > 100:
                raise ValidationError(_(
                    "Final grade must be between 0 and 100 for course %s.") %
                    rec.course_id.display_name)
