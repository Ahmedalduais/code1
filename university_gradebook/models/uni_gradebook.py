# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniGradebook(models.Model):
    """سجل الدرجات الرئيسي — يمثل دفتر درجات مقرر لفصل دراسي معين.

    يحتوي على خطوط الطلاب المسجلين، إدخالات الدرجات الفردية لكل طالب،
    والدرجات النهائية المحسوبة. يدعم سير عمل:
        draft → active → locked → closed
                       ↘ (يمكن العودة إلى draft من active فقط)
    """
    _name = 'uni.gradebook'
    _description = 'University Gradebook'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'academic_term_id desc, course_id, section, id'

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Reference', copy=False, readonly=True, index=True,
        default='New', tracking=True,
        help='Auto-generated reference identifying this gradebook.')
    code = fields.Char(
        string='Code', copy=False, tracking=True, index=True,
        help='Optional human-friendly code (e.g. GB-CS101-FALL2025).')

    # ------------------------------------------------------------------
    # Academic context
    # ------------------------------------------------------------------
    course_id = fields.Many2one(
        'uni.course', string='Course',
        required=True, ondelete='restrict', tracking=True, index=True)
    academic_term_id = fields.Many2one(
        'uni.academic.term', string='Academic Term',
        required=True, ondelete='restrict', tracking=True, index=True)
    academic_year_id = fields.Many2one(
        'uni.academic.year', string='Academic Year',
        related='academic_term_id.academic_year_id', store=True, index=True)
    university_id = fields.Many2one(
        'uni.university', string='University',
        related='academic_term_id.university_id', store=True, index=True)
    faculty_name = fields.Char(
        string='Instructor Name', tracking=True, index=True,
        help='Name of the faculty member responsible for teaching this section.')
    program_id = fields.Many2one(
        'uni.program', string='Program',
        ondelete='restrict', tracking=True, index=True)
    grading_system_id = fields.Many2one(
        'uni.grading.system', string='Grading System',
        required=True, ondelete='restrict', tracking=True, index=True,
        default=lambda self: self.env['uni.grading.system'].get_default_system())
    section = fields.Char(
        string='Section', tracking=True, index=True,
        help='Section identifier (e.g. A, B, 01) — used together with course '
             'and term to uniquely identify a gradebook.')

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('locked', 'Locked'),
        ('closed', 'Closed'),
    ], string='Status', default='draft', tracking=True, index=True,
        group_expand='_group_expand_states')
    publish_date = fields.Date(
        string='Publish Date', readonly=True, tracking=True,
        help='Date when the gradebook was activated and grades became visible.')
    lock_date = fields.Datetime(
        string='Lock Date', readonly=True, tracking=True,
        help='Timestamp when the gradebook was locked for grade changes.')

    # ------------------------------------------------------------------
    # Relations
    # ------------------------------------------------------------------
    line_ids = fields.One2many(
        'uni.gradebook.line', 'gradebook_id', string='Student Lines', copy=True)
    entry_ids = fields.One2many(
        'uni.gradebook.entry', 'gradebook_id', string='Grade Entries')
    final_ids = fields.One2many(
        'uni.gradebook.final', 'gradebook_id', string='Final Grades')

    # ------------------------------------------------------------------
    # Computed
    # ------------------------------------------------------------------
    student_count = fields.Integer(
        compute='_compute_student_count', string='Students',
        help='Number of student lines in this gradebook.')
    entry_count = fields.Integer(
        compute='_compute_entry_count', string='Entries',
        help='Number of grade entries recorded for this gradebook.')
    final_count = fields.Integer(
        compute='_compute_final_count', string='Finals',
        help='Number of computed final grades for this gradebook.')
    average_score = fields.Float(
        string='Class Average', digits=(5, 2), default=0.0,
        compute='_compute_average', store=True,
        help='Average final score across all students in this gradebook.')
    pass_rate = fields.Float(
        string='Pass Rate %', digits=(5, 2), default=0.0,
        compute='_compute_pass_rate', store=True,
        help='Percentage of students who passed the course.')
    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True, tracking=True)

    _sql_constraints = [
        ('unique_gradebook_course_term_section',
         'unique(course_id, academic_term_id, section)',
         'A gradebook already exists for this course, term and section!'),
    ]

    # ------------------------------------------------------------------
    # Group expansion helper
    # ------------------------------------------------------------------
    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in self._fields['state'].selection]

    # ------------------------------------------------------------------
    # Computed: counts, average, pass rate
    # ------------------------------------------------------------------
    @api.depends('line_ids')
    def _compute_student_count(self):
        for rec in self:
            rec.student_count = len(rec.line_ids)

    @api.depends('entry_ids')
    def _compute_entry_count(self):
        for rec in self:
            rec.entry_count = len(rec.entry_ids)

    @api.depends('final_ids')
    def _compute_final_count(self):
        for rec in self:
            rec.final_count = len(rec.final_ids)

    @api.depends('final_ids.final_score', 'final_ids.state')
    def _compute_average(self):
        """Average final score across locked / computed final grades."""
        for rec in self:
            finals = rec.final_ids.filtered(
                lambda f: f.state in ('computed', 'locked'))
            if finals:
                rec.average_score = sum(finals.mapped('final_score')) / len(finals)
            else:
                rec.average_score = 0.0

    @api.depends('final_ids.is_passing', 'final_ids.state')
    def _compute_pass_rate(self):
        """Pass rate = passing finals / total finals * 100."""
        for rec in self:
            finals = rec.final_ids.filtered(
                lambda f: f.state in ('computed', 'locked'))
            if finals:
                passing = len(finals.filtered(lambda f: f.is_passing))
                rec.pass_rate = (passing / len(finals)) * 100.0
            else:
                rec.pass_rate = 0.0

    # ------------------------------------------------------------------
    # Onchange helpers — keep academic context consistent
    # ------------------------------------------------------------------
    @api.onchange('course_id')
    def _onchange_course_id(self):
        """Pre-fill program and grading system from the course context."""
        if self.course_id:
            if not self.program_id:
                # Try to find a program-course link for this course
                link = self.env['uni.program.course'].search(
                    [('course_id', '=', self.course_id.id)], limit=1)
                if link:
                    self.program_id = link.program_id.id

    @api.onchange('academic_term_id')
    def _onchange_academic_term_id(self):
        """Infer university from the academic term."""
        if self.academic_term_id:
            self.university_id = self.academic_term_id.university_id.id

    # ------------------------------------------------------------------
    # Create — auto-generate reference and code
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.gradebook') or _('GB-NEW')
            if not vals.get('grading_system_id'):
                default_system = self.env['uni.grading.system'].get_default_system()
                if default_system:
                    vals['grading_system_id'] = default_system.id
            if not vals.get('code'):
                course_code = False
                if vals.get('course_id'):
                    course = self.env['uni.course'].browse(vals['course_id'])
                    course_code = course.code or False
                term_code = False
                if vals.get('academic_term_id'):
                    term = self.env['uni.academic.term'].browse(vals['academic_term_id'])
                    term_code = term.code or False
                section = vals.get('section') or ''
                parts = [p for p in ['GB', course_code, term_code, section] if p]
                vals['code'] = '-'.join(parts) if parts else False
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_activate(self):
        """Activate the gradebook: enable entry of scores.

        Requires at least one student line to be registered.
        """
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError(_(
                    "Only draft gradebooks can be activated (%s).") % rec.display_name)
            if not rec.line_ids:
                raise ValidationError(_(
                    "Cannot activate a gradebook without student lines (%s).")
                    % rec.display_name)
            rec.state = 'active'
            rec.publish_date = fields.Date.context_today(rec)

    def action_lock(self):
        """Lock the gradebook — no further grade changes allowed."""
        for rec in self:
            if rec.state != 'active':
                raise ValidationError(_(
                    "Only active gradebooks can be locked (%s).") % rec.display_name)
            rec.state = 'locked'
            rec.lock_date = fields.Datetime.now()
            # Mark all final grades as locked
            rec.final_ids.write({'state': 'locked'})

    def action_close(self):
        """Close the gradebook permanently."""
        for rec in self:
            if rec.state != 'locked':
                raise ValidationError(_(
                    "Only locked gradebooks can be closed (%s).") % rec.display_name)
            rec.state = 'closed'

    def action_draft(self):
        """Reset the gradebook to draft (only from active state)."""
        for rec in self:
            if rec.state == 'closed':
                raise ValidationError(_(
                    "Cannot reset a closed gradebook to draft (%s).") % rec.display_name)
            rec.state = 'draft'
            rec.publish_date = False
            rec.lock_date = False
            rec.final_ids.write({'state': 'computed'})

    def action_compute_finals(self):
        """Trigger computation of all final grades for this gradebook.

        Ensures each active student line has a final record, then recomputes
        the stored compute fields (final_score, final_percentage,
        grade_letter_id, gpa_value, is_passing, rank) by explicitly
        calling the compute methods.
        """
        for rec in self:
            if rec.state == 'draft':
                raise ValidationError(_(
                    "Cannot compute finals for a draft gradebook (%s). "
                    "Activate it first.") % rec.display_name)
            finals = self.env['uni.gradebook.final']
            for line in rec.line_ids.filtered(
                    lambda l: l.state == 'active'):
                final = line.final_id
                if not final:
                    final = finals.create({
                        'gradebook_id': rec.id,
                        'gradebook_line_id': line.id,
                        'state': 'computed',
                    })
                finals |= final
            # Force recomputation of stored compute fields on each final
            if finals:
                finals.write({'computation_date': fields.Datetime.now()})
                finals._compute_final_score()
                finals._compute_final_percentage()
                finals._compute_grade_letter()
                finals._compute_gpa_value()
                finals._compute_is_passing()
                finals._compute_rank()
                finals._compute_name()
            # Recompute aggregate fields on the gradebook
            rec._compute_average()
            rec._compute_pass_rate()
            rec._compute_final_count()
            rec.message_post(body=_(
                "Computed final grades for %d students.") % len(finals))

    # ------------------------------------------------------------------
    # Smart buttons
    # ------------------------------------------------------------------
    def action_view_lines(self):
        self.ensure_one()
        return {
            'name': _('Student Lines'),
            'type': 'ir.actions.act_window',
            'res_model': 'uni.gradebook.line',
            'view_mode': 'list,form',
            'domain': [('gradebook_id', '=', self.id)],
            'context': {'default_gradebook_id': self.id},
        }

    def action_view_entries(self):
        self.ensure_one()
        return {
            'name': _('Grade Entries'),
            'type': 'ir.actions.act_window',
            'res_model': 'uni.gradebook.entry',
            'view_mode': 'list,form',
            'domain': [('gradebook_id', '=', self.id)],
            'context': {'default_gradebook_id': self.id},
        }

    def action_view_finals(self):
        self.ensure_one()
        return {
            'name': _('Final Grades'),
            'type': 'ir.actions.act_window',
            'res_model': 'uni.gradebook.final',
            'view_mode': 'list,form,pivot',
            'domain': [('gradebook_id', '=', self.id)],
            'context': {'default_gradebook_id': self.id},
        }
