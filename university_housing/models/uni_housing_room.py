# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class UniHousingRoom(models.Model):
    """الغرفة — تمثل غرفة واحدة داخل مبنى سكني جامعي.

    يحتوي النموذج على معلومات الغرفة (الاسم/الرقم، الكود، المبنى،
    النوع، الطابق، السعة، الإيجار) ويحسب عدد الأسرة المشغولة والمتاحة
    تلقائياً من سجلات التخصيص النشطة.

    يوفّر النموذج:
        * كوداً فريداً لكل مبنى (unique per building)
        * السعة والإيجار موروثة من نوع الغرفة (related)
        * حساب occupied_beds و available_beds تلقائياً
        * سير عمل حالة: متاح → ممتلئ/صيانة → متاح
        * ربط مع التخصيصات عبر One2many
    """
    _name = 'uni.housing.room'
    _description = 'Housing Room'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'building_id, floor, name'

    # ------------------------------------------------------------------
    # Identification
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Room Number', required=True, tracking=True,
        help='Display name/number of the room (e.g. 101, 102A).')
    code = fields.Char(
        string='Code', copy=False, tracking=True, index=True,
        help='Unique code identifying the room within its building '
             '(e.g. 101, B-101).')

    # ------------------------------------------------------------------
    # Building & Type
    # ------------------------------------------------------------------
    building_id = fields.Many2one(
        'uni.housing.building', string='Building', required=True,
        ondelete='restrict', tracking=True, index=True,
        help='Building that contains this room.')
    university_id = fields.Many2one(
        'uni.university', string='University',
        related='building_id.university_id', store=True, index=True,
        help='University that owns the room (inherited from the building).')
    room_type_id = fields.Many2one(
        'uni.housing.room.type', string='Room Type', required=True,
        ondelete='restrict', tracking=True, index=True,
        help='Room type defining capacity, rent, and amenities.')
    floor = fields.Integer(
        string='Floor', default=1, tracking=True,
        help='Floor number on which the room is located.')

    # ------------------------------------------------------------------
    # Capacity & Pricing (related from room type)
    # ------------------------------------------------------------------
    capacity = fields.Integer(
        string='Capacity', related='room_type_id.capacity', store=True,
        readonly=True, tracking=True,
        help='Maximum number of beds (inherited from the room type).')
    monthly_rent = fields.Float(
        string='Monthly Rent', related='room_type_id.monthly_rent',
        store=True, readonly=True, digits=(16, 2),
        help='Monthly rental amount (inherited from the room type).')
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        related='room_type_id.currency_id', store=True, readonly=True,
        help='Currency of the monthly rent (inherited from the room type).')

    # ------------------------------------------------------------------
    # Occupancy (computed)
    # ------------------------------------------------------------------
    occupied_beds = fields.Integer(
        string='Occupied Beds', compute='_compute_occupied', store=True,
        help='Number of beds currently allocated to students.')
    available_beds = fields.Integer(
        string='Available Beds', compute='_compute_available', store=True,
        help='Number of beds still available for new allocations.')

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------
    state = fields.Selection([
        ('available', 'Available'),
        ('full', 'Full'),
        ('maintenance', 'Maintenance'),
        ('closed', 'Closed'),
    ], string='State', default='available', required=True,
        tracking=True, index=True, group_expand='_group_expand_states',
        help='Lifecycle state of the room record.')

    # ------------------------------------------------------------------
    # Relations & Media
    # ------------------------------------------------------------------
    allocation_ids = fields.One2many(
        'uni.housing.allocation', 'room_id', string='Allocations',
        help='Allocation records linked to this room.')
    photo = fields.Image(
        string='Room Photo', max_width=1024, max_height=1024,
        help='Photo of the room interior.')
    notes = fields.Text(
        string='Notes', translate=True,
        help='Internal notes about this room.')
    active = fields.Boolean(default=True, tracking=True)

    _sql_constraints = [
        ('unique_room_code_per_building',
         'unique(building_id, code)',
         'Room code must be unique per building!'),
        ('check_floor_positive', 'check(floor >= 0)',
         'Floor number cannot be negative!'),
    ]

    # ------------------------------------------------------------------
    # Computations
    # ------------------------------------------------------------------
    @api.depends('allocation_ids.state')
    def _compute_occupied(self):
        """Count active allocations as occupied beds.

        Active allocations are those in 'active' state (student currently
        living in the room).
        """
        for rec in self:
            active = rec.allocation_ids.filtered(
                lambda a: a.state == 'active')
            rec.occupied_beds = len(active)

    @api.depends('occupied_beds', 'capacity', 'state')
    def _compute_available(self):
        """Available beds = capacity - occupied_beds (clamped to 0).

        When the room is in maintenance or closed, available beds are
        always reported as 0 regardless of capacity.
        """
        for rec in self:
            if rec.state in ('maintenance', 'closed'):
                rec.available_beds = 0
            else:
                available = (rec.capacity or 0) - rec.occupied_beds
                rec.available_beds = max(available, 0)

    def _synchronise_room_state(self):
        """Synchronise the room state with its occupancy.

        Called by ``uni.housing.allocation`` workflow methods after a
        check-in or check-out so that rooms automatically flip between
        ``available`` and ``full`` based on their occupied beds. Rooms
        in maintenance or closed states are left untouched.
        """
        for rec in self:
            if rec.state not in ('available', 'full'):
                continue
            capacity = rec.capacity or 0
            if capacity > 0 and rec.occupied_beds >= capacity:
                if rec.state != 'full':
                    rec.state = 'full'
                    rec.message_post(body=_(
                        "Room marked as FULL (all %(n)d beds occupied).") % {
                        'n': capacity,
                    })
            elif rec.occupied_beds < capacity:
                if rec.state != 'available':
                    rec.state = 'available'
                    rec.message_post(body=_(
                        "Room marked as AVAILABLE (%(occ)d/%(cap)d beds "
                        "occupied).") % {
                        'occ': rec.occupied_beds,
                        'cap': capacity,
                    })

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
        """Put the room into maintenance state."""
        for rec in self:
            if rec.occupied_beds > 0:
                raise UserError(_(
                    "Cannot put room %(room)s into maintenance while it has "
                    "%(n)d active allocation(s). Please check out the "
                    "students first.") % {
                    'room': rec.display_name,
                    'n': rec.occupied_beds,
                })
            rec.state = 'maintenance'
            rec.message_post(body=_("Room put under maintenance."))

    def action_available(self):
        """Mark the room as available again.

        After setting the state, the room's available_beds is recomputed
        automatically (because ``available_beds`` depends on ``state``).
        The occupancy is then synchronised so that the room returns to
        ``full`` if it is still fully occupied.
        """
        for rec in self:
            rec.state = 'available'
            rec.message_post(body=_("Room marked as available."))
            rec._synchronise_room_state()

    # ------------------------------------------------------------------
    # Smart buttons
    # ------------------------------------------------------------------
    def action_open_allocations(self):
        """Open the allocation history for this room."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Allocations'),
            'res_model': 'uni.housing.allocation',
            'view_mode': 'list,form',
            'domain': [('room_id', '=', self.id)],
            'context': {
                'default_room_id': self.id,
                'default_building_id': self.building_id.id,
                'default_university_id': self.university_id.id,
            },
        }
