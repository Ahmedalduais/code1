# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniExamAccommodation(models.Model):
    """تسهيلات الامتحان — تسهيلات يُقدَّم للطلاب ذوي الاحتياجات الخاصة
    أثناء الامتحانات (وقت إضافي، تقنيات مساعدة، غرفة منفصلة، إلخ).

    يستخدم هذا النموذج حقول ``Char`` لمعلومات الطالب (الاسم/الكود/البريد)
    بدل ``Many2one`` إلى ``uni.student`` لأن وحدة ``university_exam`` لا تعتمد
    على ``university_student`` (قاعدة الاعتماديات الصارمة).

    سير العمل:
        ``draft`` → ``submitted`` → ``under_review`` → ``approved``
                                                  ↘ ``denied`` → ``applied``
        يمكن إلغاء التسهيل من أي حالة عبر ``cancelled``.
    """
    _name = 'uni.exam.accommodation'
    _description = 'Exam Accommodation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'exam_id, accommodation_type'

    # ------------------------------------------------------------------
    # Identity & sequence
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True,
        default=lambda self: _('New'), index=True, tracking=True,
        help='Auto-generated reference for the accommodation (EAC/...).')

    # ------------------------------------------------------------------
    # Exam context
    # ------------------------------------------------------------------
    exam_id = fields.Many2one(
        'uni.exam', string='Exam', required=True, ondelete='cascade',
        tracking=True, index=True)
    course_id = fields.Many2one(
        'uni.course', related='exam_id.course_id',
        string='Course', store=True, readonly=True, index=True)
    academic_term_id = fields.Many2one(
        'uni.academic.term', related='exam_id.academic_term_id',
        string='Term', store=True, readonly=True, index=True)

    # ------------------------------------------------------------------
    # Student info (Char fields — cannot use Many2one to uni.student)
    # ------------------------------------------------------------------
    student_name = fields.Char(
        string='Student Name', required=True, tracking=True, index=True,
        help='Full name of the student requesting the accommodation. Stored '
             'as plain text because university_exam does not depend on '
             'university_student.')
    student_code = fields.Char(
        string='Student Code', required=True, tracking=True, index=True,
        help='Internal code of the student (e.g. STU/2025/00001).')
    student_email = fields.Char(
        string='Student Email', tracking=True,
        help='Contact email of the student.')

    # ------------------------------------------------------------------
    # Disability / accommodation info
    # ------------------------------------------------------------------
    disability_type = fields.Selection([
        ('visual', 'Visual Impairment'),
        ('hearing', 'Hearing Impairment'),
        ('mobility', 'Mobility Impairment'),
        ('learning', 'Learning Disability'),
        ('adhd', 'ADHD'),
        ('autism', 'Autism Spectrum'),
        ('chronic_illness', 'Chronic Illness'),
        ('psychological', 'Psychological Condition'),
        ('other', 'Other'),
    ], string='Disability Type', tracking=True, index=True)
    disability_description = fields.Text(
        string='Disability Description', tracking=True,
        help='Optional detailed description of the disability/condition.')

    accommodation_type = fields.Selection([
        ('extra_time', 'Extended Time'),
        ('assistive_tech', 'Assistive Technology'),
        ('alternative_format', 'Alternative Format (large print, Braille, audio)'),
        ('scribe', 'Scribe'),
        ('reader', 'Reader'),
        ('separate_room', 'Separate Testing Room'),
        ('breaks', 'Scheduled Breaks'),
        ('computer_based', 'Computer-Based Testing'),
        ('oral_exam', 'Oral Examination'),
        ('sign_language', 'Sign Language Interpreter'),
        ('wheelchair_access', 'Wheelchair Accessible Room'),
        ('other', 'Other Accommodation'),
    ], string='Accommodation Type', required=True, tracking=True, index=True)
    accommodation_details = fields.Text(
        string='Accommodation Details', required=True,
        help='Detailed description of the required accommodation.')

    # ------------------------------------------------------------------
    # Extra time specifics
    # ------------------------------------------------------------------
    extra_time_minutes = fields.Integer(
        string='Extra Time (Minutes)', default=0,
        help='Additional minutes allowed for the exam.')
    extra_time_percentage = fields.Integer(
        string='Extra Time (%)', default=0,
        help='Percentage of extra time (e.g. 50% extra).')

    # ------------------------------------------------------------------
    # Room and equipment
    # ------------------------------------------------------------------
    requires_separate_room = fields.Boolean(
        string='Requires Separate Room', default=False)
    room_requirements = fields.Text(string='Room Requirements')
    equipment_needed = fields.Text(string='Equipment Needed')

    # ------------------------------------------------------------------
    # Approval workflow
    # ------------------------------------------------------------------
    requested_date = fields.Date(
        string='Requested Date', default=fields.Date.context_today,
        tracking=True, index=True)
    medical_certificate = fields.Binary(
        string='Medical Certificate', attachment=True,
        help='Uploaded medical certificate supporting the request.')
    medical_certificate_filename = fields.Char(
        string='Medical Certificate Filename')

    approved_by = fields.Many2one(
        'res.users', string='Approved By', readonly=True, tracking=True,
        index=True)
    approved_date = fields.Date(
        string='Approved Date', readonly=True, tracking=True)
    approval_comments = fields.Text(string='Approval Comments')
    denial_reason = fields.Text(string='Denial Reason')

    # ------------------------------------------------------------------
    # State & validity
    # ------------------------------------------------------------------
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('denied', 'Denied'),
        ('applied', 'Applied to Exam'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, index=True,
        group_expand='_group_expand_states')
    expiry_date = fields.Date(
        string='Accommodation Expiry Date', tracking=True,
        help='Date until which this accommodation is valid.')
    is_recurring = fields.Boolean(
        string='Recurring Accommodation', default=False,
        help='If True, applies to all exams in the term.')
    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_accommodation_reference', 'unique(name)',
         'Accommodation reference must be unique!'),
        ('check_extra_time_positive', 'check(extra_time_minutes >= 0)',
         'Extra time must be positive!'),
        ('check_extra_time_percentage', 'check(extra_time_percentage >= 0)',
         'Extra time percentage must be positive!'),
    ]

    # ------------------------------------------------------------------
    # Group expand helper
    # ------------------------------------------------------------------
    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in self._fields['state'].selection]

    # ------------------------------------------------------------------
    # Create — auto-generate reference from ir.sequence
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.exam.accommodation') or _('EAC-NEW')
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_submit(self):
        """Submit the accommodation request for review."""
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError(_(
                    "Only draft accommodations can be submitted (current: %(state)s).")
                    % {'state': rec.state})
            rec.state = 'submitted'
            rec.message_post(body=_('Accommodation request submitted.'))

    def action_start_review(self):
        """Move the request into the under_review state."""
        for rec in self:
            if rec.state != 'submitted':
                raise ValidationError(_(
                    "Only submitted accommodations can be reviewed (current: %(state)s).")
                    % {'state': rec.state})
            rec.state = 'under_review'
            rec.message_post(body=_('Review started.'))

    def action_approve(self):
        """Approve the accommodation request."""
        for rec in self:
            if rec.state != 'under_review':
                raise ValidationError(_(
                    "Only accommodations under review can be approved (current: %(state)s).")
                    % {'state': rec.state})
            rec.write({
                'state': 'approved',
                'approved_by': self.env.uid,
                'approved_date': fields.Date.context_today(self),
            })
            rec.message_post(body=_('Accommodation approved.'))

    def action_deny(self):
        """Deny the accommodation request — requires a denial reason."""
        for rec in self:
            if rec.state != 'under_review':
                raise ValidationError(_(
                    "Only accommodations under review can be denied (current: %(state)s).")
                    % {'state': rec.state})
            if not rec.denial_reason:
                raise ValidationError(_(
                    "Cannot deny accommodation '%s' without providing a denial reason.")
                    % rec.display_name)
            rec.state = 'denied'
            rec.message_post(body=_('Accommodation denied.'))

    def action_apply(self):
        """Mark that the accommodation was applied to the exam."""
        for rec in self:
            if rec.state != 'approved':
                raise ValidationError(_(
                    "Only approved accommodations can be applied to the exam "
                    "(current: %(state)s).") % {'state': rec.state})
            rec.state = 'applied'
            rec.message_post(body=_('Accommodation applied to exam.'))

    def action_cancel(self):
        """Cancel the accommodation request."""
        for rec in self:
            if rec.state in ('applied', 'cancelled'):
                raise ValidationError(_(
                    "Cannot cancel an accommodation that is already %(state)s.")
                    % {'state': rec.state})
            rec.state = 'cancelled'
            rec.message_post(body=_('Accommodation cancelled.'))

    def action_reset_to_draft(self):
        """Reset a denied/cancelled request back to draft for editing."""
        for rec in self:
            if rec.state not in ('denied', 'cancelled'):
                raise ValidationError(_(
                    "Only denied or cancelled accommodations can be reset to draft."))
            rec.state = 'draft'
            rec.message_post(body=_('Accommodation reset to draft.'))

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('extra_time_minutes', 'extra_time_percentage')
    def _check_extra_time(self):
        """At least one of (minutes, percentage) should be set when the
        accommodation type is extra_time."""
        for rec in self:
            if rec.accommodation_type == 'extra_time' \
                    and rec.extra_time_minutes == 0 \
                    and rec.extra_time_percentage == 0:
                raise ValidationError(_(
                    "Accommodation '%s' of type 'Extended Time' must specify "
                    "either extra minutes or extra percentage.")
                    % rec.display_name)
