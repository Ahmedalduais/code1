# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniClassroom(models.Model):
    """القاعة الدراسية — تمثل قاعة فعلية داخل حرم جامعي.

    ترتبط بجامعة/ذراع/كلية/قسم، وتُصنَّف بنوع، ولها سعة وتجهيزات
    وصورة وحالة (متاحة/صيانة/مشغولة). يُسمح بحجزها عبر ``uni.classroom.booking``.
    """
    _name = 'uni.classroom'
    _description = 'Classroom'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'university_id, code'

    name = fields.Char(string='Classroom Name', required=True, tracking=True, translate=True, index=True)
    code = fields.Char(string='Code', required=True, copy=False, tracking=True, index=True,
                       help='Unique code identifying this classroom within the university.')
    university_id = fields.Many2one(
        'uni.university', string='University',
        required=True, ondelete='restrict', tracking=True, index=True)
    branch_id = fields.Many2one(
        'uni.branch', string='Branch',
        ondelete='restrict', tracking=True, index=True)
    college_id = fields.Many2one(
        'uni.college', string='College',
        ondelete='restrict', tracking=True, index=True)
    department_id = fields.Many2one(
        'uni.department', string='Department',
        ondelete='restrict', tracking=True, index=True)
    classroom_type_id = fields.Many2one(
        'uni.classroom.type', string='Classroom Type',
        required=True, ondelete='restrict', tracking=True, index=True)

    # Capacity is stored directly so each classroom can override the type's default
    capacity = fields.Integer(string='Capacity', tracking=True,
                              help='Number of seats available in this classroom.')
    classroom_type_capacity = fields.Integer(
        string='Type Default Capacity',
        related='classroom_type_id.capacity', store=False, readonly=True)

    # Location details
    building = fields.Char(string='Building', tracking=True)
    floor = fields.Char(string='Floor', tracking=True)
    room_number = fields.Char(string='Room Number', tracking=True)

    # Facilities free-text (the structured flags live on the type)
    facilities = fields.Text(string='Facilities',
                             help='Additional notes about available facilities and equipment.')
    photo = fields.Image(string='Photo')

    # State
    state = fields.Selection([
        ('available', 'Available'),
        ('maintenance', 'Under Maintenance'),
        ('occupied', 'Occupied'),
    ], string='Status', default='available', tracking=True, index=True,
        group_expand='_group_expand_states')

    # Relations
    booking_ids = fields.One2many(
        'uni.classroom.booking', 'classroom_id', string='Bookings')
    booking_count = fields.Integer(
        compute='_compute_booking_count', string='Bookings')
    active_booking_count = fields.Integer(
        compute='_compute_booking_count', string='Active Bookings')

    _sql_constraints = [
        ('unique_classroom_code_university',
         'unique(university_id, code)',
         'Classroom code must be unique per university!'),
        ('check_capacity_positive', 'check(capacity >= 0)',
         'Capacity must be positive or zero!'),
    ]

    # ------------------------------------------------------------------
    # Lifecycle / group expand
    # ------------------------------------------------------------------
    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in states]

    # ------------------------------------------------------------------
    # Computed
    # ------------------------------------------------------------------
    @api.depends('booking_ids.state')
    def _compute_booking_count(self):
        for rec in self:
            rec.booking_count = len(rec.booking_ids)
            rec.active_booking_count = len(
                rec.booking_ids.filtered(
                    lambda b: b.state in ('draft', 'confirmed')))

    # ------------------------------------------------------------------
    # Onchange helpers — keep hierarchy consistent
    # ------------------------------------------------------------------
    @api.onchange('college_id')
    def _onchange_college_id(self):
        if self.college_id:
            self.university_id = self.college_id.university_id
            self.branch_id = self.college_id.branch_id

    @api.onchange('department_id')
    def _onchange_department_id(self):
        if self.department_id:
            self.college_id = self.department_id.college_id
            self.university_id = self.department_id.university_id
            self.branch_id = self.department_id.branch_id or self.college_id.branch_id

    @api.onchange('classroom_type_id')
    def _onchange_classroom_type_id(self):
        """When picking a type, suggest its default capacity if not yet set."""
        if self.classroom_type_id and not self.capacity:
            self.capacity = self.classroom_type_id.capacity

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_maintenance(self):
        """وضع القاعة في حالة الصيانة (غير متاحة للحجز)."""
        for rec in self:
            rec.state = 'maintenance'

    def action_available(self):
        """إعادة القاعة إلى حالة الإتاحة."""
        for rec in self:
            rec.state = 'available'

    # ------------------------------------------------------------------
    # Smart-button
    # ------------------------------------------------------------------
    def action_open_bookings(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Classroom Bookings'),
            'res_model': 'uni.classroom.booking',
            'view_mode': 'list,form,calendar',
            'domain': [('classroom_id', '=', self.id)],
            'context': {'default_classroom_id': self.id},
        }

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('capacity')
    def _check_capacity(self):
        for rec in self:
            if rec.capacity < 0:
                raise ValidationError(_(
                    'Classroom %s capacity cannot be negative.') % rec.display_name)
