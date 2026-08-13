# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniFacultyAssignment(models.Model):
    """التكليف التدريسي — يربط عضو هيئة التدريس بمقرر دراسي (نصياً) وبرنامج
    خلال فصل دراسي محدد بنوع تكليف (رئيسي/ثانوي/تدريس مشترك).

    ملاحظة: لا توجد إشارة إلى ``uni.course`` لأن وحدة المناهج
    (``university_curriculum``) ليست اعتمادية لهذه الوحدة. يستخدم
    النموذج حقل ``course_name`` نصي و ``program_id`` للربط بالبرنامج.
    """
    _name = 'uni.faculty.assignment'
    _description = 'Faculty Teaching Assignment'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'academic_term_id desc, faculty_id, course_name'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True,
                      default=lambda self: _('New'), index=True)
    faculty_id = fields.Many2one(
        'uni.faculty', string='Faculty', required=True,
        ondelete='restrict', tracking=True, index=True)
    university_id = fields.Many2one(
        related='faculty_id.university_id', store=True, string='University', index=True)
    course_name = fields.Char(
        string='Course Name', required=True, tracking=True,
        help='Free-text course identifier (uni.course link not available in this module).')
    course_code = fields.Char(string='Course Code', help='Optional code for the course.')
    program_id = fields.Many2one(
        'uni.program', string='Program', ondelete='restrict', tracking=True, index=True)
    academic_term_id = fields.Many2one(
        'uni.academic.term', string='Academic Term',
        required=True, ondelete='restrict', tracking=True, index=True)
    assignment_type = fields.Selection([
        ('primary', 'Primary Instructor'),
        ('secondary', 'Secondary Instructor'),
        ('co_teaching', 'Co-Teaching'),
    ], string='Assignment Type', default='primary', tracking=True, index=True)
    section = fields.Char(string='Section', help='Section label (e.g. A, B, or 01).')
    student_count = fields.Integer(string='Student Count', default=0, tracking=True)
    start_date = fields.Date(string='Start Date', tracking=True)
    end_date = fields.Date(string='End Date', tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, index=True, group_expand='_group_expand_states')
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('unique_assignment_ref', 'unique(name)',
         'Assignment reference must be unique!'),
    ]

    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in self._fields['state'].selection]

    # ------------------------------------------------------------------
    # Create — auto-generate reference
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.faculty.assignment') or _('ASN-NEW')
        return super().create(vals_list)

    @api.onchange('academic_term_id')
    def _onchange_academic_term_id(self):
        if self.academic_term_id:
            if not self.start_date:
                self.start_date = self.academic_term_id.date_start
            if not self.end_date:
                self.end_date = self.academic_term_id.date_end

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_activate(self):
        for rec in self:
            if rec.state == 'cancelled':
                continue
            rec.state = 'active'

    def action_complete(self):
        for rec in self:
            rec.state = 'completed'

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'

    def action_draft(self):
        for rec in self:
            rec.state = 'draft'

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for rec in self:
            if rec.start_date and rec.end_date and rec.end_date < rec.start_date:
                raise ValidationError(_(
                    "Assignment end date cannot be earlier than start date (%s).")
                    % rec.display_name)

    @api.constrains('student_count')
    def _check_student_count(self):
        for rec in self:
            if rec.student_count < 0:
                raise ValidationError(_(
                    "Student count cannot be negative for assignment %s.") % rec.display_name)
