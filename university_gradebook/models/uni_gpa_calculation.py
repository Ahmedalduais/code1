# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniGpaCalculation(models.Model):
    """حساب المعدل — يرث (وراثة كلاسيكية) من ``uni.grading.calculator``.

    يضيف على الحاسبة الأساسية:
        * ربط الطالب والفصل الدراسي
        * علاقة Many2many إلى الدرجات النهائية (uni.gradebook.final)
        * حساب المعدل الفصلي (term_gpa)
        * حساب المعدل التراكمي (cumulative_gpa)
        * كتابة المعدل التراكمي على سجل الطالب
    """
    _name = 'uni.gpa.calculation'
    _description = 'GPA Calculation'
    _inherit = ['uni.grading.calculator']
    _order = 'calc_date desc, id'

    # ------------------------------------------------------------------
    # Academic context (additional to the inherited calculator fields)
    # ------------------------------------------------------------------
    student_id = fields.Many2one(
        'uni.student', string='Student',
        required=True, ondelete='restrict', tracking=True, index=True)
    academic_term_id = fields.Many2one(
        'uni.academic.term', string='Academic Term',
        ondelete='restrict', tracking=True, index=True)

    # ------------------------------------------------------------------
    # Many2many to gradebook finals — the input dataset for the calculation
    # ------------------------------------------------------------------
    final_ids = fields.Many2many(
        'uni.gradebook.final', string='Final Grades',
        help='Final grade records used as input for this GPA calculation.')

    # ------------------------------------------------------------------
    # Computed totals
    # ------------------------------------------------------------------
    cumulative_gpa = fields.Float(
        string='Cumulative GPA', digits=(4, 2), default=0.0, tracking=True,
        help='Cumulative GPA computed across all completed terms.')
    term_gpa = fields.Float(
        string='Term GPA', digits=(4, 2), default=0.0, tracking=True,
        help='GPA computed for a single academic term.')
    total_credits_attempted = fields.Integer(
        string='Credits Attempted', default=0, tracking=True,
        help='Total credit hours attempted across all selected finals.')
    total_credits_earned = fields.Integer(
        string='Credits Earned', default=0, tracking=True,
        help='Total credit hours successfully earned (passing finals only).')
    total_quality_points = fields.Float(
        string='Quality Points', digits=(6, 2), default=0.0, tracking=True,
        help='Sum of (gpa_value * credit_hours) across all selected finals.')

    # ------------------------------------------------------------------
    # Create — use the GPA calculation sequence (override the parent's
    # behavior of using the calculator sequence)
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.gpa.calculation') or _('GPA-NEW')
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Onchange — pre-fill university & grading system from the student
    # ------------------------------------------------------------------
    @api.onchange('student_id')
    def _onchange_student_id(self):
        """When a student is selected, pre-fill university and grading system."""
        if self.student_id:
            if not self.university_id and self.student_id.university_id:
                self.university_id = self.student_id.university_id.id
            if not self.grading_system_id:
                default_system = self.env['uni.grading.system'].get_default_system()
                if default_system:
                    self.grading_system_id = default_system.id

    # ------------------------------------------------------------------
    # Business logic: term GPA, cumulative GPA, student record update
    # ------------------------------------------------------------------
    def action_calculate_term_gpa(self):
        """Compute the term GPA from the selected final_ids.

        Uses the grading engine's ``calculate_gpa`` method, which expects
        a list of dicts with ``gpa_value`` and ``credit_hours`` keys.
        Also computes totals (credits attempted / earned / quality points).
        """
        for rec in self:
            if not rec.final_ids:
                rec.term_gpa = 0.0
                rec.total_credits_attempted = 0
                rec.total_credits_earned = 0
                rec.total_quality_points = 0.0
                rec.result_gpa = 0.0
                rec.result_percentage = 0.0
                rec.state = 'calculated'
                rec.calc_date = fields.Datetime.now()
                continue
            course_grades = []
            for final in rec.final_ids:
                course_grades.append({
                    'gpa_value': final.gpa_value or 0.0,
                    'credit_hours': final.credit_hours or 0.0,
                })
            term_gpa = rec.calculate_gpa(
                course_grades, rec.grading_system_id.id if rec.grading_system_id else False)
            rec.term_gpa = term_gpa
            rec.result_gpa = term_gpa
            # Totals
            rec.total_credits_attempted = int(
                sum((f.credit_hours or 0.0) for f in rec.final_ids))
            rec.total_credits_earned = int(
                sum((f.credit_hours or 0.0) for f in rec.final_ids if f.is_passing))
            rec.total_quality_points = sum(
                (f.gpa_value or 0.0) * (f.credit_hours or 0.0)
                for f in rec.final_ids)
            # Average percentage across finals (weighted by credit hours)
            total_ch = sum((f.credit_hours or 0.0) for f in rec.final_ids)
            if total_ch > 0:
                rec.result_percentage = sum(
                    (f.final_percentage or 0.0) * (f.credit_hours or 0.0)
                    for f in rec.final_ids) / total_ch
            else:
                rec.result_percentage = 0.0
            # Determine academic status using the engine helper
            passing_gpa = (
                rec.grading_system_id.passing_grade / 25.0
                if rec.grading_system_id and rec.grading_system_id.passing_grade
                else 2.0)
            rec.result_status = rec.determine_status(term_gpa, passing_gpa)
            rec.state = 'calculated'
            rec.calc_date = fields.Datetime.now()

    def action_calculate_cumulative_gpa(self):
        """Compute cumulative GPA across all terms for the student.

        Gathers all ``uni.gradebook.final`` records for the student (across
        all gradebooks) and computes the weighted GPA using credit hours.
        Falls back to the term_gpa if no historical finals are found.
        """
        for rec in self:
            if not rec.student_id:
                raise ValidationError(_(
                    "A student is required to compute the cumulative GPA."))
            # Gather all final grades for this student
            all_finals = self.env['uni.gradebook.final'].search([
                ('student_id', '=', rec.student_id.id),
                ('state', 'in', ('computed', 'locked')),
            ])
            if not all_finals:
                rec.cumulative_gpa = rec.term_gpa
                continue
            course_grades = [{
                'gpa_value': f.gpa_value or 0.0,
                'credit_hours': f.credit_hours or 0.0,
            } for f in all_finals]
            cumulative = rec.calculate_gpa(
                course_grades,
                rec.grading_system_id.id if rec.grading_system_id else False)
            rec.cumulative_gpa = cumulative
            rec.result_gpa = cumulative
            passing_gpa = (
                rec.grading_system_id.passing_grade / 25.0
                if rec.grading_system_id and rec.grading_system_id.passing_grade
                else 2.0)
            rec.result_status = rec.determine_status(cumulative, passing_gpa)
            rec.state = 'calculated'
            rec.calc_date = fields.Datetime.now()

    def action_update_student_record(self):
        """Write the cumulative GPA back to the student record.

        This effectively overrides the placeholder ``cumulative_gpa`` compute
        method on ``uni.student`` by storing the official computed value.
        Note: ``uni.student.cumulative_gpa`` is a stored compute field, so
        writing directly to it may be reverted on the next compute trigger.
        Use this action after ensuring no further enrollment changes will
        recompute it, or extend ``uni.student._compute_cumulative_gpa`` to
        prefer this calculation when available.
        """
        for rec in self:
            if not rec.student_id:
                raise ValidationError(_(
                    "A student is required to update the student record."))
            if rec.cumulative_gpa <= 0.0:
                # Auto-compute first if not yet done
                rec.action_calculate_cumulative_gpa()
            # Write the official cumulative GPA to the student
            rec.student_id.sudo().write({
                'cumulative_gpa': rec.cumulative_gpa,
            })
            rec.message_post(body=_(
                "Updated student %s cumulative GPA to %s.") % (
                rec.student_id.display_name,
                f"{rec.cumulative_gpa:.2f}",
            ))

    def action_load_term_finals(self):
        """Auto-populate ``final_ids`` with all the student's finals for the
        selected academic term.
        """
        for rec in self:
            if not rec.student_id or not rec.academic_term_id:
                raise ValidationError(_(
                    "Both student and academic term are required to load "
                    "term finals."))
            finals = self.env['uni.gradebook.final'].search([
                ('student_id', '=', rec.student_id.id),
                ('academic_term_id', '=', rec.academic_term_id.id),
                ('state', 'in', ('computed', 'locked')),
            ])
            rec.final_ids = [(6, 0, finals.ids)]
