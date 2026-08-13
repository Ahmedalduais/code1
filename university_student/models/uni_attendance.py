# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniAttendance(models.Model):
    """الحضور والغياب — سجل جلسة حضور لمقرر وفصل دراسي محددين.

    يُمثّل هذا النموذج سجل جلسة حضور واحد (محاضرة، معمل، امتحان...) لمقرر
    محدد ضمن فصل دراسي محدد. يحمل الخطوط (``uni.attendance.line``) التي
    تُفصّل حالة كل طالب في الجلسة (حاضر/غائب/متأخر/...)، ويمكن ربطه بعضو
    هيئة التدريس المسؤول عن الجلسة.

    سير العمل:
        draft → validated
    """
    _name = 'uni.attendance'
    _description = 'Student Attendance'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'date desc, course_id, id'

    name = fields.Char(
        string='Reference', copy=False, readonly=True, index=True,
        help='Auto-generated reference identifying this attendance session.')
    student_id = fields.Many2one(
        'uni.student', string='Primary Student',
        ondelete='restrict', tracking=True, index=True,
        help='Primary student associated with this attendance record. '
             'Used by the student smart-button to filter attendance records.')
    course_id = fields.Many2one(
        'uni.course', string='Course',
        required=True, ondelete='restrict', tracking=True, index=True)
    academic_term_id = fields.Many2one(
        'uni.academic.term', string='Academic Term',
        required=True, ondelete='restrict', tracking=True, index=True)
    faculty_name = fields.Char(
        string='Faculty Name', tracking=True, index=True,
        help='Name of the faculty member responsible for this session. '
             'Stored as plain text to avoid a hard dependency on '
             'university_faculty.')
    university_id = fields.Many2one(
        'uni.university', string='University',
        related='academic_term_id.university_id', store=True, index=True)

    date = fields.Date(
        string='Session Date', default=fields.Date.context_today,
        required=True, tracking=True)
    session_type = fields.Selection([
        ('lecture', 'Lecture'),
        ('lab', 'Lab'),
        ('tutorial', 'Tutorial'),
        ('exam', 'Exam'),
    ], string='Session Type', default='lecture', required=True, tracking=True, index=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('validated', 'Validated'),
    ], string='Status', default='draft', tracking=True, index=True,
        group_expand='_group_expand_states')
    notes = fields.Text(string='Notes', tracking=True)

    line_ids = fields.One2many(
        'uni.attendance.line', 'attendance_id', string='Attendance Lines', copy=True)
    line_count = fields.Integer(
        compute='_compute_line_count', string='Lines')
    present_count = fields.Integer(
        compute='_compute_present_count', string='Present')
    absent_count = fields.Integer(
        compute='_compute_present_count', string='Absent')
    attendance_percentage = fields.Float(
        string='Attendance %', digits=(5, 2), default=0.0,
        compute='_compute_attendance_percentage', store=True,
        help='Percentage of present/late/excused students in the session.')

    _sql_constraints = [
        ('unique_attendance_reference', 'unique(name)',
         'Attendance reference must be unique!'),
    ]

    # ------------------------------------------------------------------
    # Group expansion helper
    # ------------------------------------------------------------------
    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in self._fields['state'].selection]

    # ------------------------------------------------------------------
    # Computed
    # ------------------------------------------------------------------
    @api.depends('line_ids')
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    @api.depends('line_ids.status')
    def _compute_present_count(self):
        for rec in self:
            rec.present_count = len(rec.line_ids.filtered(
                lambda l: l.status in ('present', 'late', 'excused', 'medical_leave')))
            rec.absent_count = len(rec.line_ids.filtered(lambda l: l.status == 'absent'))

    @api.depends('line_ids.status', 'line_count')
    def _compute_attendance_percentage(self):
        for rec in self:
            if not rec.line_count:
                rec.attendance_percentage = 0.0
            else:
                attended = len(rec.line_ids.filtered(
                    lambda l: l.status in ('present', 'late', 'excused', 'medical_leave')))
                rec.attendance_percentage = (attended / rec.line_count) * 100.0

    # ------------------------------------------------------------------
    # Create — auto-generate reference
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.attendance') or _('ATT-NEW')
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_validate(self):
        """Validate the attendance session — locks the record from editing."""
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError(_(
                    "Only draft attendance sessions can be validated (%s).")
                    % rec.display_name)
            if not rec.line_ids:
                raise ValidationError(_(
                    "Cannot validate an attendance session without lines (%s).")
                    % rec.display_name)
            rec.state = 'validated'

    def action_draft(self):
        """Reset the attendance session to draft."""
        for rec in self:
            rec.state = 'draft'

    # ------------------------------------------------------------------
    # Smart buttons
    # ------------------------------------------------------------------
    def action_view_lines(self):
        self.ensure_one()
        return {
            'name': _('Attendance Lines'),
            'type': 'ir.actions.act_window',
            'res_model': 'uni.attendance.line',
            'view_mode': 'list,form',
            'domain': [('attendance_id', '=', self.id)],
            'context': {'default_attendance_id': self.id},
        }

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('state', 'line_ids')
    def _check_validated_has_lines(self):
        for rec in self:
            if rec.state == 'validated' and not rec.line_ids:
                raise ValidationError(_(
                    "A validated attendance session must have at least one line (%s).")
                    % rec.display_name)

    @api.constrains('academic_term_id', 'date')
    def _check_date_in_term(self):
        for rec in self:
            if rec.date and rec.academic_term_id:
                term = rec.academic_term_id
                if term.date_start and rec.date < term.date_start:
                    raise ValidationError(_(
                        "Session date %(date)s is before the term start date %(start)s.")
                        % {'date': rec.date, 'start': term.date_start})
                if term.date_end and rec.date > term.date_end:
                    raise ValidationError(_(
                        "Session date %(date)s is after the term end date %(end)s.")
                        % {'date': rec.date, 'end': term.date_end})
