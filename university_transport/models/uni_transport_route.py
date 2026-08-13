# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class UniTransportRoute(models.Model):
    """الخط — مسار نقل جامعي بين نقطتين مع محطات وسياق.

    يصف الخط نقطة البداية والنهاية، المسافة، المدة التقديرية،
    أوقات المغادرة والوصول، أيام التشغيل، والمركبة والسائق
    المخصصين.

    يحتوي الخط على محطات (``uni.transport.stop``) وبطاقات طلاب
    (``uni.transport.pass``). تتوفّر أربع حالات
    (مسودة/نشط/معلق/مغلق) مع workflow كامل.
    """
    _name = 'uni.transport.route'
    _description = 'University Transport Route'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'university_id, code, name'

    # ------------------------------------------------------------------
    # Identification
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Name', required=True, tracking=True, index=True,
        help='Display name of the route (e.g. "North Campus Line").')
    code = fields.Char(
        string='Code', copy=False, tracking=True, index=True,
        help='Unique code identifying the route within the university.')

    # ------------------------------------------------------------------
    # Affiliation
    # ------------------------------------------------------------------
    university_id = fields.Many2one(
        'uni.university', string='University', required=True,
        ondelete='restrict', tracking=True, index=True,
        help='University operating this route.')
    branch_id = fields.Many2one(
        'uni.branch', string='Branch',
        ondelete='restrict', tracking=True, index=True,
        help='Branch served by this route (optional).')

    # ------------------------------------------------------------------
    # Path
    # ------------------------------------------------------------------
    start_point = fields.Char(
        string='Start Point', required=True, tracking=True,
        help='Starting point of the route (e.g. "Main Gate").')
    end_point = fields.Char(
        string='End Point', required=True, tracking=True,
        help='Ending point of the route (e.g. "North Campus").')
    distance_km = fields.Float(
        string='Distance (km)', digits=(16, 2), tracking=True,
        help='Total distance of the route in kilometres.')
    estimated_duration = fields.Float(
        string='Estimated Duration', digits=(16, 2),
        widget='float_time', tracking=True,
        help='Estimated trip duration in hours (decimal time format).')

    # ------------------------------------------------------------------
    # Schedule
    # ------------------------------------------------------------------
    departure_time = fields.Float(
        string='Departure Time', digits=(16, 2),
        widget='float_time', tracking=True,
        help='Scheduled departure time (decimal hours, e.g. 7.5 = 07:30).')
    arrival_time = fields.Float(
        string='Arrival Time', digits=(16, 2),
        widget='float_time', tracking=True,
        help='Scheduled arrival time (decimal hours, e.g. 8.25 = 08:15).')
    operating_days = fields.Selection([
        ('all', 'All Days'),
        ('weekdays', 'Weekdays'),
        ('weekend', 'Weekend'),
        ('custom', 'Custom'),
    ], string='Operating Days', default='all', required=True,
        tracking=True, index=True,
        help='Days on which the route operates.')

    # ------------------------------------------------------------------
    # Resources
    # ------------------------------------------------------------------
    vehicle_id = fields.Many2one(
        'uni.transport.vehicle', string='Vehicle',
        ondelete='restrict', tracking=True, index=True,
        domain="[('university_id', '=', university_id)]",
        help='Vehicle assigned to this route.')
    driver_id = fields.Many2one(
        'hr.employee', string='Driver',
        ondelete='restrict', tracking=True, index=True,
        help='Employee assigned as the driver of this route.')

    # ------------------------------------------------------------------
    # Relations
    # ------------------------------------------------------------------
    stop_ids = fields.One2many(
        'uni.transport.stop', 'route_id', string='Stops', copy=True,
        help='Ordered list of stops on this route.')
    pass_ids = fields.One2many(
        'uni.transport.pass', 'route_id', string='Passes',
        help='Transport passes issued for this route.')
    stop_count = fields.Integer(
        string='Stops Count', compute='_compute_stop_count', store=True)
    pass_count = fields.Integer(
        string='Passes Count', compute='_compute_pass_count', store=True)

    # ------------------------------------------------------------------
    # State & notes
    # ------------------------------------------------------------------
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('closed', 'Closed'),
    ], string='State', default='draft', required=True,
        tracking=True, index=True, group_expand='_group_expand_states',
        help='Lifecycle state of the route.')
    notes = fields.Text(
        string='Notes', translate=True,
        help='Internal notes about this route.')

    _sql_constraints = [
        ('unique_university_code',
         'unique(university_id, code)',
         'Route code must be unique per university!'),
        ('check_distance_positive',
         'CHECK(distance_km >= 0)',
         'Route distance cannot be negative!'),
        ('check_estimated_duration_positive',
         'CHECK(estimated_duration >= 0)',
         'Route estimated duration cannot be negative!'),
    ]

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends('stop_ids')
    def _compute_stop_count(self):
        """Count the stops on this route."""
        for rec in self:
            rec.stop_count = len(rec.stop_ids)

    @api.depends('pass_ids')
    def _compute_pass_count(self):
        """Count the passes issued for this route."""
        for rec in self:
            rec.pass_count = len(rec.pass_ids)

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
    def action_activate(self):
        """Activate the route so it can be used for transport."""
        for rec in self:
            if rec.state != 'draft' and rec.state != 'suspended':
                raise UserError(_(
                    "Route %(name)s cannot be activated from state "
                    "%(state)s.") % {
                    'name': rec.name,
                    'state': rec.state,
                })
            rec.state = 'active'
            rec.message_post(body=_(
                "Route %(name)s activated.") % {'name': rec.name})

    def action_suspend(self):
        """Temporarily suspend the route."""
        for rec in self:
            if rec.state != 'active':
                raise UserError(_(
                    "Only active routes can be suspended. Route %(name)s is "
                    "%(state)s.") % {
                    'name': rec.name,
                    'state': rec.state,
                })
            rec.state = 'suspended'
            rec.message_post(body=_(
                "Route %(name)s suspended.") % {'name': rec.name})

    def action_close(self):
        """Permanently close the route."""
        for rec in self:
            if rec.state == 'closed':
                raise UserError(_(
                    "Route %(name)s is already closed.") % {
                    'name': rec.name})
            rec.state = 'closed'
            rec.message_post(body=_(
                "Route %(name)s closed.") % {'name': rec.name})

    def action_draft(self):
        """Reset the route to draft state."""
        for rec in self:
            if rec.state == 'active':
                raise UserError(_(
                    "Cannot reset active route %(name)s to draft. Suspend "
                    "it first.") % {'name': rec.name})
            rec.state = 'draft'
            rec.message_post(body=_(
                "Route %(name)s reset to draft.") % {'name': rec.name})

    def action_view_stops(self):
        """Open the list of stops on this route."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Stops'),
            'res_model': 'uni.transport.stop',
            'view_mode': 'list,form',
            'domain': [('route_id', '=', self.id)],
            'context': {'default_route_id': self.id,
                        'default_university_id': self.university_id.id},
        }

    def action_view_passes(self):
        """Open the list of passes issued for this route."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Passes'),
            'res_model': 'uni.transport.pass',
            'view_mode': 'list,form',
            'domain': [('route_id', '=', self.id)],
            'context': {'default_route_id': self.id,
                        'default_university_id': self.university_id.id},
        }

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('departure_time', 'arrival_time')
    def _check_times(self):
        """Departure and arrival times must be in 0-24 range.

        If both are set and the route is not overnight, arrival should
        be after departure. We allow overnight routes (arrival earlier
        than departure) because some long-distance services cross
        midnight.
        """
        for rec in self:
            for value, label in ((rec.departure_time, 'departure'),
                                 (rec.arrival_time, 'arrival')):
                if value is not None and (value < 0 or value > 24):
                    raise ValidationError(_(
                        "Route %(name)s: %(label)s time must be between 0 "
                        "and 24 hours (got %(val)s).") % {
                        'name': rec.name,
                        'label': label,
                        'val': value,
                    })

    @api.constrains('vehicle_id', 'university_id')
    def _check_vehicle_university(self):
        """The assigned vehicle must belong to the same university."""
        for rec in self:
            if rec.vehicle_id and rec.vehicle_id.university_id \
                    and rec.vehicle_id.university_id != rec.university_id:
                raise ValidationError(_(
                    "Vehicle %(veh)s does not belong to the same university "
                    "as route %(name)s.") % {
                    'veh': rec.vehicle_id.display_name,
                    'name': rec.name,
                })
