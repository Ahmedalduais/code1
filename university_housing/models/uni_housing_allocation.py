# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class UniHousingAllocation(models.Model):
    """التخصيص — تسجيل تخصيص غرفة لطالب جامعي.

    يحتوي النموذج على معلومات تخصيص الغرفة للطالب (الطالب، الغرفة،
    المبنى، الجامعة، تواريخ الدخول والخروج المتوقع والفعلي، الإيجار
    الشهري، العقد المرتبط اختيارياً) ويدير سير عمل التخصيص من المسودة
    إلى النشاط ثم الإكمال أو الإلغاء.

    يوفّر النموذج:
        * توليد رقم تسلسلي تلقائي HAL/%(year)s/00000
        * منع التخصيص النشط المكرر للطالب نفسه (عبر @api.constrains)
        * ربط تلقائي بالمبنى والجامعة من الغرفة المختارة
        * حساب الإيجار الشهري افتراضياً من الغرفة (عبر onchange)
        * سير عمل: مسودة → نشط → مكتمل → ملغى
    """
    _name = 'uni.housing.allocation'
    _description = 'Housing Allocation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'allocation_date desc, id desc'

    # ------------------------------------------------------------------
    # Identification
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True,
        default='New', tracking=True, index=True,
        help='Unique sequence reference of the allocation.')
    code = fields.Char(
        string='Code', copy=False, tracking=True, index=True,
        help='Optional secondary code for manual lookups.')

    # ------------------------------------------------------------------
    # Student & Room
    # ------------------------------------------------------------------
    student_id = fields.Many2one(
        'uni.student', string='Student', required=True,
        ondelete='restrict', tracking=True, index=True,
        help='Student to whom the room is being allocated.')
    room_id = fields.Many2one(
        'uni.housing.room', string='Room', required=True,
        ondelete='restrict', tracking=True, index=True,
        help='Room allocated to the student.')
    building_id = fields.Many2one(
        'uni.housing.building', string='Building',
        related='room_id.building_id', store=True, index=True,
        help='Building containing the room (inherited from the room).')
    university_id = fields.Many2one(
        'uni.university', string='University',
        related='room_id.building_id.university_id', store=True, index=True,
        help='University that owns the room (inherited from the building).')

    # ------------------------------------------------------------------
    # Dates
    # ------------------------------------------------------------------
    allocation_date = fields.Date(
        string='Allocation Date', required=True,
        default=fields.Date.context_today, tracking=True,
        help='Date on which the allocation was created/approved.')
    check_in_date = fields.Date(
        string='Check-in Date', tracking=True,
        help='Actual date the student moved into the room.')
    expected_check_out_date = fields.Date(
        string='Expected Check-out Date', tracking=True,
        help='Planned date the student is expected to leave the room.')
    actual_check_out_date = fields.Date(
        string='Actual Check-out Date', tracking=True,
        help='Actual date the student left the room.')

    # ------------------------------------------------------------------
    # Pricing
    # ------------------------------------------------------------------
    monthly_rent = fields.Float(
        string='Monthly Rent', digits=(16, 2), default=0.0, tracking=True,
        help='Monthly rental amount agreed for this allocation '
             '(defaults from the room type).')
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
        help='Currency for the monthly rent.')

    # ------------------------------------------------------------------
    # Contract & State
    # ------------------------------------------------------------------
    contract_id = fields.Many2one(
        'uni.housing.contract', string='Contract',
        ondelete='set null', copy=False,
        help='Optional housing contract linked to this allocation.')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='State', default='draft', required=True,
        tracking=True, index=True, group_expand='_group_expand_states',
        help='Lifecycle state of the allocation.')
    notes = fields.Text(
        string='Notes', translate=True,
        help='Internal notes about this allocation.')

    _sql_constraints = [
        ('unique_allocation_name', 'unique(name)',
         'Allocation reference must be unique!'),
    ]

    # ------------------------------------------------------------------
    # Create — auto sequence
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        """Auto-generate the sequence reference for each new allocation."""
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.housing.allocation') or 'New'
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Onchange
    # ------------------------------------------------------------------
    @api.onchange('room_id')
    def _onchange_room_id(self):
        """Default the monthly rent and currency from the chosen room."""
        if self.room_id:
            if not self.monthly_rent:
                self.monthly_rent = self.room_id.monthly_rent
            if self.room_id.currency_id:
                self.currency_id = self.room_id.currency_id

    # ------------------------------------------------------------------
    # Group expand
    # ------------------------------------------------------------------
    @api.model
    def _group_expand_states(self, states, domain, order):
        """Return all known state keys for grouping."""
        return [key for key, _label in self._fields['state'].selection]

    # ------------------------------------------------------------------
    # Workflows
    # ------------------------------------------------------------------
    def action_check_in(self):
        """Activate the allocation and record the check-in date."""
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_(
                    "Allocation %(name)s cannot be checked in from state "
                    "%(state)s.") % {
                    'name': rec.name, 'state': rec.state,
                })
            if not rec.check_in_date:
                rec.check_in_date = fields.Date.context_today(rec)
            rec.state = 'active'
            rec.message_post(body=_(
                "Student checked in on %(date)s.") % {
                'date': rec.check_in_date,
            })
            # Refresh occupancy and synchronise the room state
            rec.room_id._compute_occupied()
            rec.room_id._compute_available()
            rec.room_id._synchronise_room_state()

    def action_check_out(self):
        """Complete the allocation and record the actual check-out date."""
        for rec in self:
            if rec.state != 'active':
                raise UserError(_(
                    "Allocation %(name)s cannot be checked out from state "
                    "%(state)s.") % {
                    'name': rec.name, 'state': rec.state,
                })
            rec.actual_check_out_date = fields.Date.context_today(rec)
            rec.state = 'completed'
            rec.message_post(body=_(
                "Student checked out on %(date)s.") % {
                'date': rec.actual_check_out_date,
            })
            # Refresh occupancy and synchronise the room state
            rec.room_id._compute_occupied()
            rec.room_id._compute_available()
            rec.room_id._synchronise_room_state()

    def action_cancel(self):
        """Cancel the allocation (only from draft or active states)."""
        affected_rooms = self.env['uni.housing.room']
        for rec in self:
            if rec.state not in ('draft', 'active'):
                raise UserError(_(
                    "Allocation %(name)s cannot be cancelled from state "
                    "%(state)s.") % {
                    'name': rec.name, 'state': rec.state,
                })
            if rec.state == 'active' and rec.room_id:
                affected_rooms |= rec.room_id
            rec.state = 'cancelled'
            rec.message_post(body=_("Allocation cancelled."))
        # Refresh occupancy and synchronise the affected rooms' states
        if affected_rooms:
            affected_rooms._compute_occupied()
            affected_rooms._compute_available()
            affected_rooms._synchronise_room_state()

    def action_draft(self):
        """Reset the allocation back to draft state."""
        for rec in self:
            if rec.state == 'cancelled':
                rec.state = 'draft'
                rec.message_post(body=_("Allocation reset to draft."))

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('student_id', 'state')
    def _check_unique_active_allocation(self):
        """A student cannot have more than one draft or active allocation.

        This is the SQL-constraint equivalent required by the specification,
        implemented via Python because PostgreSQL unique constraints cannot
        include a WHERE clause to filter by state.
        """
        for rec in self:
            if rec.state in ('draft', 'active'):
                domain = [
                    ('student_id', '=', rec.student_id.id),
                    ('state', 'in', ('draft', 'active')),
                    ('id', '!=', rec.id),
                ]
                if self.search_count(domain) > 0:
                    raise ValidationError(_(
                        "Student %(student)s already has an active or draft "
                        "allocation. Please complete or cancel it before "
                        "creating a new one.") % {
                        'student': rec.student_id.display_name,
                    })

    @api.constrains('room_id', 'state')
    def _check_room_capacity(self):
        """Active allocations for a room cannot exceed its capacity."""
        for rec in self:
            if rec.state == 'active':
                active_count = self.search_count([
                    ('room_id', '=', rec.room_id.id),
                    ('state', '=', 'active'),
                    ('id', '!=', rec.id),
                ])
                capacity = rec.room_id.capacity or 0
                if capacity > 0 and active_count >= capacity:
                    raise ValidationError(_(
                        "Room %(room)s has reached its capacity of "
                        "%(cap)d beds. Cannot allocate another student.") % {
                        'room': rec.room_id.display_name,
                        'cap': capacity,
                    })

    @api.constrains('check_in_date', 'allocation_date')
    def _check_check_in_after_allocation(self):
        """Check-in date must be on or after the allocation date."""
        for rec in self:
            if rec.check_in_date and rec.allocation_date \
                    and rec.check_in_date < rec.allocation_date:
                raise ValidationError(_(
                    "Check-in date (%(in)s) cannot be before allocation date "
                    "(%(alloc)s) for allocation %(name)s.") % {
                    'in': rec.check_in_date,
                    'alloc': rec.allocation_date,
                    'name': rec.name,
                })

    @api.constrains('expected_check_out_date', 'check_in_date')
    def _check_expected_check_out_after_check_in(self):
        """Expected check-out date must be on or after the check-in date."""
        for rec in self:
            if rec.expected_check_out_date and rec.check_in_date \
                    and rec.expected_check_out_date < rec.check_in_date:
                raise ValidationError(_(
                    "Expected check-out date (%(out)s) cannot be before "
                    "check-in date (%(in)s) for allocation %(name)s.") % {
                    'out': rec.expected_check_out_date,
                    'in': rec.check_in_date,
                    'name': rec.name,
                })

    @api.constrains('actual_check_out_date', 'check_in_date')
    def _check_actual_check_out_after_check_in(self):
        """Actual check-out date must be on or after the check-in date."""
        for rec in self:
            if rec.actual_check_out_date and rec.check_in_date \
                    and rec.actual_check_out_date < rec.check_in_date:
                raise ValidationError(_(
                    "Actual check-out date (%(out)s) cannot be before "
                    "check-in date (%(in)s) for allocation %(name)s.") % {
                    'out': rec.actual_check_out_date,
                    'in': rec.check_in_date,
                    'name': rec.name,
                })
