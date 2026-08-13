from odoo import api, fields, models, _


class UniInternshipAttendance(models.Model):
    _name = 'uni.internship.attendance'
    _description = 'Internship Attendance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True,
                       default=lambda self: _('New'), index=True)
    internship_id = fields.Many2one('uni.internship', string='Internship', required=True,
                                     ondelete='cascade', tracking=True, index=True)
    student_id = fields.Many2one('uni.student', string='Student', required=True,
                                  ondelete='restrict', tracking=True, index=True)
    student_name = fields.Char(related='student_id.name', string='Student Name',
                                store=True, readonly=True)

    date = fields.Date(string='Date', required=True, default=fields.Date.context_today, tracking=True)
    check_in = fields.Float(string='Check In', widget='float_time', tracking=True)
    check_out = fields.Float(string='Check Out', widget='float_time', tracking=True)
    hours = fields.Float(compute='_compute_hours', string='Hours', store=True)

    status = fields.Selection([
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late Arrival'),
        ('early_leave', 'Early Leave'),
        ('excused', 'Excused Absence'),
        ('holiday', 'Holiday'),
    ], string='Status', default='present', required=True, tracking=True)

    location = fields.Char(string='Location')
    is_remote = fields.Boolean(string='Remote', default=False)

    late_minutes = fields.Integer(string='Late Minutes', default=0)
    early_leave_minutes = fields.Integer(string='Early Leave Minutes', default=0)

    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_attendance_reference', 'unique(name)', 'Attendance reference must be unique!'),
        ('unique_attendance_per_day', 'unique(student_id, date)',
         'Only one attendance record per student per day!'),
    ]

    @api.depends('check_in', 'check_out')
    def _compute_hours(self):
        for rec in self:
            if rec.check_in is not None and rec.check_out is not None and rec.check_out >= rec.check_in:
                rec.hours = rec.check_out - rec.check_in
            else:
                rec.hours = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('uni.internship.attendance') or _('New')
        return super().create(vals_list)
