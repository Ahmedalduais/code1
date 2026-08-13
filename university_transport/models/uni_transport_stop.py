# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniTransportStop(models.Model):
    """المحطة — نقطة توقف على خط نقل.

    كل محطة تنتمي إلى خط وتحمل اسماً وموقعاً نصياً وإحداثيات
    جغرافية اختيارية (lat,long) وأوقات وصول ومغادرة، إضافة إلى
    تصنيفها كنقطة ركوب و/أو نقطة إنزال.
    """
    _name = 'uni.transport.stop'
    _description = 'University Transport Stop'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'route_id, sequence, id'

    # ------------------------------------------------------------------
    # Identification
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Name', required=True, tracking=True, index=True,
        help='Display name of the stop (e.g. "Gate A — Library").')
    code = fields.Char(
        string='Code', copy=False, tracking=True, index=True,
        help='Unique code identifying the stop within the route.')

    # ------------------------------------------------------------------
    # Parent route
    # ------------------------------------------------------------------
    route_id = fields.Many2one(
        'uni.transport.route', string='Route', required=True,
        ondelete='cascade', tracking=True, index=True,
        help='Route to which this stop belongs.')
    university_id = fields.Many2one(
        'uni.university', string='University',
        related='route_id.university_id', store=True, index=True,
        help='University operating the route (related from route).')

    # ------------------------------------------------------------------
    # Ordering & location
    # ------------------------------------------------------------------
    sequence = fields.Integer(
        string='Sequence', default=10, tracking=True,
        help='Order of the stop on the route (lower comes first).')
    location_name = fields.Char(
        string='Location Name', required=True, tracking=True,
        help='Human-readable location of the stop.')
    coordinates = fields.Char(
        string='Coordinates', tracking=True,
        help='Geographic coordinates of the stop in "lat,long" format '
             '(e.g. "24.7136,46.6753").')

    # ------------------------------------------------------------------
    # Schedule
    # ------------------------------------------------------------------
    arrival_time = fields.Float(
        string='Arrival Time', digits=(16, 2),
        widget='float_time', tracking=True,
        help='Scheduled arrival time at this stop (decimal hours).')
    departure_time = fields.Float(
        string='Departure Time', digits=(16, 2),
        widget='float_time', tracking=True,
        help='Scheduled departure time from this stop (decimal hours).')

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------
    is_pickup_point = fields.Boolean(
        string='Pickup Point', default=True, tracking=True,
        help='True if students can be picked up at this stop.')
    is_drop_point = fields.Boolean(
        string='Drop Point', default=True, tracking=True,
        help='True if students can be dropped off at this stop.')

    # ------------------------------------------------------------------
    # Notes
    # ------------------------------------------------------------------
    notes = fields.Text(
        string='Notes', translate=True,
        help='Internal notes about this stop.')

    _sql_constraints = [
        ('unique_route_code',
         'unique(route_id, code)',
         'Stop code must be unique per route!'),
    ]

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('arrival_time', 'departure_time')
    def _check_time_order(self):
        """Validate that arrival/departure are in [0,24] and ordered.

        We allow the case where either value is unset (0.0). When both
        are set and positive, departure must be on or after arrival
        (a vehicle cannot depart before it arrives).
        """
        for rec in self:
            for value, label in ((rec.arrival_time, 'arrival'),
                                 (rec.departure_time, 'departure')):
                if value is not None and (value < 0 or value > 24):
                    raise ValidationError(_(
                        "Stop %(name)s: %(label)s time must be between 0 "
                        "and 24 hours (got %(val)s).") % {
                        'name': rec.name,
                        'label': label,
                        'val': value,
                    })
            if rec.arrival_time and rec.departure_time \
                    and rec.departure_time < rec.arrival_time:
                raise ValidationError(_(
                    "Stop %(name)s: departure time (%(dep)s) cannot be "
                    "before arrival time (%(arr)s).") % {
                    'name': rec.name,
                    'dep': rec.departure_time,
                    'arr': rec.arrival_time,
                })

    @api.constrains('is_pickup_point', 'is_drop_point')
    def _check_at_least_one_role(self):
        """A stop must be at least a pickup or a drop point."""
        for rec in self:
            if not rec.is_pickup_point and not rec.is_drop_point:
                raise ValidationError(_(
                    "Stop %(name)s must be either a pickup point, a drop "
                    "point, or both.") % {'name': rec.name})
