# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniHousingRoomType(models.Model):
    """نوع الغرفة — يُعرّف فئة من الغرف بسعة وإيجار وخصائص موحّدة.

    يستخدم النموذج لتوحيد أوصاف الغرف داخل المباني (مفردة، مزدوجة،
    جناح، شقة...) بحيث تحمل كل غرفة مواصفات النوع المختار. كما يتيح
    عدّ الغرف المرتبطة بكل نوع لاستخدامها في التقارير ولوحات المعلومات.

    يوفّر النموذج:
        * كوداً فريداً لكل نوع غرفة
        * سعة قياسية (افتراضياً 2 سرير)
        * إيجاراً شهرياً مع العملة
        * خصائص مرافق (تكييف، مطبخ، حمام، إنترنت، أثاث)
        * عدّاد الغرف المرتبطة (محسوب)
    """
    _name = 'uni.housing.room.type'
    _description = 'Housing Room Type'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'name'

    # ------------------------------------------------------------------
    # Identification
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Room Type Name', required=True, tracking=True, translate=True,
        help='Display name of the room type (e.g. Single, Double, Suite).')
    code = fields.Char(
        string='Code', copy=False, tracking=True, index=True,
        help='Unique short code identifying the room type (e.g. SGL, DBL).')
    description = fields.Text(
        string='Description', translate=True,
        help='Detailed description of the room type and its amenities.')

    # ------------------------------------------------------------------
    # Capacity & Pricing
    # ------------------------------------------------------------------
    capacity = fields.Integer(
        string='Capacity', default=2, required=True, tracking=True,
        help='Number of beds the room can accommodate.')
    monthly_rent = fields.Float(
        string='Monthly Rent', digits=(16, 2), default=0.0, tracking=True,
        help='Monthly rental amount per bed or per room depending on policy.')
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
        help='Currency used for the monthly rent.')

    # ------------------------------------------------------------------
    # Amenities
    # ------------------------------------------------------------------
    has_ac = fields.Boolean(
        string='Air Conditioning', tracking=True,
        help='True if rooms of this type have air conditioning.')
    has_kitchen = fields.Boolean(
        string='Kitchen', tracking=True,
        help='True if rooms of this type have a private kitchen.')
    has_bathroom = fields.Boolean(
        string='Bathroom', tracking=True,
        help='True if rooms of this type have a private bathroom.')
    has_internet = fields.Boolean(
        string='Internet', tracking=True,
        help='True if rooms of this type provide internet access.')
    has_furniture = fields.Boolean(
        string='Furniture', tracking=True,
        help='True if rooms of this type come furnished.')

    # ------------------------------------------------------------------
    # Relations & Computed
    # ------------------------------------------------------------------
    room_ids = fields.One2many(
        'uni.housing.room', 'room_type_id', string='Rooms',
        help='Rooms configured with this room type.')
    room_count = fields.Integer(
        string='Room Count', compute='_compute_room_count', store=True,
        help='Number of rooms currently using this room type.')
    active = fields.Boolean(default=True, tracking=True)

    _sql_constraints = [
        ('unique_room_type_code', 'unique(code)',
         'Room type code must be unique!'),
        ('check_capacity_positive', 'check(capacity > 0)',
         'Room type capacity must be greater than zero!'),
        ('check_monthly_rent_positive', 'check(monthly_rent >= 0)',
         'Monthly rent cannot be negative!'),
    ]

    # ------------------------------------------------------------------
    # Computations
    # ------------------------------------------------------------------
    @api.depends('room_ids')
    def _compute_room_count(self):
        """Count the rooms currently linked to each room type."""
        for rec in self:
            rec.room_count = len(rec.room_ids)

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('capacity')
    def _check_capacity(self):
        """Capacity must be a positive integer (extra safety net)."""
        for rec in self:
            if rec.capacity is False or rec.capacity <= 0:
                raise ValidationError(_(
                    "Room type %(name)s capacity must be greater than "
                    "zero.") % {'name': rec.display_name})

    def _compute_display_name(self):
        """Append the code in brackets when available for clarity."""
        for rec in self:
            if rec.code:
                rec.display_name = _('%(name)s [%(code)s]') % {
                    'name': rec.name, 'code': rec.code}
            else:
                rec.display_name = rec.name
