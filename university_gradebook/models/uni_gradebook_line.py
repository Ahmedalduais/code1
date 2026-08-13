# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniGradebookLine(models.Model):
    """خط سجل الدرجات — يمثل تسجيل طالب في سجل درجات معين.

    كل خط يربط الطالب بسجل الدرجات ويحمل:
        * حالة الطالب في السجل (active / withdrawn / exempted)
        * إدخالات الدرجات الفردية للطالب
        * الدرجة النهائية المحسوبة للطالب (علاقة One2one عبر final_id)
    """
    _name = 'uni.gradebook.line'
    _description = 'Gradebook Student Line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'gradebook_id, student_id, id'

    # ------------------------------------------------------------------
    # Identity (computed display name)
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Reference', compute='_compute_name', store=True, index=True,
        help='Display name built from student, gradebook and section.')

    # ------------------------------------------------------------------
    # Relations
    # ------------------------------------------------------------------
    gradebook_id = fields.Many2one(
        'uni.gradebook', string='Gradebook',
        required=True, ondelete='cascade', tracking=True, index=True)
    student_id = fields.Many2one(
        'uni.student', string='Student',
        required=True, ondelete='restrict', tracking=True, index=True)
    enrollment_line_id = fields.Many2one(
        'uni.student.enrollment.line', string='Enrollment Line',
        ondelete='set null', index=True,
        help='Optional link to the enrollment line for this course, used to '
             'keep the gradebook in sync with the student\'s enrollment.')

    # ------------------------------------------------------------------
    # Student info (denormalized for fast list rendering)
    # ------------------------------------------------------------------
    student_code = fields.Char(
        string='Student Code',
        related='student_id.student_code', store=True, index=True)
    student_name = fields.Char(
        string='Student Name',
        related='student_id.name', store=True, index=True)
    program_id = fields.Many2one(
        'uni.program', string='Program',
        related='student_id.program_id', store=True, index=True)

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------
    is_withdrawn = fields.Boolean(
        string='Withdrawn', default=False, tracking=True,
        help='True when the student withdrew from this gradebook.')
    state = fields.Selection([
        ('active', 'Active'),
        ('withdrawn', 'Withdrawn'),
        ('exempted', 'Exempted'),
    ], string='Line State', default='active', tracking=True, index=True,
        group_expand='_group_expand_states')

    # ------------------------------------------------------------------
    # Links to entries and final grade
    # ------------------------------------------------------------------
    entry_ids = fields.One2many(
        'uni.gradebook.entry', 'gradebook_line_id', string='Grade Entries')
    entry_count = fields.Integer(
        compute='_compute_entry_count', string='Entries',
        help='Number of grade entries recorded for this student line.')
    final_id = fields.Many2one(
        'uni.gradebook.final', string='Final Grade',
        ondelete='set null', copy=False, index=True,
        help='The computed final grade record for this student.')

    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('unique_gradebook_student',
         'unique(gradebook_id, student_id)',
         'A student cannot be registered twice in the same gradebook!'),
    ]

    # ------------------------------------------------------------------
    # Group expansion helper
    # ------------------------------------------------------------------
    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in self._fields['state'].selection]

    # ------------------------------------------------------------------
    # Computed
    # ------------------------------------------------------------------
    @api.depends('entry_ids')
    def _compute_entry_count(self):
        for rec in self:
            rec.entry_count = len(rec.entry_ids)

    @api.depends('student_id', 'student_name', 'student_code', 'gradebook_id')
    def _compute_name(self):
        for rec in self:
            parts = []
            if rec.student_name:
                parts.append(rec.student_name)
            elif rec.student_id:
                parts.append(rec.student_id.display_name)
            if rec.student_code:
                parts.append(rec.student_code)
            if rec.gradebook_id:
                parts.append(rec.gradebook_id.display_name)
            rec.name = ' - '.join(parts) if parts else _('New')

    # ------------------------------------------------------------------
    # Onchange
    # ------------------------------------------------------------------
    @api.onchange('student_id')
    def _onchange_student_id(self):
        """When a student is selected, try to pre-link their enrollment line."""
        if self.student_id and self.gradebook_id and self.gradebook_id.course_id:
            # Look for an enrollment line matching this student+course
            enrollment_line = self.env['uni.student.enrollment.line'].search([
                ('student_id', '=', self.student_id.id),
                ('course_id', '=', self.gradebook_id.course_id.id),
            ], limit=1)
            if enrollment_line:
                self.enrollment_line_id = enrollment_line.id

    @api.onchange('state')
    def _onchange_state(self):
        """Sync is_withdrawn flag with the state."""
        self.is_withdrawn = self.state == 'withdrawn'

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_withdraw(self):
        """Mark the student line as withdrawn from the gradebook."""
        for rec in self:
            if rec.state == 'exempted':
                raise ValidationError(_(
                    "Cannot withdraw an exempted student line (%s).")
                    % rec.display_name)
            rec.state = 'withdrawn'
            rec.is_withdrawn = True

    def action_exempt(self):
        """Mark the student line as exempted from the gradebook."""
        for rec in self:
            if rec.state == 'withdrawn':
                raise ValidationError(_(
                    "Cannot exempt a withdrawn student line (%s).")
                    % rec.display_name)
            rec.state = 'exempted'

    def action_reactivate(self):
        """Reactivate a withdrawn or exempted student line."""
        for rec in self:
            rec.state = 'active'
            rec.is_withdrawn = False

    def action_view_entries(self):
        self.ensure_one()
        return {
            'name': _('Grade Entries'),
            'type': 'ir.actions.act_window',
            'res_model': 'uni.gradebook.entry',
            'view_mode': 'list,form',
            'domain': [('gradebook_line_id', '=', self.id)],
            'context': {'default_gradebook_line_id': self.id,
                        'default_gradebook_id': self.gradebook_id.id},
        }
