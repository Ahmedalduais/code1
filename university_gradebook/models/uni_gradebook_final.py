# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class UniGradebookFinal(models.Model):
    """الدرجة النهائية للطالب في سجل درجات — محسوبة من إدخالات الدرجات.

    تُحسب الدرجات النهائية من خلال تجميع إدخالات الطالب (entries) موزونةً
    بأوزانها النسبية، ثم تحويل النسبة المئوية النهائية إلى:
        * تقدير حرفي (grade_letter_id)
        * قيمة GPA (gpa_value)
        * حالة نجاح/رسوب (is_passing)
        * ترتيب الطالب ضمن السجل (rank)
    """
    _name = 'uni.gradebook.final'
    _description = 'Gradebook Final Grade'
    _inherit = ['mail.thread']
    _order = 'gradebook_id, final_percentage desc, id'

    # ------------------------------------------------------------------
    # Relations
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Reference', compute='_compute_name', store=True, index=True,
        help='Display name built from student, course and term.')
    gradebook_id = fields.Many2one(
        'uni.gradebook', string='Gradebook',
        required=True, ondelete='cascade', tracking=True, index=True)
    gradebook_line_id = fields.Many2one(
        'uni.gradebook.line', string='Student Line',
        required=True, ondelete='cascade', tracking=True, index=True)
    student_id = fields.Many2one(
        'uni.student', string='Student',
        related='gradebook_line_id.student_id', store=True, index=True)

    # ------------------------------------------------------------------
    # Course context (denormalized for fast list / pivot rendering)
    # ------------------------------------------------------------------
    course_id = fields.Many2one(
        'uni.course', string='Course',
        related='gradebook_id.course_id', store=True, index=True)
    academic_term_id = fields.Many2one(
        'uni.academic.term', string='Term',
        related='gradebook_id.academic_term_id', store=True, index=True)
    credit_hours = fields.Float(
        string='Credit Hours',
        related='gradebook_id.course_id.credit_hours', store=True,
        help='Credit hours of the course for this final grade.')

    # ------------------------------------------------------------------
    # Computed scores
    # ------------------------------------------------------------------
    final_score = fields.Float(
        string='Final Score', digits=(5, 2), default=0.0,
        compute='_compute_final_score', store=True,
        help='Weighted sum of all (entry.score * entry.weight / 100).')
    final_percentage = fields.Float(
        string='Final %', digits=(5, 2), default=0.0,
        compute='_compute_final_percentage', store=True,
        help='Final score normalized to a 0-100 percentage.')
    grade_letter_id = fields.Many2one(
        'uni.grade.letter', string='Grade Letter',
        compute='_compute_grade_letter', store=True, ondelete='restrict',
        help='Letter grade derived from the final percentage.')
    gpa_value = fields.Float(
        string='GPA Value', digits=(4, 2), default=0.0,
        compute='_compute_gpa_value', store=True,
        help='GPA point value derived from the grade letter (or computed '
             'from the percentage if no letter is found).')
    is_passing = fields.Boolean(
        string='Passing', default=False,
        compute='_compute_is_passing', store=True,
        help='True when the final percentage is greater than or equal to the '
             'grading system\'s passing grade.')

    # ------------------------------------------------------------------
    # Ranking
    # ------------------------------------------------------------------
    rank = fields.Integer(
        string='Rank', default=0,
        compute='_compute_rank',
        help='Rank of this student within the gradebook (1 = highest score).')

    # ------------------------------------------------------------------
    # State / metadata
    # ------------------------------------------------------------------
    remarks = fields.Text(string='Remarks')
    state = fields.Selection([
        ('computed', 'Computed'),
        ('locked', 'Locked'),
    ], string='Status', default='computed', tracking=True, index=True,
        group_expand='_group_expand_states')
    computation_date = fields.Datetime(
        string='Computation Date', default=fields.Datetime.now, tracking=True,
        help='Last time this final grade was (re)computed.')

    _sql_constraints = [
        ('unique_final_per_line',
         'unique(gradebook_line_id)',
         'Each student line can have only one final grade record!'),
    ]

    # ------------------------------------------------------------------
    # Group expansion helper
    # ------------------------------------------------------------------
    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in self._fields['state'].selection]

    # ------------------------------------------------------------------
    # Computed: display name (student + course + term)
    # ------------------------------------------------------------------
    @api.depends('student_id', 'course_id', 'academic_term_id')
    def _compute_name(self):
        for rec in self:
            parts = []
            if rec.student_id:
                parts.append(rec.student_id.display_name)
            if rec.course_id:
                parts.append(rec.course_id.code or rec.course_id.display_name)
            if rec.academic_term_id:
                parts.append(rec.academic_term_id.code or rec.academic_term_id.display_name)
            rec.name = ' - '.join(parts) if parts else _('New')

    # ------------------------------------------------------------------
    # Create — sync back to the gradebook line (One2one)
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.gradebook_line_id and not rec.gradebook_line_id.final_id:
                rec.gradebook_line_id.final_id = rec.id
        return records

    # ------------------------------------------------------------------
    # Computed: final score, percentage, grade letter, GPA, passing, rank
    # ------------------------------------------------------------------
    @api.depends('gradebook_line_id.entry_ids.score',
                 'gradebook_line_id.entry_ids.weight',
                 'gradebook_line_id.entry_ids.max_score',
                 'gradebook_line_id.entry_ids.is_excused',
                 'gradebook_line_id.entry_ids.percentage')
    def _compute_final_score(self):
        """Compute the weighted final score on a 0-100 scale.

        Formula (per spec): sum of (entry.score * entry.weight / 100)
        Excused entries are excluded from the sum.
        """
        for rec in self:
            entries = rec.gradebook_line_id.entry_ids.filtered(
                lambda e: not e.is_excused)
            if not entries:
                rec.final_score = 0.0
                continue
            total = sum(
                (e.score or 0.0) * (e.weight or 0.0) / 100.0
                for e in entries)
            rec.final_score = total

    @api.depends('final_score',
                 'gradebook_line_id.entry_ids.weight',
                 'gradebook_line_id.entry_ids.is_excused',
                 'gradebook_line_id.entry_ids.max_score')
    def _compute_final_percentage(self):
        """Normalize the final score to a 0-100 percentage.

        If the entries' weights sum to less than 100, the final_score
        represents only a partial contribution. We normalize by dividing
        by the total weight and multiplying by 100 (capped to 0-100).
        """
        for rec in self:
            entries = rec.gradebook_line_id.entry_ids.filtered(
                lambda e: not e.is_excused)
            total_weight = sum((e.weight or 0.0) for e in entries)
            if total_weight > 0:
                percentage = (rec.final_score * 100.0) / total_weight
                rec.final_percentage = min(max(percentage, 0.0), 100.0)
            else:
                rec.final_percentage = 0.0

    @api.depends('final_percentage', 'gradebook_id.grading_system_id')
    def _compute_grade_letter(self):
        """Derive the grade letter from the final percentage using the
        gradebook's grading system scale.
        """
        for rec in self:
            if not rec.gradebook_id or not rec.gradebook_id.grading_system_id:
                rec.grade_letter_id = False
                continue
            system = rec.gradebook_id.grading_system_id
            letter = system.get_grade_letter_for_percentage(rec.final_percentage)
            rec.grade_letter_id = letter.id if letter else False

    @api.depends('grade_letter_id', 'final_percentage',
                 'gradebook_id.grading_system_id')
    def _compute_gpa_value(self):
        """GPA value: prefer the grade letter's gpa_value, fall back to
        the grading system's compute_gpa_value(percentage).
        """
        for rec in self:
            if rec.grade_letter_id:
                rec.gpa_value = rec.grade_letter_id.gpa_value or 0.0
            elif rec.gradebook_id and rec.gradebook_id.grading_system_id:
                rec.gpa_value = rec.gradebook_id.grading_system_id.compute_gpa_value(
                    rec.final_percentage)
            else:
                rec.gpa_value = 0.0

    @api.depends('final_percentage', 'gradebook_id.grading_system_id')
    def _compute_is_passing(self):
        """A final grade is passing when final_percentage >= the grading
        system's passing grade threshold.
        """
        for rec in self:
            system = rec.gradebook_id.grading_system_id if rec.gradebook_id else False
            passing_grade = system.passing_grade if system else 60.0
            rec.is_passing = rec.final_percentage >= passing_grade

    @api.depends('final_percentage', 'gradebook_id.final_ids.final_percentage',
                 'gradebook_id.final_ids.state', 'state')
    def _compute_rank(self):
        """Rank within the gradebook by final_percentage (descending).
        Ties share the same rank.
        """
        for rec in self:
            if not rec.gradebook_id:
                rec.rank = 0
                continue
            other_finals = rec.gradebook_id.final_ids.filtered(
                lambda f: f.state in ('computed', 'locked') and f.id != rec.id)
            # Count how many finals have a strictly higher percentage
            higher = sum(
                1 for f in other_finals
                if f.final_percentage > rec.final_percentage)
            rec.rank = higher + 1

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_lock(self):
        """Lock individual final grades (e.g. before gradebook is locked)."""
        for rec in self:
            rec.state = 'locked'

    def action_unlock(self):
        """Unlock a locked final grade."""
        for rec in self:
            if rec.gradebook_id.state == 'locked':
                # Do not unlock if the parent gradebook is locked
                continue
            rec.state = 'computed'

    def action_recompute(self):
        """Force recomputation of this final grade."""
        for rec in self:
            rec.computation_date = fields.Datetime.now()
            # Trigger stored compute fields by reassigning
            rec._compute_final_score()
            rec._compute_final_percentage()
            rec._compute_grade_letter()
            rec._compute_gpa_value()
            rec._compute_is_passing()
            rec._compute_rank()
