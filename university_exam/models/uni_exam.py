# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniExam(models.Model):
    """الامتحان — يمثّل امتحاناً لمقرر دراسي في فصل دراسي محدد.

    يجمع هذا النموذج كل المعلومات اللازمة لإجراء الامتحان:
        * المقرر، الفصل الدراسي، ونوع الامتحان
        * الجامعة والكلية والقسم (مشتقة من المقرر)
        * البرنامج وعضو هيئة التدريس المسؤول
        * تاريخ ووقت ومدة الامتحان
        * القاعات المخصصة والمراقبون المعيّنون
        * عدد الطلاب والدرجة العظمى ودرجة النجاح
        * المخالفات المرتبطة بالامتحان

    سير العمل:
        ``draft`` → ``scheduled`` → ``ongoing`` → ``completed``
                  ↘ ``cancelled`` (من أي حالة سابقة)
    """
    _name = 'uni.exam'
    _description = 'Exam'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'exam_date desc, name'

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Name', required=True, copy=False, default=_('New'),
        tracking=True, index=True,
        help='Auto-generated reference for the exam (EXM/...).')
    code = fields.Char(
        string='Code', copy=False, index=True, tracking=True,
        help='Optional human-readable code for the exam.')
    active = fields.Boolean(string='Active', default=True)

    # ------------------------------------------------------------------
    # Academic context
    # ------------------------------------------------------------------
    course_id = fields.Many2one(
        'uni.course', string='Course', required=True, ondelete='restrict',
        tracking=True, index=True)
    academic_term_id = fields.Many2one(
        'uni.academic.term', string='Academic Term', required=True,
        ondelete='restrict', tracking=True, index=True)
    exam_type_id = fields.Many2one(
        'uni.exam.type', string='Exam Type', required=True,
        ondelete='restrict', tracking=True, index=True)
    program_id = fields.Many2one(
        'uni.program', string='Program', ondelete='restrict',
        tracking=True, index=True)
    faculty_name = fields.Char(
        string='Supervising Faculty', tracking=True, index=True,
        help='Name of the faculty member responsible for supervising this '
             'exam. Stored as plain text to avoid a hard dependency on '
             'university_faculty.')

    # ------------------------------------------------------------------
    # Hierarchy (derived from course / term)
    # ------------------------------------------------------------------
    university_id = fields.Many2one(
        'uni.university', string='University', store=True,
        related='course_id.university_id', tracking=True, index=True)
    college_id = fields.Many2one(
        'uni.college', string='College', store=True,
        related='course_id.college_id', tracking=True, index=True)
    department_id = fields.Many2one(
        'uni.department', string='Department', store=True,
        related='course_id.department_id', tracking=True, index=True)
    academic_year_id = fields.Many2one(
        'uni.academic.year', string='Academic Year', store=True,
        related='academic_term_id.academic_year_id', index=True)

    # ------------------------------------------------------------------
    # Schedule
    # ------------------------------------------------------------------
    exam_date = fields.Datetime(
        string='Exam Date', tracking=True, index=True,
        help='Date and time at which the exam starts.')
    duration = fields.Float(
        string='Duration', default=2.0, widget='float_time', tracking=True,
        help='Planned duration of the exam in hours (float, e.g. 2.5 = 2h30).')
    start_time = fields.Float(
        string='Start Time', widget='float_time', tracking=True,
        help='Start time of the exam in decimal hours (e.g. 9.5 = 09:30).')
    end_time = fields.Float(
        string='End Time', widget='float_time', tracking=True,
        help='End time of the exam in decimal hours (e.g. 11.5 = 11:30).')

    # ------------------------------------------------------------------
    # Grading defaults
    # ------------------------------------------------------------------
    max_score = fields.Float(
        string='Max Score', default=100.0, tracking=True,
        help='Maximum score achievable on this exam.')
    passing_score = fields.Float(
        string='Passing Score', default=50.0, tracking=True,
        help='Minimum score required to pass this exam.')
    weight_percentage = fields.Float(
        string='Weight (%)', default=30.0, tracking=True,
        help='Weight of this exam in the final course grade (percentage).')

    # ------------------------------------------------------------------
    # Logistics
    # ------------------------------------------------------------------
    room_ids = fields.Many2many(
        'uni.exam.room', string='Exam Rooms',
        help='Rooms assigned to host this exam.')
    invigilator_ids = fields.Many2many(
        'uni.exam.invigilator', string='Invigilators',
        help='Invigilators assigned to supervise this exam.')
    total_students = fields.Integer(
        string='Total Students', default=0, tracking=True,
        help='Total number of students expected to sit this exam.')
    total_capacity = fields.Integer(
        compute='_compute_total_capacity', string='Total Room Capacity',
        help='Sum of capacities of all assigned rooms.')

    # ------------------------------------------------------------------
    # State & relations
    # ------------------------------------------------------------------
    state = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='State', default='draft', tracking=True, index=True,
        group_expand='_group_expand_states')

    schedule_ids = fields.Many2many(
        'uni.exam.schedule', string='Schedules',
        relation='uni_exam_schedule_rel',
        column1='exam_id', column2='schedule_id',
        help='Exam schedules in which this exam appears.')

    violation_ids = fields.One2many(
        'uni.exam.violation', 'exam_id', string='Violations')
    violation_count = fields.Integer(
        compute='_compute_violation_count', string='Violations')

    notes = fields.Text(string='Notes', translate=True)

    _sql_constraints = [
        ('unique_term_code', 'unique(academic_term_id, code)',
         'Exam code must be unique per academic term!'),
        ('check_max_score', 'check(max_score >= 0)',
         'Max score cannot be negative!'),
        ('check_passing_score', 'check(passing_score >= 0)',
         'Passing score cannot be negative!'),
        ('check_total_students', 'check(total_students >= 0)',
         'Total students cannot be negative!'),
        ('check_duration', 'check(duration >= 0)',
         'Duration cannot be negative!'),
        ('check_time_range', 'check(start_time >= 0 AND end_time <= 24)',
         'Time values must be between 0 and 24!'),
    ]

    # ------------------------------------------------------------------
    # Group expansion helper
    # ------------------------------------------------------------------
    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in self._fields['state'].selection]

    # ------------------------------------------------------------------
    # Computed
    # ------------------------------------------------------------------
    @api.depends('room_ids', 'room_ids.capacity')
    def _compute_total_capacity(self):
        for rec in self:
            rec.total_capacity = sum(rec.room_ids.mapped('capacity'))

    @api.depends('violation_ids')
    def _compute_violation_count(self):
        for rec in self:
            rec.violation_count = len(rec.violation_ids)

    # ------------------------------------------------------------------
    # Onchange — prefill from exam type & course
    # ------------------------------------------------------------------
    @api.onchange('exam_type_id')
    def _onchange_exam_type_id(self):
        if self.exam_type_id:
            et = self.exam_type_id
            if not self.duration:
                self.duration = et.default_duration
            if not self.max_score or self.max_score == 100.0:
                self.max_score = et.default_max_score
            if not self.weight_percentage or self.weight_percentage == 30.0:
                self.weight_percentage = et.weight_percentage
            if not self.passing_score or self.passing_score == 50.0:
                self.passing_score = (et.default_max_score * et.passing_percentage / 100.0) \
                    if et.default_max_score else 50.0

    @api.onchange('course_id')
    def _onchange_course_id(self):
        if self.course_id:
            if not self.program_id and self.course_id.college_id:
                # Suggest first program of the course's college if any
                program = self.env['uni.program'].search(
                    [('college_id', '=', self.course_id.college_id.id)],
                    limit=1)
                if program:
                    self.program_id = program

    @api.onchange('start_time', 'end_time', 'duration')
    def _onchange_times(self):
        """Auto-fill end_time = start_time + duration when only those are set."""
        if self.start_time and self.duration and not self.end_time:
            self.end_time = self.start_time + self.duration
        if self.start_time and self.end_time and not self.duration:
            self.duration = self.end_time - self.start_time

    # ------------------------------------------------------------------
    # Create — auto-generate name from ir.sequence
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('uni.exam') or _('EXM-NEW')
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_schedule(self):
        """Schedule the exam — requires a date and at least one room."""
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError(_(
                    "Only draft exams can be scheduled (current state: %(state)s).")
                    % {'state': rec.state})
            if not rec.exam_date:
                raise ValidationError(_(
                    "Cannot schedule exam '%s' without an exam date.")
                    % rec.display_name)
            rec.state = 'scheduled'
            rec.message_post(body=_('Exam scheduled for %s.') % rec.exam_date)

    def action_start(self):
        """Mark the exam as ongoing."""
        for rec in self:
            if rec.state != 'scheduled':
                raise ValidationError(_(
                    "Only scheduled exams can be started (current state: %(state)s).")
                    % {'state': rec.state})
            rec.state = 'ongoing'
            rec.message_post(body=_('Exam started.'))

    def action_complete(self):
        """Mark the exam as completed."""
        for rec in self:
            if rec.state != 'ongoing':
                raise ValidationError(_(
                    "Only ongoing exams can be completed (current state: %(state)s).")
                    % {'state': rec.state})
            rec.state = 'completed'
            rec.message_post(body=_('Exam completed.'))

    def action_cancel(self):
        """Cancel the exam."""
        for rec in self:
            if rec.state in ('completed', 'cancelled'):
                raise ValidationError(_(
                    "Cannot cancel an exam in state '%(state)s'.")
                    % {'state': rec.state})
            rec.state = 'cancelled'
            rec.message_post(body=_('Exam cancelled.'))

    def action_draft(self):
        """Reset the exam to draft state."""
        for rec in self:
            if rec.state == 'ongoing':
                raise ValidationError(_(
                    "Cannot reset an ongoing exam to draft. Cancel it first."))
            rec.state = 'draft'
            rec.message_post(body=_('Exam reset to draft.'))

    # ------------------------------------------------------------------
    # Smart-button action
    # ------------------------------------------------------------------
    def action_view_violations(self):
        self.ensure_one()
        return {
            'name': _('Violations'),
            'type': 'ir.actions.act_window',
            'res_model': 'uni.exam.violation',
            'view_mode': 'list,form',
            'domain': [('exam_id', '=', self.id)],
            'context': {'default_exam_id': self.id},
        }

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('start_time', 'end_time')
    def _check_times(self):
        for rec in self:
            if rec.start_time and rec.end_time and rec.end_time <= rec.start_time:
                raise ValidationError(_(
                    "End time must be greater than start time for exam '%s'.")
                    % rec.display_name)
            if rec.start_time and not (0 <= rec.start_time <= 24):
                raise ValidationError(_(
                    "Start time must be between 0 and 24 for exam '%s'.")
                    % rec.display_name)
            if rec.end_time and not (0 <= rec.end_time <= 24):
                raise ValidationError(_(
                    "End time must be between 0 and 24 for exam '%s'.")
                    % rec.display_name)

    @api.constrains('max_score', 'passing_score')
    def _check_scores(self):
        for rec in self:
            if rec.max_score > 0 and rec.passing_score > rec.max_score:
                raise ValidationError(_(
                    "Passing score cannot exceed max score for exam '%s'.")
                    % rec.display_name)

    @api.constrains('duration')
    def _check_duration(self):
        for rec in self:
            if rec.duration < 0:
                raise ValidationError(_(
                    "Duration cannot be negative for exam '%s'.")
                    % rec.display_name)

    @api.constrains('room_ids', 'university_id')
    def _check_rooms_university(self):
        """All assigned rooms must belong to the same university as the exam."""
        for rec in self:
            if rec.university_id and rec.room_ids:
                wrong = rec.room_ids.filtered(
                    lambda r: r.university_id.id != rec.university_id.id)
                if wrong:
                    raise ValidationError(_(
                        "All exam rooms must belong to the same university as "
                        "the exam (%s). Mismatch: %s")
                        % (rec.display_name,
                           ', '.join(wrong.mapped('display_name'))))
