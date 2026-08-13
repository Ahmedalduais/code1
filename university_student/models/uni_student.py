# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniStudent(models.Model):
    """الطالب — التصميم القياسي للوحدة.

    يستخدم وراثة التفويض ``_inherits`` من ``uni.person`` (الذي بدوره يفوّض
    ``res.partner``)، مما يجعل كل بيانات الهوية والاتصال متاحة مباشرة على
    سجل الطالب (name, email, phone, photo, gender, birth_date...).

    يوفّر هذا النموذج إدارة كاملة لدورة حياة الطالب:
        * البرنامج والقسم والكلية والفرع
        * المعدل التراكمي والساعات المكتسبة والموقف الأكاديمي
        * التسجيلات الأكاديمية والوثائق وسجل الحضور
        * المرشد الأكاديمي والممول والمعلومات الشخصية الإضافية
        * حالات الحالة (prospective/active/graduated/suspended/withdrawn/deceased)
    """
    _name = 'uni.student'
    _description = 'Student'
    _inherits = {'uni.person': 'person_id'}
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'student_code, name'

    # ------------------------------------------------------------------
    # Delegation
    # ------------------------------------------------------------------
    person_id = fields.Many2one(
        'uni.person', string='Person',
        required=True, ondelete='restrict', auto_join=True, index=True,
        help='Delegated person record holding identity & contact data.')

    # ------------------------------------------------------------------
    # Student identity
    # ------------------------------------------------------------------
    student_code = fields.Char(
        string='Student Code', copy=False, index=True, tracking=True,
        help='Unique internal code identifying the student.')
    barcode = fields.Char(
        string='Barcode', copy=False, index=True,
        help='Barcode used by the ID card / library / attendance scanners.')

    # ------------------------------------------------------------------
    # Academic affiliation
    # ------------------------------------------------------------------
    program_id = fields.Many2one(
        'uni.program', string='Program',
        ondelete='restrict', tracking=True, index=True)
    department_id = fields.Many2one(
        'uni.department', string='Department',
        ondelete='restrict', tracking=True, index=True)
    college_id = fields.Many2one(
        'uni.college', string='College',
        ondelete='restrict', tracking=True, index=True)
    branch_id = fields.Many2one(
        'uni.branch', string='Branch',
        ondelete='restrict', tracking=True, index=True)

    # ------------------------------------------------------------------
    # Academic standing / progress
    # ------------------------------------------------------------------
    status_id = fields.Many2one(
        'uni.student.status', string='Student Status',
        ondelete='restrict', tracking=True, index=True)
    current_level = fields.Integer(
        string='Current Level', default=1, tracking=True,
        help='Academic level/year currently being studied (1, 2, 3...).')
    admission_date = fields.Date(string='Admission Date', tracking=True)
    expected_graduation_date = fields.Date(string='Expected Graduation', tracking=True)
    actual_graduation_date = fields.Date(string='Actual Graduation', tracking=True)
    state = fields.Selection([
        ('prospective', 'Prospective'),
        ('active', 'Active'),
        ('graduated', 'Graduated'),
        ('suspended', 'Suspended'),
        ('withdrawn', 'Withdrawn'),
        ('deceased', 'Deceased'),
    ], string='State', default='prospective', tracking=True, index=True,
        group_expand='_group_expand_states')

    cumulative_gpa = fields.Float(
        string='Cumulative GPA', digits=(4, 2), default=0.0,
        compute='_compute_cumulative_gpa', store=True, tracking=True,
        help='Cumulative Grade Point Average computed from completed enrollments.')
    total_credits_earned = fields.Integer(
        string='Credits Earned', default=0,
        compute='_compute_credits', store=True,
        help='Total credit hours successfully earned across all enrollments.')
    total_credits_required = fields.Integer(
        string='Credits Required',
        related='program_id.credit_hours', store=True,
        help='Total credit hours required by the program for graduation.')
    academic_standing = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('probation', 'Academic Probation'),
        ('dismissed', 'Dismissed'),
    ], string='Academic Standing', default='good',
        compute='_compute_standing', store=True, tracking=True,
        help='Academic standing derived from the cumulative GPA.')

    # ------------------------------------------------------------------
    # Academic guidance / sponsorship
    # ------------------------------------------------------------------
    advisor_name = fields.Char(
        string='Advisor Name', tracking=True, index=True,
        help='Name of the faculty member serving as the academic advisor '
             'for this student. Stored as plain text to avoid a hard '
             'dependency on university_faculty.')
    sponsor = fields.Char(string='Sponsor', tracking=True,
                          help='Person or organization financially sponsoring the student.')
    sponsor_phone = fields.Char(string='Sponsor Phone', tracking=True)

    # ------------------------------------------------------------------
    # Student type & transfer info
    # ------------------------------------------------------------------
    student_type = fields.Selection([
        ('regular', 'Regular'),
        ('transfer', 'Transfer'),
        ('exchange', 'Exchange'),
        ('visiting', 'Visiting'),
    ], string='Student Type', default='regular', tracking=True, index=True)
    transfer_university = fields.Char(
        string='Transfer University', tracking=True,
        help='Previous university name if the student transferred in.')

    # ------------------------------------------------------------------
    # Guardian
    # ------------------------------------------------------------------
    guardian_name = fields.Char(string='Guardian Name', tracking=True)
    guardian_phone = fields.Char(string='Guardian Phone', tracking=True)
    guardian_relationship = fields.Char(string='Guardian Relationship', tracking=True,
                                        help='Relationship to the student (e.g. Father, Mother).')

    # ------------------------------------------------------------------
    # Relations
    # ------------------------------------------------------------------
    enrollment_ids = fields.One2many(
        'uni.student.enrollment', 'student_id', string='Enrollments')
    document_ids = fields.One2many(
        'uni.student.document', 'student_id', string='Documents')
    attendance_ids = fields.One2many(
        'uni.attendance', 'student_id', string='Attendance Records')

    # ------------------------------------------------------------------
    # Computed counts for smart buttons
    # ------------------------------------------------------------------
    enrollment_count = fields.Integer(
        compute='_compute_enrollment_count', string='Enrollments')
    document_count = fields.Integer(
        compute='_compute_document_count', string='Documents')
    attendance_count = fields.Integer(
        compute='_compute_attendance_count', string='Attendance Sessions')
    active_enrollment_count = fields.Integer(
        compute='_compute_enrollment_count', string='Active Enrollments')

    _sql_constraints = [
        ('unique_student_code', 'unique(student_code)',
         'Student code must be unique!'),
        ('unique_barcode', 'unique(barcode)',
         'Barcode must be unique!'),
    ]

    # ------------------------------------------------------------------
    # Group expansion helper for state field
    # ------------------------------------------------------------------
    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in self._fields['state'].selection]

    # ------------------------------------------------------------------
    # Computed: cumulative GPA, credits, standing, counts
    # ------------------------------------------------------------------
    @api.depends('enrollment_ids.cumulative_gpa', 'enrollment_ids.state')
    def _compute_cumulative_gpa(self):
        """Compute cumulative GPA from completed enrollments.

        Placeholder policy: average of ``cumulative_gpa`` on enrollments
        whose state is ``completed``. The gradebook module may override
        this method to provide the official weighted calculation.
        """
        for rec in self:
            completed = rec.enrollment_ids.filtered(
                lambda e: e.state == 'completed' and e.cumulative_gpa > 0.0)
            if completed:
                rec.cumulative_gpa = sum(completed.mapped('cumulative_gpa')) / len(completed)
            else:
                rec.cumulative_gpa = 0.0

    @api.depends('enrollment_ids.total_credits_earned', 'enrollment_ids.state')
    def _compute_credits(self):
        """Compute total credits earned across all completed enrollments."""
        for rec in self:
            completed = rec.enrollment_ids.filtered(lambda e: e.state == 'completed')
            rec.total_credits_earned = int(sum(completed.mapped('total_credits_earned')))

    @api.depends('cumulative_gpa')
    def _compute_standing(self):
        """Derive academic standing from cumulative GPA."""
        for rec in self:
            gpa = rec.cumulative_gpa or 0.0
            if gpa >= 3.5:
                rec.academic_standing = 'excellent'
            elif gpa >= 2.0:
                rec.academic_standing = 'good'
            elif gpa >= 1.0:
                rec.academic_standing = 'probation'
            else:
                rec.academic_standing = 'dismissed'

    @api.depends('enrollment_ids')
    def _compute_enrollment_count(self):
        for rec in self:
            rec.enrollment_count = len(rec.enrollment_ids)
            rec.active_enrollment_count = len(
                rec.enrollment_ids.filtered(lambda e: e.state == 'enrolled'))

    @api.depends('document_ids')
    def _compute_document_count(self):
        for rec in self:
            rec.document_count = len(rec.document_ids)

    @api.depends('attendance_ids')
    def _compute_attendance_count(self):
        for rec in self:
            rec.attendance_count = len(rec.attendance_ids)

    # ------------------------------------------------------------------
    # Onchange — keep hierarchy consistent
    # ------------------------------------------------------------------
    @api.onchange('college_id')
    def _onchange_college_id(self):
        if self.college_id:
            self.university_id = self.college_id.university_id
            if self.college_id.branch_id:
                self.branch_id = self.college_id.branch_id

    @api.onchange('department_id')
    def _onchange_department_id(self):
        if self.department_id:
            self.college_id = self.department_id.college_id
            self.university_id = self.department_id.university_id
            if self.department_id.college_id.branch_id:
                self.branch_id = self.department_id.college_id.branch_id

    @api.onchange('program_id')
    def _onchange_program_id(self):
        if self.program_id:
            self.college_id = self.program_id.college_id
            self.department_id = self.program_id.department_id
            self.university_id = self.program_id.university_id
            if self.program_id.branch_id:
                self.branch_id = self.program_id.branch_id

    # ------------------------------------------------------------------
    # Create — auto-set person_type and infer university hierarchy
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('person_type'):
                vals['person_type'] = 'student'
            if not vals.get('university_id'):
                if vals.get('program_id'):
                    program = self.env['uni.program'].browse(vals['program_id'])
                    vals['university_id'] = program.university_id.id
                elif vals.get('department_id'):
                    dept = self.env['uni.department'].browse(vals['department_id'])
                    vals['university_id'] = dept.university_id.id
                elif vals.get('college_id'):
                    college = self.env['uni.college'].browse(vals['college_id'])
                    vals['university_id'] = college.university_id.id
            if not vals.get('student_code'):
                vals['student_code'] = self.env['ir.sequence'].next_by_code('uni.student') or _('STU-NEW')
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Lifecycle workflow actions
    # ------------------------------------------------------------------
    def action_activate(self):
        """Mark the student as active (currently enrolled)."""
        for rec in self:
            if rec.state in ('graduated', 'deceased'):
                raise ValidationError(_(
                    "Cannot activate a student in state '%(state)s' (%(name)s).")
                    % {'state': rec.state, 'name': rec.display_name})
            rec.state = 'active'

    def action_suspend(self):
        """Suspend the student (blocks enrollment)."""
        for rec in self:
            if rec.state in ('graduated', 'deceased', 'withdrawn'):
                raise ValidationError(_(
                    "Cannot suspend a student in state '%(state)s' (%(name)s).")
                    % {'state': rec.state, 'name': rec.display_name})
            rec.state = 'suspended'

    def action_graduate(self):
        """Mark the student as graduated — sets actual graduation date."""
        for rec in self:
            if rec.state not in ('active', 'suspended'):
                raise ValidationError(_(
                    "Cannot graduate a student in state '%(state)s' (%(name)s).")
                    % {'state': rec.state, 'name': rec.display_name})
            if not rec.actual_graduation_date:
                rec.actual_graduation_date = fields.Date.context_today(rec)
            rec.state = 'graduated'

    def action_withdraw(self):
        """Withdraw the student from the university."""
        for rec in self:
            if rec.state in ('graduated', 'deceased'):
                raise ValidationError(_(
                    "Cannot withdraw a student in state '%(state)s' (%(name)s).")
                    % {'state': rec.state, 'name': rec.display_name})
            rec.state = 'withdrawn'

    def action_reactivate(self):
        """Reactivate a previously suspended or withdrawn student."""
        for rec in self:
            if rec.state not in ('suspended', 'withdrawn'):
                raise ValidationError(_(
                    "Cannot reactivate a student in state '%(state)s' (%(name)s). "
                    "Only suspended or withdrawn students can be reactivated.")
                    % {'state': rec.state, 'name': rec.display_name})
            rec.state = 'active'

    # ------------------------------------------------------------------
    # Smart-button actions
    # ------------------------------------------------------------------
    def action_view_enrollments(self):
        self.ensure_one()
        return {
            'name': _('Enrollments'),
            'type': 'ir.actions.act_window',
            'res_model': 'uni.student.enrollment',
            'view_mode': 'list,form',
            'domain': [('student_id', '=', self.id)],
            'context': {'default_student_id': self.id,
                        'default_program_id': self.program_id.id if self.program_id else False},
        }

    def action_view_documents(self):
        self.ensure_one()
        return {
            'name': _('Documents'),
            'type': 'ir.actions.act_window',
            'res_model': 'uni.student.document',
            'view_mode': 'list,form',
            'domain': [('student_id', '=', self.id)],
            'context': {'default_student_id': self.id},
        }

    def action_view_attendance(self):
        self.ensure_one()
        return {
            'name': _('Attendance'),
            'type': 'ir.actions.act_window',
            'res_model': 'uni.attendance',
            'view_mode': 'list,form',
            'domain': [('student_id', '=', self.id)],
            'context': {'default_student_id': self.id},
        }

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('admission_date', 'expected_graduation_date', 'actual_graduation_date')
    def _check_dates(self):
        for rec in self:
            if rec.expected_graduation_date and rec.admission_date and \
                    rec.expected_graduation_date < rec.admission_date:
                raise ValidationError(_(
                    "Expected graduation date cannot be earlier than admission date "
                    "for student %s.") % rec.display_name)
            if rec.actual_graduation_date and rec.admission_date and \
                    rec.actual_graduation_date < rec.admission_date:
                raise ValidationError(_(
                    "Actual graduation date cannot be earlier than admission date "
                    "for student %s.") % rec.display_name)
            if rec.actual_graduation_date and rec.expected_graduation_date and \
                    rec.actual_graduation_date < rec.expected_graduation_date:
                raise ValidationError(_(
                    "Actual graduation date cannot be earlier than expected graduation "
                    "date for student %s.") % rec.display_name)

    @api.constrains('state', 'actual_graduation_date')
    def _check_graduation_state(self):
        for rec in self:
            if rec.state == 'graduated' and not rec.actual_graduation_date:
                raise ValidationError(_(
                    "A graduated student must have an actual graduation date (%s).")
                    % rec.display_name)
            if rec.state == 'deceased':
                # deceased is a terminal state — make sure no future graduation expected
                if rec.expected_graduation_date and rec.expected_graduation_date > fields.Date.context_today(rec):
                    raise ValidationError(_(
                        "A deceased student cannot have a future expected graduation date (%s).")
                        % rec.display_name)

    @api.constrains('current_level')
    def _check_current_level(self):
        for rec in self:
            if rec.current_level < 0:
                raise ValidationError(_(
                    "Current level cannot be negative for student %s.") % rec.display_name)
