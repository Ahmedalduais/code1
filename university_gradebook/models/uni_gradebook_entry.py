# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniGradebookEntry(models.Model):
    """إدخال درجة فردي — يمثل درجة طالب في تقييم واحد ضمن سجل الدرجات.

    كل إدخال يربط طالباً (عبر خط السجل) بنوع تقييم محدد، ويحمل:
        * الدرجة (score) وأقصى درجة (max_score) والوزن (weight)
        * النسبة المئوية المحسوبة (percentage)
        * التقدير الحرفي المشتق من نظام الدرجات
        * حالة الإعفاء أو الفقدان
    """
    _name = 'uni.gradebook.entry'
    _description = 'Gradebook Entry'
    _inherit = ['mail.thread']
    _order = 'gradebook_line_id, assessment_date, id'

    # ------------------------------------------------------------------
    # Identity (computed display name)
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Reference', compute='_compute_name', store=True, index=True,
        help='Display name built from student, assessment name and gradebook.')

    # ------------------------------------------------------------------
    # Relations
    # ------------------------------------------------------------------
    gradebook_id = fields.Many2one(
        'uni.gradebook', string='Gradebook',
        related='gradebook_line_id.gradebook_id', store=True, index=True)
    gradebook_line_id = fields.Many2one(
        'uni.gradebook.line', string='Student Line',
        required=True, ondelete='cascade', tracking=True, index=True)
    student_id = fields.Many2one(
        'uni.student', string='Student',
        related='gradebook_line_id.student_id', store=True, index=True)

    # ------------------------------------------------------------------
    # Assessment info
    # ------------------------------------------------------------------
    evaluation_type_id = fields.Many2one(
        'uni.evaluation.type', string='Evaluation Type',
        ondelete='restrict', index=True,
        help='Type of assessment (Final Exam, Midterm, Assignment, etc.).')
    assessment_name = fields.Char(
        string='Assessment Name', tracking=True,
        help='Free-text name for the assessment (e.g. Midterm Exam 1).')
    assessment_date = fields.Date(
        string='Assessment Date', tracking=True,
        help='Date when the assessment took place.')

    # ------------------------------------------------------------------
    # Scores & weights
    # ------------------------------------------------------------------
    score = fields.Float(
        string='Score', digits=(5, 2), default=0.0, tracking=True,
        help='Raw score obtained by the student.')
    max_score = fields.Float(
        string='Max Score', digits=(5, 2), default=100.0, tracking=True,
        help='Maximum possible score for this assessment.')
    weight = fields.Float(
        string='Weight %', digits=(5, 2), default=0.0, tracking=True,
        help='Weight percentage of this assessment in the final grade (0-100). '
             'Sum of all weights per student should equal 100 for a complete gradebook.')
    percentage = fields.Float(
        string='Percentage %', digits=(5, 2), default=0.0,
        compute='_compute_percentage', store=True,
        help='Score as a percentage of the max score.')

    # ------------------------------------------------------------------
    # Derived grade info
    # ------------------------------------------------------------------
    grade_letter_id = fields.Many2one(
        'uni.grade.letter', string='Grade Letter',
        compute='_compute_grade_letter', store=True,
        ondelete='restrict',
        help='Letter grade derived from the percentage using the gradebook\'s '
             'grading system.')

    # ------------------------------------------------------------------
    # Status flags
    # ------------------------------------------------------------------
    is_excused = fields.Boolean(
        string='Excused', default=False, tracking=True,
        help='True if the student was excused from this assessment.')
    is_missing = fields.Boolean(
        string='Missing', default=False,
        compute='_compute_is_missing', store=True,
        help='True if the entry has no score (and is not excused).')

    notes = fields.Text(string='Notes')

    # ------------------------------------------------------------------
    # Computed: percentage, grade letter, missing
    # ------------------------------------------------------------------
    @api.depends('student_id', 'assessment_name', 'evaluation_type_id',
                 'gradebook_id', 'gradebook_line_id')
    def _compute_name(self):
        for rec in self:
            parts = []
            if rec.assessment_name:
                parts.append(rec.assessment_name)
            elif rec.evaluation_type_id:
                parts.append(rec.evaluation_type_id.display_name)
            if rec.student_id:
                parts.append(rec.student_id.display_name)
            elif rec.gradebook_line_id and rec.gradebook_line_id.student_id:
                parts.append(rec.gradebook_line_id.student_id.display_name)
            rec.name = ' - '.join(parts) if parts else _('New')

    @api.depends('score', 'max_score', 'is_excused')
    def _compute_percentage(self):
        """Compute the percentage of the score relative to the max score.

        Excused entries are treated as 0% (they should typically be excluded
        from final computation via the weight mechanism in the caller).
        """
        for rec in self:
            if rec.is_excused:
                rec.percentage = 0.0
            elif rec.max_score and rec.max_score > 0:
                rec.percentage = (rec.score or 0.0) / rec.max_score * 100.0
            else:
                rec.percentage = 0.0

    @api.depends('percentage', 'gradebook_id.grading_system_id', 'is_excused')
    def _compute_grade_letter(self):
        """Derive the grade letter from the percentage using the gradebook's
        grading system scale (if any).
        """
        for rec in self:
            if rec.is_excused or not rec.gradebook_id or \
                    not rec.gradebook_id.grading_system_id:
                rec.grade_letter_id = False
                continue
            system = rec.gradebook_id.grading_system_id
            letter = system.get_grade_letter_for_percentage(rec.percentage)
            rec.grade_letter_id = letter.id if letter else False

    @api.depends('score', 'is_excused', 'max_score')
    def _compute_is_missing(self):
        """An entry is missing when the score is 0 (or unset) and the
        entry is not marked as excused.
        """
        for rec in self:
            rec.is_missing = (not rec.is_excused) and (rec.score or 0.0) <= 0.0

    # ------------------------------------------------------------------
    # Onchange helpers
    # ------------------------------------------------------------------
    @api.onchange('evaluation_type_id')
    def _onchange_evaluation_type_id(self):
        """Pre-fill name, max_score and weight from the evaluation type."""
        if self.evaluation_type_id:
            if not self.assessment_name:
                self.assessment_name = self.evaluation_type_id.name
            if self.evaluation_type_id.default_weight and not self.weight:
                self.weight = self.evaluation_type_id.default_weight

    @api.onchange('gradebook_line_id')
    def _onchange_gradebook_line_id(self):
        """Keep gradebook_id in sync with the line's gradebook."""
        if self.gradebook_line_id and self.gradebook_line_id.gradebook_id:
            self.gradebook_id = self.gradebook_line_id.gradebook_id.id

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('score', 'max_score')
    def _check_score_range(self):
        """Score cannot exceed the max score (and cannot be negative)."""
        for rec in self:
            if rec.score < 0:
                raise ValidationError(_(
                    "Score cannot be negative for entry %s.") % rec.display_name)
            if rec.max_score and rec.score > rec.max_score:
                raise ValidationError(_(
                    "Score (%(score)s) cannot exceed the maximum score "
                    "(%(max)s) for entry %(entry)s.") % {
                        'score': rec.score,
                        'max': rec.max_score,
                        'entry': rec.display_name,
                    })
            if rec.max_score and rec.max_score <= 0:
                raise ValidationError(_(
                    "Maximum score must be greater than zero for entry %s.")
                    % rec.display_name)

    @api.constrains('weight')
    def _check_weight_range(self):
        """Weight must be between 0 and 100 (inclusive)."""
        for rec in self:
            if rec.weight < 0 or rec.weight > 100:
                raise ValidationError(_(
                    "Weight (%s) must be between 0 and 100 for entry %s.") %
                    (rec.weight, rec.display_name))

    @api.constrains('gradebook_line_id', 'evaluation_type_id', 'assessment_name')
    def _check_unique_assessment(self):
        """Prevent duplicate entries for the same student + assessment
        (combination of evaluation_type_id OR assessment_name).
        """
        for rec in self:
            if not rec.gradebook_line_id:
                continue
            domain = [
                ('gradebook_line_id', '=', rec.gradebook_line_id.id),
                ('id', '!=', rec.id),
            ]
            if rec.evaluation_type_id:
                domain.append(('evaluation_type_id', '=', rec.evaluation_type_id.id))
            elif rec.assessment_name:
                domain.append(('assessment_name', '=', rec.assessment_name))
            else:
                continue
            duplicates = self.search(domain, limit=1)
            if duplicates:
                raise ValidationError(_(
                    "An entry for this assessment already exists for student %s.")
                    % rec.gradebook_line_id.student_id.display_name)
