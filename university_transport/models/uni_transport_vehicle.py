# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class UniTransportVehicle(models.Model):
    """المركبة — تسجيل مركبة نقل جامعي.

    يوفّر النموذج بيانات كاملة للمركبة (اللوحة، النوع، الماركة،
    الموديل، السنة، اللون، رقم الشاسيه VIN) ومعلومات تشغيلية
    (السعة، نوع الوقود، استهلاك الوقود، العداد الحالي) ومعلومات
    إدارية (تاريخ الشراء وسعره، انتهاء التأمين والترخيص، السائق).

    تتوفّر المركبة في أربع حالات (متاحة/قيد الاستخدام/صيانة/متقاعدة)
    مع workflow كامل عبر أزرار الإجراءات.
    """
    _name = 'uni.transport.vehicle'
    _description = 'University Transport Vehicle'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'university_id, code, plate_number'

    # ------------------------------------------------------------------
    # Identification
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Name', required=True, tracking=True, index=True,
        help='Display name of the vehicle (e.g. "Bus A — North Route").')
    code = fields.Char(
        string='Code', copy=False, tracking=True, index=True,
        help='Unique code identifying the vehicle within the university.')
    plate_number = fields.Char(
        string='Plate Number', required=True, tracking=True, index=True,
        help='Official license plate number of the vehicle.')

    # ------------------------------------------------------------------
    # Affiliation
    # ------------------------------------------------------------------
    university_id = fields.Many2one(
        'uni.university', string='University', required=True,
        ondelete='restrict', tracking=True, index=True,
        help='University that owns or operates this vehicle.')
    branch_id = fields.Many2one(
        'uni.branch', string='Branch',
        ondelete='restrict', tracking=True, index=True,
        help='Branch to which the vehicle is assigned (optional).')

    # ------------------------------------------------------------------
    # Vehicle characteristics
    # ------------------------------------------------------------------
    vehicle_type = fields.Selection([
        ('bus', 'Bus'),
        ('minibus', 'Minibus'),
        ('van', 'Van'),
        ('car', 'Car'),
        ('sedan', 'Sedan'),
        ('suv', 'SUV'),
        ('other', 'Other'),
    ], string='Vehicle Type', default='bus', required=True,
        tracking=True, index=True,
        help='Type of the vehicle.')
    brand = fields.Char(
        string='Brand', tracking=True,
        help='Manufacturer brand (e.g. Mercedes, Toyota).')
    model = fields.Char(
        string='Model', tracking=True,
        help='Model name of the vehicle.')
    year = fields.Integer(
        string='Year', tracking=True,
        help='Manufacturing year of the vehicle.')
    color = fields.Char(
        string='Color', tracking=True,
        help='Exterior color of the vehicle.')
    vin = fields.Char(
        string='VIN', tracking=True, index=True,
        help='Vehicle Identification Number (chassis number).')
    capacity = fields.Integer(
        string='Capacity', required=True, tracking=True,
        help='Maximum number of passengers the vehicle can carry.')

    # ------------------------------------------------------------------
    # Fuel & mileage
    # ------------------------------------------------------------------
    fuel_type = fields.Selection([
        ('petrol', 'Petrol'),
        ('diesel', 'Diesel'),
        ('electric', 'Electric'),
        ('hybrid', 'Hybrid'),
        ('hydrogen', 'Hydrogen'),
    ], string='Fuel Type', default='diesel', tracking=True, index=True,
        help='Type of fuel used by the vehicle.')
    fuel_consumption = fields.Float(
        string='Fuel Consumption', digits=(16, 2), tracking=True,
        help='Average fuel consumption in litres per 100 km (L/100km).')
    mileage = fields.Float(
        string='Mileage (km)', digits=(16, 2), tracking=True,
        help='Current mileage of the vehicle in kilometres.')

    # ------------------------------------------------------------------
    # Purchase & financials
    # ------------------------------------------------------------------
    purchase_date = fields.Date(
        string='Purchase Date', tracking=True,
        help='Date the vehicle was purchased by the university.')
    purchase_price = fields.Float(
        string='Purchase Price', digits=(16, 2), tracking=True,
        help='Purchase price of the vehicle.')
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
        help='Currency used for the purchase price.')

    # ------------------------------------------------------------------
    # Compliance
    # ------------------------------------------------------------------
    insurance_expiry = fields.Date(
        string='Insurance Expiry', tracking=True,
        help='Date when the vehicle insurance policy expires.')
    registration_expiry = fields.Date(
        string='Registration Expiry', tracking=True,
        help='Date when the vehicle registration expires.')

    # ------------------------------------------------------------------
    # Driver & photo
    # ------------------------------------------------------------------
    driver_id = fields.Many2one(
        'hr.employee', string='Driver',
        ondelete='restrict', tracking=True, index=True,
        help='Employee assigned as the driver of this vehicle.')
    photo = fields.Image(
        string='Photo', max_width=1024, max_height=1024,
        help='Photo of the vehicle.')

    # ------------------------------------------------------------------
    # Relations
    # ------------------------------------------------------------------
    route_ids = fields.Many2many(
        'uni.transport.route', string='Routes',
        relation='uni_transport_vehicle_route_rel',
        column1='vehicle_id', column2='route_id',
        help='Routes assigned to this vehicle.')
    route_count = fields.Integer(
        string='Routes Count', compute='_compute_route_count', store=True)

    # ------------------------------------------------------------------
    # State & notes
    # ------------------------------------------------------------------
    state = fields.Selection([
        ('available', 'Available'),
        ('in_use', 'In Use'),
        ('maintenance', 'Maintenance'),
        ('retired', 'Retired'),
    ], string='State', default='available', required=True,
        tracking=True, index=True, group_expand='_group_expand_states',
        help='Lifecycle state of the vehicle.')
    notes = fields.Text(
        string='Notes', translate=True,
        help='Internal notes about this vehicle.')

    _sql_constraints = [
        ('unique_university_code',
         'unique(university_id, code)',
         'Vehicle code must be unique per university!'),
        ('unique_university_plate',
         'unique(university_id, plate_number)',
         'Vehicle plate number must be unique per university!'),
        ('check_capacity_positive',
         'CHECK(capacity > 0)',
         'Vehicle capacity must be greater than zero!'),
        ('check_year_positive',
         'CHECK(year IS NULL OR year > 0)',
         'Vehicle manufacturing year must be positive!'),
        ('check_mileage_positive',
         'CHECK(mileage >= 0)',
         'Vehicle mileage cannot be negative!'),
        ('check_fuel_consumption_positive',
         'CHECK(fuel_consumption >= 0)',
         'Vehicle fuel consumption cannot be negative!'),
        ('check_purchase_price_positive',
         'CHECK(purchase_price >= 0)',
         'Vehicle purchase price cannot be negative!'),
    ]

    # ------------------------------------------------------------------
    # Group expand
    # ------------------------------------------------------------------
    @api.model
    def _group_expand_states(self, states, domain, order):
        """Return all known state keys for grouping."""
        return [key for key, _label in self._fields['state'].selection]

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends('route_ids')
    def _compute_route_count(self):
        """Count the routes assigned to this vehicle."""
        for rec in self:
            rec.route_count = len(rec.route_ids)

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_assign(self):
        """Mark the vehicle as currently in use."""
        for rec in self:
            if rec.state != 'available':
                raise UserError(_(
                    "Vehicle %(name)s cannot be set to 'In Use' from "
                    "state %(state)s. It must be 'Available' first.") % {
                    'name': rec.name,
                    'state': rec.state,
                })
            rec.state = 'in_use'
            rec.message_post(body=_(
                "Vehicle %(name)s is now in use.") % {'name': rec.name})

    def action_maintenance(self):
        """Send the vehicle to maintenance."""
        for rec in self:
            if rec.state in ('retired',):
                raise UserError(_(
                    "Cannot send retired vehicle %(name)s to maintenance.") % {
                    'name': rec.name,
                })
            rec.state = 'maintenance'
            rec.message_post(body=_(
                "Vehicle %(name)s sent to maintenance.") % {
                'name': rec.name})

    def action_retire(self):
        """Retire the vehicle permanently."""
        for rec in self:
            if rec.state == 'retired':
                raise UserError(_(
                    "Vehicle %(name)s is already retired.") % {
                    'name': rec.name})
            rec.state = 'retired'
            rec.message_post(body=_(
                "Vehicle %(name)s has been retired.") % {'name': rec.name})

    def action_available(self):
        """Mark the vehicle as available for assignment."""
        for rec in self:
            if rec.state == 'retired':
                raise UserError(_(
                    "Retired vehicle %(name)s cannot be set to 'Available'. "
                    "Use a different vehicle or un-retire it first.") % {
                    'name': rec.name})
            rec.state = 'available'
            rec.message_post(body=_(
                "Vehicle %(name)s is now available.") % {'name': rec.name})

    def action_view_routes(self):
        """Open the list of routes assigned to this vehicle."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Assigned Routes'),
            'res_model': 'uni.transport.route',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.route_ids.ids)],
            'context': {'default_vehicle_id': self.id,
                        'default_university_id': self.university_id.id},
        }

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('insurance_expiry', 'purchase_date')
    def _check_insurance_after_purchase(self):
        """Insurance expiry must be after the purchase date."""
        for rec in self:
            if rec.insurance_expiry and rec.purchase_date \
                    and rec.insurance_expiry < rec.purchase_date:
                raise ValidationError(_(
                    "Insurance expiry (%(exp)s) cannot be before purchase "
                    "date (%(pur)s) for vehicle %(name)s.") % {
                    'exp': rec.insurance_expiry,
                    'pur': rec.purchase_date,
                    'name': rec.name,
                })

    @api.constrains('registration_expiry', 'purchase_date')
    def _check_registration_after_purchase(self):
        """Registration expiry must be after the purchase date."""
        for rec in self:
            if rec.registration_expiry and rec.purchase_date \
                    and rec.registration_expiry < rec.purchase_date:
                raise ValidationError(_(
                    "Registration expiry (%(exp)s) cannot be before purchase "
                    "date (%(pur)s) for vehicle %(name)s.") % {
                    'exp': rec.registration_expiry,
                    'pur': rec.purchase_date,
                    'name': rec.name,
                })

    @api.constrains('insurance_expiry', 'registration_expiry')
    def _check_expiries_not_past_when_available(self):
        """Warn the user if a vehicle available/in_use has expired docs.

        We do not block saving historical records, but we prevent an
        ``available`` or ``in_use`` vehicle from having expired
        insurance or registration — this is a safety/business rule.
        """
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.state not in ('available', 'in_use'):
                continue
            if rec.insurance_expiry and rec.insurance_expiry < today:
                raise ValidationError(_(
                    "Vehicle %(name)s cannot be %(state)s while its "
                    "insurance expired on %(exp)s. Please renew it or send "
                    "the vehicle to maintenance.") % {
                    'name': rec.name,
                    'state': rec.state,
                    'exp': rec.insurance_expiry,
                })
            if rec.registration_expiry and rec.registration_expiry < today:
                raise ValidationError(_(
                    "Vehicle %(name)s cannot be %(state)s while its "
                    "registration expired on %(exp)s. Please renew it or "
                    "retire the vehicle.") % {
                    'name': rec.name,
                    'state': rec.state,
                    'exp': rec.registration_expiry,
                })
