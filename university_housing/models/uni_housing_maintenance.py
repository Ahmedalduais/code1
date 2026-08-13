# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class UniHousingMaintenance(models.Model):
    """الصيانة — طلب صيانة لمبنى أو غرفة في السكن الجامعي.

    يحتوي النموذج على بيانات طلب الصيانة (المبنى/الغرفة، المُبلِّغ،
    نوع الصيانة، الأولوية، الوصف، الفني المُكلِّف، التواريخ، التكلفة،
    قطع الغيار، وصف العمل، التقييم، الملاحظات) ويدير سير عمل الصيانة
    الكامل من الإنشاء حتى الإكمال أو الإلغاء.

    يوفّر النموذج:
        * توليد رقم تسلسلي تلقائي HMN/%(year)s/00000
        * تصنيف الصيانة (كهرباء/سباكة/نجارة/دهان/تكييف/تنظيف/إنشائي/أخرى)
        * أولويات (منخفضة/عادية/عالية/عاجلة)
        * تتبع كامل للفني المُكلِّف والتواريخ (الجدولة/البدء/الإكمال)
        * تكلفة الصيانة وقطع الغيار المستخدمة ووصف العمل المنجز
        * تقييم رضا الطالب/المشرف (1-5) مع ملاحظات
        * سير عمل: جديد → مُكلّف → مجدول → قيد التنفيذ → مكتمل/ملغى
    """
    _name = 'uni.housing.maintenance'
    _description = 'Housing Maintenance Request'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'reported_date desc, id desc'

    # ------------------------------------------------------------------
    # Identification
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True,
        default='New', tracking=True, index=True,
        help='Unique sequence reference of the maintenance request.')
    code = fields.Char(
        string='Code', copy=False, tracking=True, index=True,
        help='Optional secondary code for manual lookups.')

    # ------------------------------------------------------------------
    # Location
    # ------------------------------------------------------------------
    building_id = fields.Many2one(
        'uni.housing.building', string='Building',
        ondelete='restrict', tracking=True, index=True,
        help='Building where the maintenance issue is located.')
    room_id = fields.Many2one(
        'uni.housing.room', string='Room',
        ondelete='restrict', tracking=True, index=True,
        domain="[('building_id', '=', building_id)]",
        help='Specific room where the maintenance issue is located '
             '(optional).')

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------
    reported_by = fields.Many2one(
        'res.users', string='Reported By', tracking=True, index=True,
        default=lambda self: self.env.uid,
        help='User who reported the maintenance issue.')
    reported_date = fields.Datetime(
        string='Reported Date', required=True,
        default=fields.Datetime.now, tracking=True,
        help='Date and time the issue was reported.')

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------
    maintenance_type = fields.Selection([
        ('electrical', 'Electrical'),
        ('plumbing', 'Plumbing'),
        ('carpentry', 'Carpentry'),
        ('painting', 'Painting'),
        ('hvac', 'HVAC / AC'),
        ('cleaning', 'Cleaning'),
        ('structural', 'Structural'),
        ('other', 'Other'),
    ], string='Maintenance Type', default='other', required=True,
        tracking=True, index=True,
        help='Category of the maintenance work required.')
    priority = fields.Selection([
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ], string='Priority', default='normal', required=True,
        tracking=True, index=True,
        help='Priority of the maintenance request.')
    description = fields.Text(
        string='Description', required=True, translate=True,
        help='Detailed description of the issue reported.')

    # ------------------------------------------------------------------
    # Assignment & Scheduling
    # ------------------------------------------------------------------
    assigned_to = fields.Many2one(
        'res.users', string='Assigned To', tracking=True, index=True,
        help='Technician or staff member assigned to perform the work.')
    scheduled_date = fields.Datetime(
        string='Scheduled Date', tracking=True,
        help='Date and time the work is scheduled to start.')
    started_date = fields.Datetime(
        string='Started Date', tracking=True,
        help='Date and time the work actually started.')
    completed_date = fields.Datetime(
        string='Completed Date', tracking=True,
        help='Date and time the work was completed.')

    # ------------------------------------------------------------------
    # Cost & Work
    # ------------------------------------------------------------------
    cost = fields.Float(
        string='Cost', digits=(16, 2), default=0.0, tracking=True,
        help='Total cost of the maintenance work.')
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
        help='Currency used for the maintenance cost.')
    parts_used = fields.Text(
        string='Parts Used', translate=True,
        help='List of spare parts used during the maintenance work.')
    work_description = fields.Text(
        string='Work Description', translate=True,
        help='Detailed description of the work performed.')

    # ------------------------------------------------------------------
    # State & Feedback
    # ------------------------------------------------------------------
    state = fields.Selection([
        ('new', 'New'),
        ('assigned', 'Assigned'),
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='State', default='new', required=True,
        tracking=True, index=True, group_expand='_group_expand_states',
        help='Lifecycle state of the maintenance request.')
    rating = fields.Integer(
        string='Rating',
        help='Satisfaction rating from 1 (worst) to 5 (best).')
    feedback = fields.Text(
        string='Feedback', translate=True,
        help='Optional feedback or comment about the maintenance service.')
    notes = fields.Text(
        string='Notes', translate=True,
        help='Internal notes about this maintenance request.')
    active = fields.Boolean(default=True, tracking=True)

    _sql_constraints = [
        ('unique_maintenance_name', 'unique(name)',
         'Maintenance reference must be unique!'),
        ('check_cost_positive', 'check(cost >= 0)',
         'Cost cannot be negative!'),
        ('check_rating_range', 'check(rating >= 0 and rating <= 5)',
         'Rating must be between 0 (unrated) and 5!'),
    ]

    # ------------------------------------------------------------------
    # Create — auto sequence
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        """Auto-generate the sequence reference for each new request."""
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.housing.maintenance') or 'New'
        return super().create(vals_list)

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
    def action_assign(self):
        """Assign the request to a technician (state: new → assigned)."""
        for rec in self:
            if rec.state != 'new':
                raise UserError(_(
                    "Maintenance request %(name)s cannot be assigned from "
                    "state %(state)s.") % {
                    'name': rec.name, 'state': rec.state,
                })
            if not rec.assigned_to:
                raise UserError(_(
                    "Please set the 'Assigned To' technician before "
                    "assigning request %(name)s.") % {'name': rec.name})
            rec.state = 'assigned'
            rec.message_post(body=_(
                "Request assigned to %(user)s.") % {
                'user': rec.assigned_to.display_name,
            })

    def action_schedule(self):
        """Schedule the request for a specific date (state → scheduled)."""
        for rec in self:
            if rec.state not in ('new', 'assigned'):
                raise UserError(_(
                    "Maintenance request %(name)s cannot be scheduled from "
                    "state %(state)s.") % {
                    'name': rec.name, 'state': rec.state,
                })
            if not rec.scheduled_date:
                raise UserError(_(
                    "Please set the 'Scheduled Date' before scheduling "
                    "request %(name)s.") % {'name': rec.name})
            if not rec.assigned_to:
                raise UserError(_(
                    "Please assign a technician before scheduling request "
                    "%(name)s.") % {'name': rec.name})
            rec.state = 'scheduled'
            rec.message_post(body=_(
                "Request scheduled for %(date)s.") % {
                'date': rec.scheduled_date,
            })

    def action_start(self):
        """Start the maintenance work (state → in_progress)."""
        for rec in self:
            if rec.state not in ('assigned', 'scheduled'):
                raise UserError(_(
                    "Maintenance request %(name)s cannot be started from "
                    "state %(state)s.") % {
                    'name': rec.name, 'state': rec.state,
                })
            rec.started_date = fields.Datetime.now()
            rec.state = 'in_progress'
            rec.message_post(body=_("Maintenance work started."))

    def action_complete(self):
        """Complete the maintenance work (state → completed)."""
        for rec in self:
            if rec.state != 'in_progress':
                raise UserError(_(
                    "Maintenance request %(name)s cannot be completed from "
                    "state %(state)s.") % {
                    'name': rec.name, 'state': rec.state,
                })
            rec.completed_date = fields.Datetime.now()
            rec.state = 'completed'
            rec.message_post(body=_("Maintenance work completed."))

    def action_cancel(self):
        """Cancel the maintenance request."""
        for rec in self:
            if rec.state == 'completed':
                raise UserError(_(
                    "Cannot cancel a completed maintenance request "
                    "(%(name)s).") % {'name': rec.name})
            rec.state = 'cancelled'
            rec.message_post(body=_("Maintenance request cancelled."))

    def action_draft(self):
        """Reset a cancelled request back to new state."""
        for rec in self:
            if rec.state == 'cancelled':
                rec.state = 'new'
                rec.message_post(body=_("Maintenance request reset to new."))

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('building_id', 'room_id')
    def _check_room_belongs_to_building(self):
        """When both are set, room must belong to the chosen building."""
        for rec in self:
            if rec.building_id and rec.room_id \
                    and rec.room_id.building_id != rec.building_id:
                raise UserError(_(
                    "Room %(room)s does not belong to building "
                    "%(building)s.") % {
                    'room': rec.room_id.display_name,
                    'building': rec.building_id.display_name,
                })

    @api.constrains('scheduled_date', 'started_date', 'completed_date')
    def _check_chronology(self):
        """Started date must be on/after scheduled, completed after started."""
        for rec in self:
            if rec.scheduled_date and rec.started_date \
                    and rec.started_date < rec.scheduled_date:
                raise UserError(_(
                    "Started date cannot be before scheduled date for "
                    "request %(name)s.") % {'name': rec.name})
            if rec.started_date and rec.completed_date \
                    and rec.completed_date < rec.started_date:
                raise UserError(_(
                    "Completed date cannot be before started date for "
                    "request %(name)s.") % {'name': rec.name})

    @api.constrains('rating')
    def _check_rating(self):
        """Rating must be in [0, 5] where 0 means unrated."""
        for rec in self:
            if rec.rating is False or rec.rating < 0 or rec.rating > 5:
                raise UserError(_(
                    "Rating for request %(name)s must be between 0 (unrated) "
                    "and 5.") % {'name': rec.name})
