# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniStudentTransfer(models.Model):
    """تحويلات الطلاب — داخل الجامعة (داخلي) أو من/إلى جامعة أخرى (خارجي).

    سير العمل:
        draft → approved → completed
                ↘ rejected
    عند الموافقة والاكتمال، تُحدّث بيانات الطالب تلقائياً لتناسب البرنامج/الكلية/القسم الجديد.
    """
    _name = 'uni.student.transfer'
    _description = 'Student Transfer'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'student_id, transfer_date desc, id'

    name = fields.Char(
        string='Reference', copy=False, readonly=True, index=True,
        help='Auto-generated reference identifying this transfer request.')
    student_id = fields.Many2one(
        'uni.student', string='Student',
        required=True, ondelete='restrict', tracking=True, index=True)
    transfer_date = fields.Date(
        string='Transfer Date', default=fields.Date.context_today, tracking=True, required=True)
    university_id = fields.Many2one(
        'uni.university', string='University',
        related='student_id.university_id', store=True, index=True)

    # ------------------------------------------------------------------
    # FROM (source)
    # ------------------------------------------------------------------
    from_program_id = fields.Many2one(
        'uni.program', string='From Program',
        ondelete='restrict', tracking=True,
        help='Program the student is transferring from (auto-filled from the student).')
    from_college_id = fields.Many2one(
        'uni.college', string='From College',
        ondelete='restrict', tracking=True)
    from_department_id = fields.Many2one(
        'uni.department', string='From Department',
        ondelete='restrict', tracking=True)

    # ------------------------------------------------------------------
    # TO (destination)
    # ------------------------------------------------------------------
    to_program_id = fields.Many2one(
        'uni.program', string='To Program',
        ondelete='restrict', tracking=True, required=True)
    to_college_id = fields.Many2one(
        'uni.college', string='To College',
        ondelete='restrict', tracking=True,
        help='Auto-filled from the destination program.')
    to_department_id = fields.Many2one(
        'uni.department', string='To Department',
        ondelete='restrict', tracking=True,
        help='Auto-filled from the destination program.')

    transfer_type = fields.Selection([
        ('internal', 'Internal'),
        ('external', 'External'),
    ], string='Transfer Type', default='internal', tracking=True, index=True,
        help='Internal = within the same university; External = to/from another university.')
    reason = fields.Text(string='Reason', tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
    ], string='Status', default='draft', tracking=True, index=True,
        group_expand='_group_expand_states')

    approved_by = fields.Many2one(
        'res.users', string='Approved By', readonly=True, copy=False, tracking=True)
    approved_date = fields.Datetime(
        string='Approved Date', readonly=True, copy=False, tracking=True)
    completed_by = fields.Many2one(
        'res.users', string='Completed By', readonly=True, copy=False, tracking=True)
    completed_date = fields.Datetime(
        string='Completed Date', readonly=True, copy=False, tracking=True)
    notes = fields.Text(string='Notes', tracking=True)

    _sql_constraints = [
        ('unique_transfer_reference', 'unique(name)',
         'Transfer reference must be unique!'),
    ]

    # ------------------------------------------------------------------
    # Group expansion helper
    # ------------------------------------------------------------------
    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in self._fields['state'].selection]

    # ------------------------------------------------------------------
    # Onchange — pre-fill FROM side from the student
    # ------------------------------------------------------------------
    @api.onchange('student_id')
    def _onchange_student_id(self):
        if self.student_id:
            self.from_program_id = self.student_id.program_id
            self.from_college_id = self.student_id.college_id
            self.from_department_id = self.student_id.department_id

    @api.onchange('to_program_id')
    def _onchange_to_program_id(self):
        if self.to_program_id:
            self.to_college_id = self.to_program_id.college_id
            self.to_department_id = self.to_program_id.department_id

    # ------------------------------------------------------------------
    # Create — auto-generate reference
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.student.transfer') or _('TRF-NEW')
            # Auto-populate FROM from the student if missing
            if vals.get('student_id') and not vals.get('from_program_id'):
                student = self.env['uni.student'].browse(vals['student_id'])
                if student.program_id:
                    vals.setdefault('from_program_id', student.program_id.id)
                if student.college_id:
                    vals.setdefault('from_college_id', student.college_id.id)
                if student.department_id:
                    vals.setdefault('from_department_id', student.department_id.id)
            # Auto-populate TO college/department from the destination program
            if vals.get('to_program_id'):
                program = self.env['uni.program'].browse(vals['to_program_id'])
                vals.setdefault('to_college_id', program.college_id.id if program.college_id else False)
                vals.setdefault('to_department_id', program.department_id.id if program.department_id else False)
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_approve(self):
        """Approve the transfer request (manager action)."""
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError(_(
                    "Only draft transfer requests can be approved (%s).") % rec.display_name)
            rec.write({
                'state': 'approved',
                'approved_by': self.env.uid,
                'approved_date': fields.Datetime.now(),
            })

    def action_reject(self):
        """Reject the transfer request."""
        for rec in self:
            if rec.state not in ('draft', 'approved'):
                raise ValidationError(_(
                    "Cannot reject a transfer in state '%s' (%s).")
                    % (rec.state, rec.display_name))
            rec.write({
                'state': 'rejected',
                'approved_by': self.env.uid,
                'approved_date': fields.Datetime.now(),
            })

    def action_complete(self):
        """Complete the transfer — apply changes to the student record.

        Sets the student's program/college/department to the destination
        values and posts a message on the student's chatter.
        """
        for rec in self:
            if rec.state != 'approved':
                raise ValidationError(_(
                    "Only approved transfers can be completed (%s).") % rec.display_name)
            student_vals = {
                'program_id': rec.to_program_id.id,
                'college_id': rec.to_college_id.id,
                'department_id': rec.to_department_id.id,
            }
            if rec.to_program_id and rec.to_program_id.branch_id:
                student_vals['branch_id'] = rec.to_program_id.branch_id.id
            rec.student_id.write(student_vals)
            rec.write({
                'state': 'completed',
                'completed_by': self.env.uid,
                'completed_date': fields.Datetime.now(),
            })
            rec.student_id.message_post(body=_(
                "Transfer %(ref)s completed: moved to program '%(prog)s'.") % {
                'ref': rec.name or _('TRF-NEW'),
                'prog': rec.to_program_id.display_name,
            })

    def action_draft(self):
        """Reset to draft (only from rejected)."""
        for rec in self:
            if rec.state != 'rejected':
                raise ValidationError(_(
                    "Only rejected transfers can be reset to draft (%s).") % rec.display_name)
            rec.state = 'draft'

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('from_program_id', 'to_program_id')
    def _check_different_programs(self):
        for rec in self:
            if rec.from_program_id and rec.to_program_id and \
                    rec.from_program_id == rec.to_program_id:
                raise ValidationError(_(
                    "Source and destination programs must differ in transfer %s.")
                    % rec.display_name)

    @api.constrains('transfer_type', 'from_program_id')
    def _check_internal_transfer(self):
        for rec in self:
            if rec.transfer_type == 'internal':
                if not rec.from_program_id:
                    raise ValidationError(_(
                        "Internal transfer %s must have a source program.") % rec.display_name)
                if rec.from_program_id and rec.to_program_id and \
                        rec.from_program_id.university_id != rec.to_program_id.university_id:
                    raise ValidationError(_(
                        "Internal transfer %s must be within the same university.") %
                        rec.display_name)
