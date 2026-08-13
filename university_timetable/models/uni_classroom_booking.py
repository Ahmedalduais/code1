# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniClassroomBooking(models.Model):
    """حجز القاعات — يمثل حجزاً لقاعة في تاريخ محدد خلال فترة زمنية معينة.

    يُمنع التعارض الزمني بين الحجوزات لنفس القاعة عبر قيد SQL
    ومنطق ``@api.constrains`` يتحقق من عدم وجود تداخل زمني.
    يمكن ربط الحجز بخط جدول دراسي (``uni.timetable.line``).
    """
    _name = 'uni.classroom.booking'
    _description = 'Classroom Booking'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'booking_date, start_time, classroom_id'

    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True, index=True,
        default=lambda self: _('New'),
        help='Auto-generated booking reference.')
    classroom_id = fields.Many2one(
        'uni.classroom', string='Classroom',
        required=True, ondelete='restrict', tracking=True, index=True)
    university_id = fields.Many2one(
        'uni.university', string='University',
        related='classroom_id.university_id', store=True, readonly=True)
    booking_date = fields.Date(
        string='Booking Date', required=True, tracking=True, index=True,
        default=fields.Date.context_today)
    start_time = fields.Float(
        string='Start Time', required=True, tracking=True,
        help='Start time of the booking (24h, e.g. 8.5 = 08:30).')
    end_time = fields.Float(
        string='End Time', required=True, tracking=True,
        help='End time of the booking (24h, e.g. 10.25 = 10:15).')
    booked_by = fields.Many2one(
        'res.users', string='Booked By',
        default=lambda self: self.env.uid, required=True, tracking=True, index=True)
    timetable_line_id = fields.Many2one(
        'uni.timetable.line', string='Timetable Line',
        ondelete='set null', index=True,
        help='Optional link to the timetable line that triggered this booking.')
    purpose = fields.Char(string='Purpose', tracking=True)
    notes = fields.Text(string='Notes')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ], string='Status', default='draft', tracking=True, index=True,
        group_expand='_group_expand_states')

    # ------------------------------------------------------------------
    # Computed Datetime helpers — used by the calendar view to position
    # events at the right time-of-day on the right date.
    # ------------------------------------------------------------------
    calendar_start = fields.Datetime(
        compute='_compute_calendar_datetimes', store=False,
        string='Calendar Start')
    calendar_stop = fields.Datetime(
        compute='_compute_calendar_datetimes', store=False,
        string='Calendar Stop')

    _sql_constraints = [
        # SQL constraint enforces exact uniqueness on the four-tuple.
        # The Python @api.constrains below additionally detects time-overlap
        # (different start/end values that still overlap).
        ('unique_classroom_booking_slot',
         'unique(classroom_id, booking_date, start_time, end_time)',
         'A booking already exists for this classroom at the same date and time!'),
        ('check_booking_times',
         'check(end_time > start_time)',
         'End time must be after start time!'),
        ('check_booking_time_range',
         'check(start_time >= 0 AND end_time <= 24)',
         'Time must be between 00:00 and 24:00!'),
    ]

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in states]

    @api.depends('booking_date', 'start_time', 'end_time')
    def _compute_calendar_datetimes(self):
        """Combine booking_date + float_time into Datetime values for the
        calendar view so events are positioned at the right time of day."""
        for rec in self:
            if rec.booking_date:
                rec.calendar_start = fields.Datetime.to_datetime(
                    '%s %s' % (rec.booking_date,
                               self._format_float_time(rec.start_time)))
                rec.calendar_stop = fields.Datetime.to_datetime(
                    '%s %s' % (rec.booking_date,
                               self._format_float_time(rec.end_time)))
            else:
                rec.calendar_start = False
                rec.calendar_stop = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.classroom.booking') or _('BOOK-NEW')
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_confirm(self):
        """تأكيد الحجز (يصبح ملزماً)."""
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError(_(
                    'Only draft bookings can be confirmed (booking %s).')
                    % rec.display_name)
            rec.state = 'confirmed'

    def action_cancel(self):
        """إلغاء الحجز."""
        for rec in self:
            if rec.state == 'completed':
                raise ValidationError(_(
                    'Cannot cancel a completed booking (%s).') % rec.display_name)
            rec.state = 'cancelled'

    def action_complete(self):
        """إتمام الحجز (بعد انتهاء الفعالية)."""
        for rec in self:
            if rec.state != 'confirmed':
                raise ValidationError(_(
                    'Only confirmed bookings can be completed (booking %s).')
                    % rec.display_name)
            rec.state = 'completed'

    def action_draft(self):
        """إعادة الحجز إلى حالة المسودة."""
        for rec in self:
            rec.state = 'draft'

    # ------------------------------------------------------------------
    # Conflict detection (overlap-aware, not just exact match)
    # ------------------------------------------------------------------
    @api.constrains('classroom_id', 'booking_date', 'start_time', 'end_time', 'state')
    def _check_no_overlap(self):
        """منع التعارض الزمني بين الحجوزات لنفس القاعة.

        لا يُسمح بحجزين متداخلين زمنياً في نفس القاعة بنفس التاريخ،
        ما لم يكن أحدهما ملغىً.
        """
        for rec in self:
            if rec.state == 'cancelled':
                continue
            if rec.end_time <= rec.start_time:
                raise ValidationError(_(
                    'Booking %s: end time must be strictly after start time.')
                    % rec.display_name)
            # Find any other non-cancelled booking for the same classroom+date
            # whose [start, end) interval overlaps with this one.
            domain = [
                ('id', '!=', rec.id),
                ('classroom_id', '=', rec.classroom_id.id),
                ('booking_date', '=', rec.booking_date),
                ('state', '!=', 'cancelled'),
                ('start_time', '<', rec.end_time),
                ('end_time', '>', rec.start_time),
            ]
            conflict = self.search(domain, limit=1)
            if conflict:
                raise ValidationError(_(
                    'Classroom %s is already booked on %s between %s and %s '
                    '(conflicting booking: %s).') % (
                        rec.classroom_id.display_name,
                        rec.booking_date,
                        self._format_float_time(rec.start_time),
                        self._format_float_time(rec.end_time),
                        conflict.display_name,
                    ))

    @api.model
    def _format_float_time(self, value):
        """تنسيق قيمة Float زمنية (ساعات.دقائق) إلى HH:MM."""
        if value is False or value is None:
            return '00:00'
        hours = int(value)
        minutes = int(round((value - hours) * 60))
        if minutes == 60:
            hours += 1
            minutes = 0
        return '%02d:%02d' % (hours, minutes)
