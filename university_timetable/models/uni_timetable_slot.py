# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniTimetableSlot(models.Model):
    """الفترة الزمنية — تمثل حصة (Period) أو استراحة (Break) في يوم من أيام الأسبوع.

    تُستخدم الفترات لبناء الجداول الأسبوعية؛ كل خط جدول يشير إلى فترة محددة.
    الأوقات مخزنة كـ Float (ساعات.كسور) وتُعرض عبر ``widget='float_time'``.
    """
    _name = 'uni.timetable.slot'
    _description = 'Timetable Slot'
    _inherit = ['mail.thread', 'uni.mixin.archivable']
    _order = 'day_of_week, start_time, sequence'

    name = fields.Char(
        string='Slot Name', required=True, tracking=True, translate=True, index=True)
    code = fields.Char(
        string='Code', required=True, copy=False, tracking=True, index=True,
        help='Short unique code identifying this slot.')
    sequence = fields.Integer(string='Sequence', default=10)
    day_of_week = fields.Selection([
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ], string='Day of Week', required=True, tracking=True, index=True)
    start_time = fields.Float(
        string='Start Time', required=True, tracking=True,
        help='Start time in 24h float format (8.5 = 08:30).')
    end_time = fields.Float(
        string='End Time', required=True, tracking=True,
        help='End time in 24h float format (10.25 = 10:15).')
    duration = fields.Float(
        compute='_compute_duration', store=True, string='Duration (Hours)',
        help='Computed duration in hours = end_time - start_time.')
    break_slot = fields.Boolean(
        string='Break', default=False, tracking=True,
        help='Mark this slot as a break (no teaching).')
    description = fields.Text(string='Description')

    # ------------------------------------------------------------------
    # Computed
    # ------------------------------------------------------------------
    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for rec in self:
            if rec.start_time is not False and rec.end_time is not False:
                rec.duration = max(0.0, rec.end_time - rec.start_time)
            else:
                rec.duration = 0.0

    _sql_constraints = [
        ('unique_slot_day_start',
         'unique(day_of_week, start_time)',
         'A slot already exists for this day at the same start time!'),
        ('check_slot_times',
         'check(end_time > start_time)',
         'End time must be after start time!'),
        ('check_slot_time_range',
         'check(start_time >= 0 AND end_time <= 24)',
         'Time must be between 00:00 and 24:00!'),
    ]

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('start_time', 'end_time')
    def _check_times(self):
        for rec in self:
            if rec.start_time < 0 or rec.end_time > 24:
                raise ValidationError(_(
                    'Slot %s: time must be between 00:00 and 24:00.')
                    % rec.display_name)
            if rec.end_time <= rec.start_time:
                raise ValidationError(_(
                    'Slot %s: end time must be after start time.')
                    % rec.display_name)

    # ------------------------------------------------------------------
    # Display helper
    # ------------------------------------------------------------------
    @api.depends('name', 'day_of_week', 'start_time', 'end_time')
    def _compute_display_name(self):
        for rec in self:
            label = dict(rec._fields['day_of_week'].selection).get(rec.day_of_week, '')
            rec.display_name = '%s — %s [%s-%s]' % (
                rec.name, label,
                self._format_float_time(rec.start_time),
                self._format_float_time(rec.end_time),
            )

    @api.model
    def _format_float_time(self, value):
        """تنسيق قيمة Float زمنية إلى HH:MM."""
        if value is False or value is None:
            return '00:00'
        hours = int(value)
        minutes = int(round((value - hours) * 60))
        if minutes == 60:
            hours += 1
            minutes = 0
        return '%02d:%02d' % (hours, minutes)
