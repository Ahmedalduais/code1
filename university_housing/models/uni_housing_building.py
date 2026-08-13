# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniHousingBuilding(models.Model):
    """المبنى — يمثل مبنى سكنياً جامعياً (سكن طلابي، شقق، فيلا، hostel).

    يحتوي النموذج على بيانات المبنى الأساسية (الاسم، الكود، الجامعة،
    الفرع، النوع، العنوان، عدد الطوابق والغرف) بالإضافة إلى المرافق
    المتوفرة (موقف سيارات، مغسلة، صالة رياضية، أمن، واي فاي) ومعلومات
    الإشراف وحالة المبنى.

    يوفّر النموذج:
        * كوداً فريداً لكل جامعة (unique per university)
        * ربط مباشر بالجامعة والفرع
        * قائمة الغرف المرتبطة (One2many)
        * عدّاد الغرف وعدّاد الغرف المشغولة (محسوب)
        * سير عمل حالة: متاح → صيانة → مغلق → متاح
        * صورة المبنى وملاحظات
    """
    _name = 'uni.housing.building'
    _description = 'Housing Building'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'university_id, code'

    # ------------------------------------------------------------------
    # Identification
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Building Name', required=True, tracking=True, translate=True,
        help='Display name of the building.')
    code = fields.Char(
        string='Code', copy=False, tracking=True, index=True,
        help='Unique code identifying the building within the university '
             '(e.g. BLD-A, DORM-1).')
    description = fields.Text(
        string='Description', translate=True,
        help='Optional description of the building.')

    # ------------------------------------------------------------------
    # University Link
    # ------------------------------------------------------------------
    university_id = fields.Many2one(
        'uni.university', string='University', required=True,
        ondelete='restrict', tracking=True, index=True,
        help='University that owns the building.')
    branch_id = fields.Many2one(
        'uni.branch', string='Branch',
        ondelete='restrict', tracking=True, index=True,
        help='Branch of the university where the building is located.')

    # ------------------------------------------------------------------
    # Type & Location
    # ------------------------------------------------------------------
    building_type = fields.Selection([
        ('dormitory', 'Dormitory'),
        ('apartment', 'Apartment'),
        ('villa', 'Villa'),
        ('hostel', 'Hostel'),
    ], string='Building Type', default='dormitory', required=True,
        tracking=True, index=True,
        help='Physical type of the building structure.')
    address = fields.Char(
        string='Address', tracking=True,
        help='Street address of the building.')
    city = fields.Char(
        string='City', tracking=True,
        help='City where the building is located.')
    country_id = fields.Many2one(
        'res.country', string='Country', tracking=True,
        help='Country where the building is located.')
    floors = fields.Integer(
        string='Floors', default=1, tracking=True,
        help='Total number of floors in the building.')
    total_rooms = fields.Integer(
        string='Total Rooms', default=0, tracking=True,
        help='Total number of rooms planned for the building (informational).')

    # ------------------------------------------------------------------
    # Amenities
    # ------------------------------------------------------------------
    has_parking = fields.Boolean(
        string='Parking', tracking=True,
        help='True if the building provides parking facilities.')
    has_laundry = fields.Boolean(
        string='Laundry', tracking=True,
        help='True if the building has a laundry room/service.')
    has_gym = fields.Boolean(
        string='Gym', tracking=True,
        help='True if the building has a fitness gym.')
    has_security = fields.Boolean(
        string='Security', tracking=True,
        help='True if the building has security personnel or service.')
    has_wifi = fields.Boolean(
        string='Wi-Fi', tracking=True,
        help='True if the building provides Wi-Fi connectivity.')

    # ------------------------------------------------------------------
    # Supervision & Media
    # ------------------------------------------------------------------
    supervisor_id = fields.Many2one(
        'res.users', string='Supervisor', tracking=True,
        help='User responsible for supervising the building.')
    photo = fields.Image(
        string='Building Photo', max_width=1024, max_height=1024,
        help='Photo of the building exterior or interior.')

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------
    state = fields.Selection([
        ('available', 'Available'),
        ('maintenance', 'Maintenance'),
        ('closed', 'Closed'),
    ], string='State', default='available', required=True,
        tracking=True, index=True, group_expand='_group_expand_states',
        help='Lifecycle state of the building record.')

    # ------------------------------------------------------------------
    # Relations & Computed
    # ------------------------------------------------------------------
    room_ids = fields.One2many(
        'uni.housing.room', 'building_id', string='Rooms',
        help='Rooms located inside this building.')
    room_count = fields.Integer(
        string='Room Count', compute='_compute_room_count', store=True,
        help='Number of rooms currently registered in this building.')
    occupied_count = fields.Integer(
        string='Occupied Rooms', compute='_compute_occupied', store=True,
        help='Number of rooms in this building that are fully occupied '
             '(state = full).')
    notes = fields.Text(
        string='Notes', translate=True,
        help='Internal notes about the building.')
    active = fields.Boolean(default=True, tracking=True)

    _sql_constraints = [
        ('unique_building_code_per_university',
         'unique(university_id, code)',
         'Building code must be unique per university!'),
        ('check_floors_positive', 'check(floors >= 0)',
         'Number of floors cannot be negative!'),
        ('check_total_rooms_positive', 'check(total_rooms >= 0)',
         'Total rooms cannot be negative!'),
    ]

    # ------------------------------------------------------------------
    # Computations
    # ------------------------------------------------------------------
    @api.depends('room_ids')
    def _compute_room_count(self):
        """Count the rooms currently registered in each building."""
        for rec in self:
            rec.room_count = len(rec.room_ids)

    @api.depends('room_ids.state')
    def _compute_occupied(self):
        """Count rooms that are fully occupied (state == 'full')."""
        for rec in self:
            rec.occupied_count = len(
                rec.room_ids.filtered(lambda r: r.state == 'full'))

    # ------------------------------------------------------------------
    # Group expand for state
    # ------------------------------------------------------------------
    @api.model
    def _group_expand_states(self, states, domain, order):
        """Return all known state keys for grouping."""
        return [key for key, _label in self._fields['state'].selection]

    # ------------------------------------------------------------------
    # Workflows
    # ------------------------------------------------------------------
    def action_maintenance(self):
        """Put the building into maintenance state."""
        for rec in self:
            rec.state = 'maintenance'
            rec.message_post(body=_("Building put under maintenance."))

    def action_close(self):
        """Close the building (no longer available for housing)."""
        for rec in self:
            rec.state = 'closed'
            rec.message_post(body=_("Building closed."))

    def action_available(self):
        """Re-open the building and mark it as available."""
        for rec in self:
            rec.state = 'available'
            rec.message_post(body=_("Building marked as available."))

    # ------------------------------------------------------------------
    # Smart buttons
    # ------------------------------------------------------------------
    def action_open_rooms(self):
        """Open the room list filtered by this building."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Rooms'),
            'res_model': 'uni.housing.room',
            'view_mode': 'list,form',
            'domain': [('building_id', '=', self.id)],
            'context': {
                'default_building_id': self.id,
                'default_university_id': self.university_id.id,
            },
        }

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('branch_id', 'university_id')
    def _check_branch_belongs_to_university(self):
        """When set, branch must belong to the chosen university."""
        for rec in self:
            if rec.branch_id and rec.university_id \
                    and rec.branch_id.university_id \
                    and rec.branch_id.university_id != rec.university_id:
                raise ValidationError(_(
                    "Branch %(branch)s does not belong to university "
                    "%(univ)s.") % {
                    'branch': rec.branch_id.display_name,
                    'univ': rec.university_id.display_name,
                })

    @api.constrains('total_rooms', 'room_ids')
    def _check_total_rooms_capacity(self):
        """Warn — informational only — when registered rooms exceed total.

        This is enforced as a soft check via ValidationError to keep the
        declared capacity consistent with the actual rooms registered.
        """
        for rec in self:
            if rec.total_rooms and len(rec.room_ids) > rec.total_rooms:
                raise ValidationError(_(
                    "Building %(name)s has %(actual)d rooms registered but "
                    "declared total is only %(total)d.") % {
                    'name': rec.display_name,
                    'actual': len(rec.room_ids),
                    'total': rec.total_rooms,
                })
