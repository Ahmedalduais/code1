# -*- coding: utf-8 -*-
import re

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


EMAIL_REGEX = r'^[^@\s]+@[^@\s]+\.[^@\s]+$'


class UniAdmissionApplication(models.Model):
    """طلب القبول الجامعي.

    يمثل دورة حياة كاملة لطلب التقديم على برنامج دراسي:
    ``draft → submitted → under_review → interview_scheduled
       → accepted / rejected / waitlisted → enrolled``

    عند الوصول لمرحلة القبول النهائي يُنشئ النموذج سجل ``uni.student``
    تلقائياً عبر ``action_enroll`` ويربطه بالطلب.

    الوراثة من ``mail.thread`` + ``mail.activity.mixin`` تتيح تتبع
    كامل للمحادثات والأنشطة على كل طلب.
    """
    _name = 'uni.admission.application'
    _description = 'Admission Application'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'application_date desc, name'

    # ------------------------------------------------------------------
    # Reference & identification
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Application Reference', copy=False, readonly=True, index=True,
        default=lambda self: _('New'), tracking=True,
        help='Unique reference generated for this application (ADM/...).')
    application_date = fields.Datetime(
        string='Application Date', default=fields.Datetime.now, tracking=True)
    submission_date = fields.Datetime(
        string='Submission Date', readonly=True, copy=False, tracking=True,
        help='Date & time when the applicant submitted the application.')

    # ------------------------------------------------------------------
    # Applicant identity
    # ------------------------------------------------------------------
    applicant_name = fields.Char(
        string='Applicant Name', required=True, tracking=True, index=True)
    applicant_email = fields.Char(
        string='Email', tracking=True, index=True)
    applicant_phone = fields.Char(string='Phone', tracking=True)
    applicant_mobile = fields.Char(string='Mobile', tracking=True)
    applicant_birth_date = fields.Date(string='Date of Birth', tracking=True)
    applicant_gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ], string='Gender', tracking=True)
    applicant_nationality_id = fields.Many2one(
        'res.country', string='Nationality', tracking=True)
    applicant_national_id = fields.Char(
        string='National ID', tracking=True, index=True)
    applicant_photo = fields.Image(
        string='Photo', max_width=1024, max_height=1024)
    applicant_user_id = fields.Many2one(
        'res.users', string='Applicant User',
        tracking=True, index=True,
        help='Portal/related user submitting the application (optional).')

    # ------------------------------------------------------------------
    # Academic target
    # ------------------------------------------------------------------
    university_id = fields.Many2one(
        'uni.university', string='University',
        required=True, ondelete='restrict', tracking=True, index=True)
    college_id = fields.Many2one(
        'uni.college', string='College',
        ondelete='restrict', tracking=True, index=True)
    department_id = fields.Many2one(
        'uni.department', string='Department',
        ondelete='restrict', tracking=True, index=True)
    program_id = fields.Many2one(
        'uni.program', string='Program',
        ondelete='restrict', tracking=True, index=True)
    level_id = fields.Many2one(
        'uni.program.level', string='Program Level',
        ondelete='restrict', tracking=True,
        help='Targeted program level (Bachelor, Master, PhD...).')
    academic_term_id = fields.Many2one(
        'uni.academic.term', string='Academic Term',
        ondelete='restrict', tracking=True, index=True,
        help='The academic term the applicant is applying for.')

    branch_id = fields.Many2one(
        'uni.branch', string='Branch',
        related='college_id.branch_id', store=True)

    # ------------------------------------------------------------------
    # Academic background (high school)
    # ------------------------------------------------------------------
    high_school_name = fields.Char(string='High School Name', tracking=True)
    high_school_graduation_year = fields.Integer(
        string='Graduation Year', tracking=True)
    high_school_grade = fields.Float(
        string='High School Grade', digits=(5, 2), tracking=True,
        help='Final high school grade (percentage or GPA per type).')
    high_school_grade_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('gpa', 'GPA'),
    ], string='Grade Type', default='percentage', tracking=True)
    transcript_file = fields.Binary(
        string='Transcript', attachment=True,
        help='Official high school transcript.')
    transcript_filename = fields.Char(string='Transcript Filename')
    recommendation_letters = fields.Binary(
        string='Recommendation Letters', attachment=True,
        help='Optional combined PDF of recommendation letters.')
    personal_statement = fields.Text(
        string='Personal Statement', translate=True)

    # ------------------------------------------------------------------
    # Assignment & workflow
    # ------------------------------------------------------------------
    assigned_to = fields.Many2one(
        'res.users', string='Assigned To',
        tracking=True, index=True,
        default=lambda self: self.env.user,
        help='Admissions officer responsible for processing this application.')
    status = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('interview_scheduled', 'Interview Scheduled'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('waitlisted', 'Waitlisted'),
        ('enrolled', 'Enrolled'),
    ], string='Status', default='draft', tracking=True, index=True,
        group_expand='_group_expand_states')

    # ------------------------------------------------------------------
    # Relations
    # ------------------------------------------------------------------
    requirements_line_ids = fields.One2many(
        'uni.admission.requirement.line', 'application_id',
        string='Requirements', copy=True)
    interview_ids = fields.One2many(
        'uni.admission.interview', 'application_id', string='Interviews')
    decision_id = fields.Many2one(
        'uni.admission.decision', string='Decision',
        ondelete='set null', copy=False, tracking=True)
    student_id = fields.Many2one(
        'uni.student', string='Enrolled Student',
        ondelete='set null', copy=False, readonly=True, tracking=True,
        help='Student record created upon enrollment.')

    # ------------------------------------------------------------------
    # Computed counts
    # ------------------------------------------------------------------
    requirements_count = fields.Integer(
        compute='_compute_requirements_count', string='Requirements')
    fulfilled_requirements_count = fields.Integer(
        compute='_compute_requirements_count', string='Fulfilled')
    mandatory_requirements_count = fields.Integer(
        compute='_compute_requirements_count', string='Mandatory')
    interview_count = fields.Integer(
        compute='_compute_interview_count', string='Interviews')
    notes = fields.Text(string='Notes')
    color = fields.Integer(string='Color Index')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_application_name', 'unique(name)',
         'Application reference must be unique!'),
    ]

    # ------------------------------------------------------------------
    # Group expansion for status field
    # ------------------------------------------------------------------
    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in self._fields['status'].selection]

    # ------------------------------------------------------------------
    # Computed
    # ------------------------------------------------------------------
    @api.depends('requirements_line_ids', 'requirements_line_ids.is_fulfilled',
                 'requirements_line_ids.is_mandatory')
    def _compute_requirements_count(self):
        for rec in self:
            lines = rec.requirements_line_ids
            rec.requirements_count = len(lines)
            rec.fulfilled_requirements_count = len(
                lines.filtered(lambda l: l.is_fulfilled))
            rec.mandatory_requirements_count = len(
                lines.filtered(lambda l: l.is_mandatory))

    @api.depends('interview_ids')
    def _compute_interview_count(self):
        for rec in self:
            rec.interview_count = len(rec.interview_ids)

    # ------------------------------------------------------------------
    # Create — auto-generate the application reference (ADM)
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.admission.application') or _('ADM-NEW')
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Onchange — keep academic hierarchy consistent
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

    @api.onchange('program_id')
    def _onchange_program_id(self):
        if self.program_id:
            self.university_id = self.program_id.university_id
            self.college_id = self.program_id.college_id
            self.department_id = self.program_id.department_id
            self.level_id = self.program_id.level_id
            if self.program_id.branch_id:
                self.branch_id = self.program_id.branch_id

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_submit(self):
        """Submit the application for review — stamps submission_date."""
        for rec in self:
            if rec.status != 'draft':
                raise ValidationError(_(
                    "Only draft applications can be submitted (current: %(s)s).")
                    % {'s': rec.status})
            if not rec.applicant_email and not rec.applicant_mobile:
                raise ValidationError(_(
                    "Application %(n)s must have at least an email or a mobile "
                    "before submission.") % {'n': rec.display_name})
            rec.write({
                'status': 'submitted',
                'submission_date': fields.Datetime.now(),
            })
            rec.message_post(body=_(
                "Application submitted for review by %(who)s.") % {
                'who': rec.applicant_name or _('Applicant')})

    def action_review(self):
        """Move the application into the Under Review stage."""
        for rec in self:
            if rec.status not in ('submitted', 'interview_scheduled'):
                raise ValidationError(_(
                    "Application must be 'Submitted' to start review "
                    "(current: %(s)s).") % {'s': rec.status})
            rec.status = 'under_review'
            rec.message_post(body=_("Application is now under review."))

    def action_schedule_interview(self):
        """Mark the application as having scheduled interviews.

        Doesn't create interviews directly — the user creates them via
        the Interview smart button. This action only advances the status
        if at least one interview exists.
        """
        for rec in self:
            if rec.status not in ('under_review', 'submitted'):
                raise ValidationError(_(
                    "Cannot schedule an interview from status '%(s)s' "
                    "(application %(n)s).") % {'s': rec.status,
                                               'n': rec.display_name})
            if not rec.interview_ids:
                raise ValidationError(_(
                    "Please create at least one interview record before "
                    "scheduling (application %(n)s).") % {'n': rec.display_name})
            rec.status = 'interview_scheduled'
            rec.message_post(body=_(
                "Interview scheduled for application %(n)s.") % {
                'n': rec.display_name})

    def action_accept(self):
        """Mark the application as accepted."""
        for rec in self:
            if rec.status in ('rejected', 'enrolled'):
                raise ValidationError(_(
                    "Cannot accept an application already '%(s)s' "
                    "(%(n)s).") % {'s': rec.status, 'n': rec.display_name})
            rec.status = 'accepted'
            rec.message_post(body=_(
                "Application accepted."))

    def action_reject(self):
        """Mark the application as rejected."""
        for rec in self:
            if rec.status in ('accepted', 'enrolled'):
                raise ValidationError(_(
                    "Cannot reject an application already '%(s)s' "
                    "(%(n)s).") % {'s': rec.status, 'n': rec.display_name})
            rec.status = 'rejected'
            rec.message_post(body=_("Application rejected."))

    def action_waitlist(self):
        """Move the application to the waitlist."""
        for rec in self:
            if rec.status in ('enrolled', 'rejected'):
                raise ValidationError(_(
                    "Cannot waitlist an application already '%(s)s' "
                    "(%(n)s).") % {'s': rec.status, 'n': rec.display_name})
            rec.status = 'waitlisted'
            rec.message_post(body=_("Application placed on the waitlist."))

    def action_enroll(self):
        """Create a ``uni.student`` record from the application and link it.

        Only accepted (or waitlisted-then-accepted) applications may enroll.
        The new student inherits the applicant's identity, program/college/
        department/university affiliation and the chosen academic term.
        """
        Student = self.env['uni.student']
        Person = self.env['uni.person']
        for rec in self:
            if rec.status != 'accepted':
                raise ValidationError(_(
                    "Only accepted applications can be enrolled "
                    "(current status: %(s)s for %(n)s).") % {
                    's': rec.status, 'n': rec.display_name})
            if rec.student_id:
                raise ValidationError(_(
                    "Application %(n)s is already linked to student %(s).") % {
                    'n': rec.display_name, 's': rec.student_id.display_name})

            # 1) Build the underlying uni.person (which delegates to res.partner)
            person_vals = {
                'name': rec.applicant_name,
                'university_id': rec.university_id.id,
                'person_type': 'student',
                'gender': rec.applicant_gender or False,
                'birth_date': rec.applicant_birth_date or False,
                'nationality_id': rec.applicant_nationality_id.id
                if rec.applicant_nationality_id else False,
                'national_id': rec.applicant_national_id or False,
                'photo': rec.applicant_photo or False,
                'email': rec.applicant_email or False,
                'phone': rec.applicant_phone or False,
                'mobile': rec.applicant_mobile or False,
            }
            person = Person.create(person_vals)

            # 2) Build the student record (auto-generates student_code)
            student_vals = {
                'person_id': person.id,
                'university_id': rec.university_id.id,
                'program_id': rec.program_id.id if rec.program_id else False,
                'college_id': rec.college_id.id if rec.college_id else False,
                'department_id': rec.department_id.id if rec.department_id else False,
                'branch_id': rec.branch_id.id if rec.branch_id else False,
                'admission_date': fields.Date.context_today(rec),
                'student_type': 'regular',
                'state': 'active',
            }
            if rec.level_id:
                # uni.student exposes current_level as Integer (1..N)
                # We try to map the level record's sequence; fallback to 1.
                student_vals['current_level'] = max(
                    int(rec.level_id.sequence or 1), 1)
            student = Student.create(student_vals)

            # 3) Link + finalise the workflow
            rec.write({
                'student_id': student.id,
                'status': 'enrolled',
            })
            rec.message_post(body=_(
                "Student <a href='#' data-oe-model='uni.student' "
                "data-oe-id='%(id)d'>%(name)s</a> created from this application.") % {
                'id': student.id, 'name': student.display_name})

    # ------------------------------------------------------------------
    # Smart-button actions
    # ------------------------------------------------------------------
    def action_view_interviews(self):
        self.ensure_one()
        return {
            'name': _('Interviews'),
            'type': 'ir.actions.act_window',
            'res_model': 'uni.admission.interview',
            'view_mode': 'list,form',
            'domain': [('application_id', '=', self.id)],
            'context': {
                'default_application_id': self.id,
                'default_university_id': self.university_id.id,
            },
        }

    def action_view_requirements(self):
        self.ensure_one()
        return {
            'name': _('Requirements'),
            'type': 'ir.actions.act_window',
            'res_model': 'uni.admission.requirement.line',
            'view_mode': 'list,form',
            'domain': [('application_id', '=', self.id)],
            'context': {'default_application_id': self.id},
        }

    def action_view_student(self):
        """Jump to the linked student record."""
        self.ensure_one()
        if not self.student_id:
            return False
        return {
            'name': _('Enrolled Student'),
            'type': 'ir.actions.act_window',
            'res_model': 'uni.student',
            'res_id': self.student_id.id,
            'view_mode': 'form',
        }

    def action_apply_default_requirements(self):
        """Create requirement lines for all currently-active requirements."""
        Requirement = self.env['uni.admission.requirement']
        for rec in self:
            existing = rec.requirements_line_ids.mapped('requirement_id')
            to_add = Requirement.search([
                ('active', '=', True),
                ('id', 'not in', existing.ids),
            ])
            for req in to_add:
                rec.requirements_line_ids.create({
                    'application_id': rec.id,
                    'requirement_id': req.id,
                })

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('applicant_email')
    def _check_email_format(self):
        """Validate email format when provided."""
        for rec in self:
            if rec.applicant_email and not re.match(EMAIL_REGEX,
                                                    rec.applicant_email):
                raise ValidationError(_(
                    "The email address '%(e)s' on application %(n)s is not "
                    "valid.") % {'e': rec.applicant_email,
                                 'n': rec.display_name})

    @api.constrains('high_school_graduation_year')
    def _check_graduation_year(self):
        """Sanity check: graduation year cannot be in the future."""
        current_year = fields.Date.today().year
        for rec in self:
            if rec.high_school_graduation_year and \
                    rec.high_school_graduation_year > current_year + 1:
                raise ValidationError(_(
                    "High school graduation year %(y)d cannot be more than "
                    "one year in the future (application %(n)s).") % {
                    'y': rec.high_school_graduation_year,
                    'n': rec.display_name})

    @api.constrains('high_school_grade', 'high_school_grade_type')
    def _check_high_school_grade(self):
        """Validate the high school grade range per type."""
        for rec in self:
            if not rec.high_school_grade:
                continue
            if rec.high_school_grade_type == 'percentage':
                if not (0.0 <= rec.high_school_grade <= 100.0):
                    raise ValidationError(_(
                        "High school percentage must be between 0 and 100 "
                        "(got %(g)s for %(n)s).") % {
                        'g': rec.high_school_grade, 'n': rec.display_name})
            else:  # gpa
                if not (0.0 <= rec.high_school_grade <= 10.0):
                    raise ValidationError(_(
                        "High school GPA must be between 0 and 10 "
                        "(got %(g)s for %(n)s).") % {
                        'g': rec.high_school_grade, 'n': rec.display_name})
