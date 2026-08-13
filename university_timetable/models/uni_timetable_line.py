# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniTimetableLine(models.Model):
    """خط الجدول — يربط المقرر بعضو هيئة التدريس والقاعة والفترة الزمنية.

    يمنع قيد ``@api.constrains`` وجود تعارض في:
      * نفس عضو هيئة التدريس في نفس الفترة (لا يمكن لعضو واحد أن يدرّس
        مقررين في نفس الوقت).
      * نفس القاعة في نفس الفترة (لا يمكن لقاعة أن تستضيف حصتين معاً).
      * نفس المقرر/الشعبة في نفس الفترة (تفادي التكرار).
    """
    _name = 'uni.timetable.line'
    _description = 'Timetable Line'
    _inherit = ['mail.thread']
    _order = 'day_of_week, start_time, course_id'

    name = fields.Char(
        string='Reference', compute='_compute_name', store=True, index=True)
    timetable_id = fields.Many2one(
        'uni.timetable', string='Timetable',
        required=True, ondelete='cascade', tracking=True, index=True)
    academic_term_id = fields.Many2one(
        'uni.academic.term', string='Academic Term',
        related='timetable_id.academic_term_id', store=True, readonly=True)
    university_id = fields.Many2one(
        'uni.university', string='University',
        related='timetable_id.university_id', store=True, readonly=True)
    college_id = fields.Many2one(
        'uni.college', string='College',
        related='timetable_id.college_id', store=True, readonly=True)
    department_id = fields.Many2one(
        'uni.department', string='Department',
        related='timetable_id.department_id', store=True, readonly=True)
    program_id = fields.Many2one(
        'uni.program', string='Program',
        ondelete='restrict', tracking=True, index=True)

    course_id = fields.Many2one(
        'uni.course', string='Course',
        required=True, ondelete='restrict', tracking=True, index=True)
    faculty_id = fields.Many2one(
        'uni.faculty', string='Faculty',
        required=True, ondelete='restrict', tracking=True, index=True)
    classroom_id = fields.Many2one(
        'uni.classroom', string='Classroom',
        ondelete='restrict', tracking=True, index=True,
        domain="[('university_id', '=', university_id)]")
    slot_id = fields.Many2one(
        'uni.timetable.slot', string='Time Slot',
        required=True, ondelete='restrict', tracking=True, index=True)

    day_of_week = fields.Selection(
        string='Day', related='slot_id.day_of_week', store=True, readonly=True)
    start_time = fields.Float(
        string='Start Time', related='slot_id.start_time', store=True, readonly=True)
    end_time = fields.Float(
        string='End Time', related='slot_id.end_time', store=True, readonly=True)
    is_break = fields.Boolean(
        string='Break Slot', related='slot_id.break_slot', store=False, readonly=True)

    section = fields.Char(
        string='Section', tracking=True,
        help='Section identifier (e.g. A, B, C) within the course offering.')
    group = fields.Char(
        string='Group', tracking=True,
        help='Sub-group identifier inside the section (e.g. Lab Group 1).')
    is_makeup = fields.Boolean(
        string='Make-up Session', default=False, tracking=True,
        help='Mark this line as a make-up session for a missed class.')
    notes = fields.Text(string='Notes')

    # ------------------------------------------------------------------
    # Computed
    # ------------------------------------------------------------------
    @api.depends('course_id', 'faculty_id', 'slot_id', 'section', 'group')
    def _compute_name(self):
        for rec in self:
            parts = []
            if rec.course_id:
                parts.append(rec.course_id.display_name)
            if rec.faculty_id:
                parts.append(rec.faculty_id.display_name)
            if rec.section:
                parts.append(_('Sec %s') % rec.section)
            if rec.group:
                parts.append(_('Grp %s') % rec.group)
            if rec.slot_id:
                parts.append(rec.slot_id.display_name or rec.slot_id.name)
            rec.name = ' — '.join(parts) if parts else _('New Line')

    # ------------------------------------------------------------------
    # Onchange helpers
    # ------------------------------------------------------------------
    @api.onchange('course_id')
    def _onchange_course_id(self):
        """عند اختيار المقرر، يقترح البرنامج المرتبط به إن وُجد."""
        if self.course_id and not self.program_id:
            # Pick the first program-course link for this course if available
            link = self.env['uni.program.course'].search(
                [('course_id', '=', self.course_id.id)], limit=1)
            if link:
                self.program_id = link.program_id.id

    # ------------------------------------------------------------------
    # Constraints — conflict detection
    # ------------------------------------------------------------------
    @api.constrains('faculty_id', 'slot_id', 'academic_term_id', 'is_makeup')
    def _check_faculty_conflict(self):
        """نفس عضو هيئة التدريس لا يمكن أن يدرّس حصتين في نفس الفترة الزمنية
        خلال نفس الفصل الدراسي (ما لم تكن إحداهما حصة تعويضية معلَّمة)."""
        for rec in self:
            if not rec.faculty_id or not rec.slot_id or not rec.academic_term_id:
                continue
            domain = [
                ('id', '!=', rec.id),
                ('faculty_id', '=', rec.faculty_id.id),
                ('slot_id', '=', rec.slot_id.id),
                ('academic_term_id', '=', rec.academic_term_id.id),
                ('is_makeup', '=', False),
            ]
            if rec.is_makeup:
                # A make-up session is allowed to coincide with a regular one
                # only if explicitly flagged; still prevent two make-ups
                # from coinciding:
                domain = [
                    ('id', '!=', rec.id),
                    ('faculty_id', '=', rec.faculty_id.id),
                    ('slot_id', '=', rec.slot_id.id),
                    ('academic_term_id', '=', rec.academic_term_id.id),
                    ('is_makeup', '=', True),
                ]
            conflict = self.search(domain, limit=1)
            if conflict:
                raise ValidationError(_(
                    'Faculty conflict: %s is already assigned to "%s" '
                    'on %s at the same slot (%s).') % (
                        rec.faculty_id.display_name,
                        conflict.display_name,
                        dict(rec._fields['day_of_week'].selection).get(
                            rec.day_of_week, rec.day_of_week) if rec.day_of_week else '',
                        rec.slot_id.display_name or rec.slot_id.name,
                    ))

    @api.constrains('classroom_id', 'slot_id', 'academic_term_id')
    def _check_classroom_conflict(self):
        """نفس القاعة لا يمكن أن تستضيف حصتين في نفس الفترة الزمنية
        خلال نفس الفصل الدراسي."""
        for rec in self:
            if not rec.classroom_id or not rec.slot_id or not rec.academic_term_id:
                continue
            domain = [
                ('id', '!=', rec.id),
                ('classroom_id', '=', rec.classroom_id.id),
                ('slot_id', '=', rec.slot_id.id),
                ('academic_term_id', '=', rec.academic_term_id.id),
            ]
            conflict = self.search(domain, limit=1)
            if conflict:
                raise ValidationError(_(
                    'Classroom conflict: %s is already booked for "%s" '
                    'on %s at the same slot (%s).') % (
                        rec.classroom_id.display_name,
                        conflict.display_name,
                        dict(rec._fields['day_of_week'].selection).get(
                            rec.day_of_week, rec.day_of_week) if rec.day_of_week else '',
                        rec.slot_id.display_name or rec.slot_id.name,
                    ))

    @api.constrains('course_id', 'section', 'group', 'slot_id', 'academic_term_id')
    def _check_course_section_conflict(self):
        """نفس المقرر/الشعبة/المجموعة لا يمكن أن يظهر مرتين في نفس الفترة."""
        for rec in self:
            if not rec.course_id or not rec.slot_id or not rec.academic_term_id:
                continue
            domain = [
                ('id', '!=', rec.id),
                ('course_id', '=', rec.course_id.id),
                ('slot_id', '=', rec.slot_id.id),
                ('academic_term_id', '=', rec.academic_term_id.id),
            ]
            if rec.section:
                domain.append(('section', '=', rec.section))
            else:
                domain.append(('section', '=', False))
            if rec.group:
                domain.append(('group', '=', rec.group))
            else:
                domain.append(('group', '=', False))
            conflict = self.search(domain, limit=1)
            if conflict:
                raise ValidationError(_(
                    'Course conflict: %s (section %s / group %s) is already '
                    'scheduled on %s at the same slot (%s).') % (
                        rec.course_id.display_name,
                        rec.section or '—',
                        rec.group or '—',
                        dict(rec._fields['day_of_week'].selection).get(
                            rec.day_of_week, rec.day_of_week) if rec.day_of_week else '',
                        rec.slot_id.display_name or rec.slot_id.name,
                    ))

    @api.constrains('classroom_id', 'university_id')
    def _check_classroom_university(self):
        """القاعة يجب أن تنتمي لنفس الجامعة التي ينتمي إليها الجدول."""
        for rec in self:
            if rec.classroom_id and rec.university_id and \
                    rec.classroom_id.university_id.id != rec.university_id.id:
                raise ValidationError(_(
                    'Classroom %s does not belong to the same university (%s) '
                    'as the timetable.') % (
                        rec.classroom_id.display_name,
                        rec.university_id.display_name))
