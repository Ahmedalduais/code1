# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniAttendanceLine(models.Model):
    """تفاصيل الحضور — يمثل سجل حضور طالب واحد في جلسة حضور واحدة.

    كل خط يحمل حالة الطالب (حاضر/غائب/متأخر/...) مع تفاصيل وقت الحضور
    والانصراف وعدد دقائق التأخير. كما يحسب نسبة حضور الطالب عبر جميع
    سجلاته في نفس المقرر والفصل.
    """
    _name = 'uni.attendance.line'
    _description = 'Attendance Line'
    _order = 'attendance_id, student_id, id'

    attendance_id = fields.Many2one(
        'uni.attendance', string='Attendance Session',
        required=True, ondelete='cascade', index=True)
    student_id = fields.Many2one(
        'uni.student', string='Student',
        required=True, ondelete='restrict', tracking=True, index=True)
    course_id = fields.Many2one(
        'uni.course', string='Course',
        related='attendance_id.course_id', store=True, index=True)
    academic_term_id = fields.Many2one(
        'uni.academic.term', string='Academic Term',
        related='attendance_id.academic_term_id', store=True, index=True)
    university_id = fields.Many2one(
        'uni.university', string='University',
        related='attendance_id.university_id', store=True, index=True)

    status = fields.Selection([
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('excused', 'Excused'),
        ('medical_leave', 'Medical Leave'),
    ], string='Status', default='present', required=True, tracking=True, index=True)
    arrival_time = fields.Float(
        string='Arrival Time', default=0.0,
        help='Arrival time as decimal hours (e.g. 9.5 = 09:30).')
    departure_time = fields.Float(
        string='Departure Time', default=0.0,
        help='Departure time as decimal hours (e.g. 11.25 = 11:15).')
    minutes_late = fields.Integer(
        string='Minutes Late', default=0,
        help='Number of minutes the student was late to the session.')
    notes = fields.Text(string='Notes', tracking=True)

    # ------------------------------------------------------------------
    # Computed: attendance percentage for this student in this course/term
    # ------------------------------------------------------------------
    attendance_percentage = fields.Float(
        string='Attendance %', digits=(5, 2), default=0.0,
        compute='_compute_attendance_percentage', store=True,
        help='Percentage of sessions attended by this student in this course/term.')

    @api.depends('student_id', 'course_id', 'academic_term_id', 'status',
                 'attendance_id.state')
    def _compute_attendance_percentage(self):
        """Compute attendance percentage for each student in their course/term.

        Counts the number of validated sessions where the student's status
        is present/late/excused/medical_leave vs. total validated sessions
        for the same (student, course, term) tuple.
        """
        for rec in self:
            if not rec.student_id or not rec.course_id or not rec.academic_term_id:
                rec.attendance_percentage = 0.0
                continue
            all_lines = self.search([
                ('student_id', '=', rec.student_id.id),
                ('course_id', '=', rec.course_id.id),
                ('academic_term_id', '=', rec.academic_term_id.id),
                ('attendance_id.state', '=', 'validated'),
            ])
            total = len(all_lines)
            if not total:
                rec.attendance_percentage = 0.0
                continue
            attended = len(all_lines.filtered(
                lambda l: l.status in ('present', 'late', 'excused', 'medical_leave')))
            rec.attendance_percentage = (attended / total) * 100.0

    # ------------------------------------------------------------------
    # Onchange helpers
    # ------------------------------------------------------------------
    @api.onchange('attendance_id')
    def _onchange_attendance_id(self):
        """Pre-fill the student from the parent attendance record if available."""
        if self.attendance_id and self.attendance_id.student_id and not self.student_id:
            self.student_id = self.attendance_id.student_id

    @api.onchange('arrival_time', 'departure_time')
    def _onchange_times(self):
        """Auto-compute minutes_late if arrival is after the standard start (assumed 0)."""
        if self.arrival_time > 0:
            self.minutes_late = int(self.arrival_time * 60)

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('arrival_time', 'departure_time')
    def _check_times(self):
        for rec in self:
            if rec.arrival_time < 0 or rec.arrival_time > 24:
                raise ValidationError(_(
                    "Arrival time must be between 0 and 24 hours."))
            if rec.departure_time < 0 or rec.departure_time > 24:
                raise ValidationError(_(
                    "Departure time must be between 0 and 24 hours."))
            if rec.arrival_time and rec.departure_time and \
                    rec.departure_time < rec.arrival_time:
                raise ValidationError(_(
                    "Departure time cannot be earlier than arrival time."))

    @api.constrains('minutes_late')
    def _check_minutes_late(self):
        for rec in self:
            if rec.minutes_late < 0:
                raise ValidationError(_(
                    "Minutes late cannot be negative."))

    @api.constrains('attendance_id', 'student_id')
    def _check_unique_student_in_session(self):
        for rec in self:
            duplicates = self.search([
                ('attendance_id', '=', rec.attendance_id.id),
                ('student_id', '=', rec.student_id.id),
                ('id', '!=', rec.id),
            ])
            if duplicates:
                raise ValidationError(_(
                    "Student %s already has a line in this attendance session.")
                    % rec.student_id.display_name)
