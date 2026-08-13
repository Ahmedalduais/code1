# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class UniTransportAttendance(models.Model):
    """حضور النقل — سجل حضور يومي لخط نقل.

    يحتوي السجل على تاريخ وخط ومركبة وسائق (المركبة والسائق
    مرتبطان من الخط)، واتجاه الرحلة (صباحية/ظهرية/مسائية/أخرى).
    يضم خطوطاً لكل بطاقة نقل نشطة على الخط مع حالة الحضور
    (حاضر/غائب/متأخر/ملغى).

    يقوم النموذج بحساب المجاميع تلقائياً (الإجمالي/الحاضر/الغائب)
    ويتيح ملء الخطوط تلقائياً من بطاقات الخط النشطة عبر
    ``action_populate_lines()``.
    """
    _name = 'uni.transport.attendance'
    _description = 'University Transport Attendance'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'date desc, id desc'

    # ------------------------------------------------------------------
    # Identification
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True,
        default='New', tracking=True, index=True,
        help='Unique sequence reference of the attendance (TRA/...).')
    code = fields.Char(
        string='Code', copy=False, tracking=True, index=True,
        help='Optional secondary code for manual lookups.')

    # ------------------------------------------------------------------
    # Trip context
    # ------------------------------------------------------------------
    date = fields.Date(
        string='Date', required=True,
        default=fields.Date.context_today, tracking=True, index=True,
        help='Date of the transport trip.')
    route_id = fields.Many2one(
        'uni.transport.route', string='Route', required=True,
        ondelete='restrict', tracking=True, index=True,
        help='Route on which this attendance was taken.')
    university_id = fields.Many2one(
        'uni.university', string='University',
        related='route_id.university_id', store=True, index=True,
        help='University operating the route (related from route).')
    vehicle_id = fields.Many2one(
        'uni.transport.vehicle', string='Vehicle',
        related='route_id.vehicle_id', store=True, tracking=True,
        help='Vehicle assigned to the route (related from route).')
    driver_id = fields.Many2one(
        'hr.employee', string='Driver',
        related='route_id.driver_id', store=True, tracking=True,
        help='Driver assigned to the route (related from route).')
    direction = fields.Selection([
        ('morning_pickup', 'Morning Pickup'),
        ('afternoon_drop', 'Afternoon Drop'),
        ('night_drop', 'Night Drop'),
        ('other', 'Other'),
    ], string='Direction', default='morning_pickup', required=True,
        tracking=True, index=True,
        help='Direction/purpose of the trip.')

    # ------------------------------------------------------------------
    # Lines & totals
    # ------------------------------------------------------------------
    line_ids = fields.One2many(
        'uni.transport.attendance.line', 'attendance_id', string='Lines',
        copy=True,
        help='Per-pass attendance lines for this trip.')
    total_passengers = fields.Integer(
        string='Total Passengers', compute='_compute_totals', store=True,
        help='Total number of passengers expected on this trip.')
    present_count = fields.Integer(
        string='Present', compute='_compute_totals', store=True,
        help='Number of passengers marked present.')
    absent_count = fields.Integer(
        string='Absent', compute='_compute_totals', store=True,
        help='Number of passengers marked absent.')

    # ------------------------------------------------------------------
    # State & notes
    # ------------------------------------------------------------------
    state = fields.Selection([
        ('draft', 'Draft'),
        ('validated', 'Validated'),
    ], string='State', default='draft', required=True,
        tracking=True, index=True, group_expand='_group_expand_states',
        help='Lifecycle state of the attendance record.')
    notes = fields.Text(
        string='Notes', translate=True,
        help='Internal notes about this attendance.')

    _sql_constraints = [
        ('unique_attendance_name',
         'unique(name)',
         'Attendance reference must be unique!'),
    ]

    # ------------------------------------------------------------------
    # Create — auto sequence
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        """Auto-generate the TRA sequence reference for each new record."""
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.transport.attendance') or 'New'
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends('line_ids', 'line_ids.status')
    def _compute_totals(self):
        """Compute total, present, and absent passenger counts."""
        for rec in self:
            lines = rec.line_ids
            rec.total_passengers = len(lines)
            rec.present_count = sum(
                1 for ln in lines if ln.status == 'present')
            rec.absent_count = sum(
                1 for ln in lines if ln.status in ('absent', 'cancelled'))

    # ------------------------------------------------------------------
    # Group expand
    # ------------------------------------------------------------------
    @api.model
    def _group_expand_states(self, states, domain, order):
        """Return all known state keys for grouping."""
        return [key for key, _label in self._fields['state'].selection]

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_populate_lines(self):
        """Pre-populate attendance lines from active passes on the route.

        For each active pass on the chosen route, creates an attendance
        line with the pass, the student, and the default pickup stop.
        Existing lines are preserved; new lines are appended.
        """
        Pass = self.env['uni.transport.pass']
        Line = self.env['uni.transport.attendance.line']
        for rec in self:
            if not rec.route_id:
                raise UserError(_(
                    "Please select a route before populating lines."))
            existing_pass_ids = rec.line_ids.mapped('pass_id').ids
            new_passes = Pass.search([
                ('route_id', '=', rec.route_id.id),
                ('state', '=', 'active'),
                ('id', 'not in', existing_pass_ids),
            ], order='student_id')
            new_lines = []
            for p in new_passes:
                new_lines.append((0, 0, {
                    'pass_id': p.id,
                    'student_id': p.student_id.id,
                    'pickup_stop_id': p.pickup_stop_id.id if p.pickup_stop_id else False,
                    'status': 'present',
                }))
            if new_lines:
                rec.write({'line_ids': new_lines})
            rec.message_post(body=_(
                "Populated %(n)d attendance line(s) from active passes on "
                "route %(route)s.") % {
                'n': len(new_lines),
                'route': rec.route_id.display_name,
            })

    def action_validate(self):
        """Validate the attendance record (lock it from editing)."""
        for rec in self:
            if not rec.line_ids:
                raise UserError(_(
                    "Cannot validate attendance %(name)s without any "
                    "lines. Please populate lines first.") % {
                    'name': rec.name})
            rec.state = 'validated'
            rec.message_post(body=_(
                "Attendance %(name)s validated. Present: %(p)d, Absent: "
                "%(a)d, Total: %(t)d.") % {
                'name': rec.name,
                'p': rec.present_count,
                'a': rec.absent_count,
                't': rec.total_passengers,
            })

    def action_draft(self):
        """Reset the attendance record back to draft."""
        for rec in self:
            rec.state = 'draft'
            rec.message_post(body=_(
                "Attendance %(name)s reset to draft.") % {'name': rec.name})

    def action_view_lines(self):
        """Open the lines of this attendance record."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Attendance Lines'),
            'res_model': 'uni.transport.attendance.line',
            'view_mode': 'list',
            'domain': [('attendance_id', '=', self.id)],
            'context': {'default_attendance_id': self.id},
        }


class UniTransportAttendanceLine(models.Model):
    """خطّ حضور النقل — سطر حضور لكل بطاقة في رحلة.

    يربط سجل الحضور ببطاقة نقل والطالب المرتبط بها، ومحطة الركوب،
    وحالة الحضور (حاضر/غائب/متأخر/ملغى) وأوقات الركوب المجدولة
    والفعلية.
    """
    _name = 'uni.transport.attendance.line'
    _description = 'University Transport Attendance Line'
    _order = 'attendance_id, pickup_stop_id, student_id'

    # ------------------------------------------------------------------
    # Parent
    # ------------------------------------------------------------------
    attendance_id = fields.Many2one(
        'uni.transport.attendance', string='Attendance', required=True,
        ondelete='cascade', index=True,
        help='Attendance record to which this line belongs.')
    date = fields.Date(
        string='Date',
        related='attendance_id.date', store=True, index=True,
        help='Date of the trip (related from attendance).')
    route_id = fields.Many2one(
        'uni.transport.route', string='Route',
        related='attendance_id.route_id', store=True, index=True,
        help='Route of the trip (related from attendance).')

    # ------------------------------------------------------------------
    # Pass & student
    # ------------------------------------------------------------------
    pass_id = fields.Many2one(
        'uni.transport.pass', string='Pass',
        ondelete='restrict', index=True,
        help='Transport pass used by the student.')
    student_id = fields.Many2one(
        'uni.student', string='Student', required=True,
        ondelete='restrict', tracking=True, index=True,
        help='Student whose attendance is being recorded.')
    student_name = fields.Char(
        string='Student Name',
        related='student_id.display_name', store=False,
        help='Display name of the student (for quick reference).')

    # ------------------------------------------------------------------
    # Pickup
    # ------------------------------------------------------------------
    pickup_stop_id = fields.Many2one(
        'uni.transport.stop', string='Pickup Stop',
        ondelete='restrict', index=True,
        domain="[('route_id', '=', route_id), ('is_pickup_point', '=', True)]",
        help='Stop where the student is expected to be picked up.')

    # ------------------------------------------------------------------
    # Status & timing
    # ------------------------------------------------------------------
    status = fields.Selection([
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='present', required=True,
        tracking=True, index=True,
        help='Attendance status of the student on this trip.')
    pickup_time = fields.Float(
        string='Scheduled Pickup', digits=(16, 2),
        widget='float_time',
        help='Scheduled pickup time at the stop (decimal hours).')
    actual_pickup_time = fields.Float(
        string='Actual Pickup', digits=(16, 2),
        widget='float_time',
        help='Actual pickup time of the student (decimal hours).')

    # ------------------------------------------------------------------
    # Notes
    # ------------------------------------------------------------------
    notes = fields.Text(
        string='Notes', translate=True,
        help='Internal notes about this attendance line.')

    # ------------------------------------------------------------------
    # Onchanges
    # ------------------------------------------------------------------
    @api.onchange('pass_id')
    def _onchange_pass_id(self):
        """When a pass is selected, default the student and pickup stop."""
        if self.pass_id:
            self.student_id = self.pass_id.student_id
            self.pickup_stop_id = self.pass_id.pickup_stop_id \
                if self.pass_id.pickup_stop_id else False
            self.pickup_time = self.pickup_stop_id.departure_time \
                if self.pickup_stop_id else 0.0

    @api.onchange('pickup_stop_id')
    def _onchange_pickup_stop_id(self):
        """When a pickup stop is selected, default the scheduled pickup time."""
        if self.pickup_stop_id:
            self.pickup_time = self.pickup_stop_id.departure_time

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('pickup_time', 'actual_pickup_time')
    def _check_times(self):
        """Pickup times must be in [0, 24] hours."""
        for rec in self:
            for value, label in ((rec.pickup_time, 'scheduled pickup'),
                                 (rec.actual_pickup_time, 'actual pickup')):
                if value is not None and (value < 0 or value > 24):
                    raise ValidationError(_(
                        "Line for student %(student)s: %(label)s time must "
                        "be between 0 and 24 hours (got %(val)s).") % {
                        'student': rec.student_id.display_name,
                        'label': label,
                        'val': value,
                    })

    @api.constrains('pass_id', 'student_id')
    def _check_pass_student(self):
        """The selected pass must belong to the selected student."""
        for rec in self:
            if rec.pass_id and rec.student_id \
                    and rec.pass_id.student_id != rec.student_id:
                raise ValidationError(_(
                    "Pass %(pass)s does not belong to student %(student)s.") % {
                    'pass': rec.pass_id.display_name,
                    'student': rec.student_id.display_name,
                })
