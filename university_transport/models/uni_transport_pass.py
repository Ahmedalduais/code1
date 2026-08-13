# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class UniTransportPass(models.Model):
    """بطاقة النقل — اشتراك طالب في خط نقل جامعي.

    تصدّر البطاقة لطالب على خط معين لفترة زمنية محددة بنوع من
    الاشتراكات (فصلي/سنوي/شهري/ذهاب فقط/ذهاب وعودة). تحمل البطاقة
    محطة الركوب ومحطة الإنزال، ومبلغ الاشتراك ومدفوعيته، وباركود
    وصورة الطالب. يتم تسجيل الاستخدام بعدّاد وآخر استخدام.

    تتوفّر البطاقة في خمس حالات (مسودة/نشطة/منتهية/معلقة/ملغاة)
    مع workflow كامل عبر أزرار الإجراءات.
    """
    _name = 'uni.transport.pass'
    _description = 'University Transport Pass'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'university_id, route_id, student_id, start_date desc'

    # ------------------------------------------------------------------
    # Identification
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True,
        default='New', tracking=True, index=True,
        help='Unique sequence reference of the pass (TPS/...).')
    code = fields.Char(
        string='Code', copy=False, tracking=True, index=True,
        help='Optional secondary code for manual lookups.')

    # ------------------------------------------------------------------
    # Student & university
    # ------------------------------------------------------------------
    student_id = fields.Many2one(
        'uni.student', string='Student', required=True,
        ondelete='restrict', tracking=True, index=True,
        help='Student to whom this transport pass is issued.')
    university_id = fields.Many2one(
        'uni.university', string='University',
        related='student_id.university_id', store=True, index=True,
        help='University of the student (related from student).')
    student_name = fields.Char(
        string='Student Name',
        related='student_id.display_name', store=False,
        help='Display name of the student (for quick reference).')

    # ------------------------------------------------------------------
    # Route & stops
    # ------------------------------------------------------------------
    route_id = fields.Many2one(
        'uni.transport.route', string='Route', required=True,
        ondelete='restrict', tracking=True, index=True,
        domain="[('university_id', '=', university_id)]",
        help='Route on which this pass is valid.')
    pickup_stop_id = fields.Many2one(
        'uni.transport.stop', string='Pickup Stop',
        ondelete='restrict', tracking=True, index=True,
        domain="[('route_id', '=', route_id), ('is_pickup_point', '=', True)]",
        help='Stop where the student is picked up.')
    drop_stop_id = fields.Many2one(
        'uni.transport.stop', string='Drop Stop',
        ondelete='restrict', tracking=True, index=True,
        domain="[('route_id', '=', route_id), ('is_drop_point', '=', True)]",
        help='Stop where the student is dropped off.')

    # ------------------------------------------------------------------
    # Subscription
    # ------------------------------------------------------------------
    pass_type = fields.Selection([
        ('semester', 'Semester'),
        ('annual', 'Annual'),
        ('monthly', 'Monthly'),
        ('one_way', 'One Way'),
        ('round_trip', 'Round Trip'),
    ], string='Pass Type', default='semester', required=True,
        tracking=True, index=True,
        help='Type of transport subscription.')
    issue_date = fields.Date(
        string='Issue Date', default=fields.Date.context_today,
        tracking=True,
        help='Date the pass was issued.')
    start_date = fields.Date(
        string='Start Date', required=True, tracking=True,
        help='First day the pass is valid.')
    end_date = fields.Date(
        string='End Date', required=True, tracking=True,
        help='Last day the pass is valid.')

    # ------------------------------------------------------------------
    # Pricing
    # ------------------------------------------------------------------
    amount = fields.Float(
        string='Amount', digits=(16, 2), tracking=True,
        help='Subscription amount paid (or to be paid) for this pass.')
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
        help='Currency of the subscription amount.')
    paid = fields.Boolean(
        string='Paid', default=False, tracking=True,
        help='True if the subscription amount has been paid.')

    # ------------------------------------------------------------------
    # Identification & media
    # ------------------------------------------------------------------
    barcode = fields.Char(
        string='Barcode', copy=False, index=True,
        help='Barcode used by the bus scanners to validate the pass.')
    photo = fields.Image(
        string='Photo', related='student_id.photo', store=False,
        help='Photo of the student (related from student record).')

    # ------------------------------------------------------------------
    # Usage tracking
    # ------------------------------------------------------------------
    usage_count = fields.Integer(
        string='Usage Count', default=0, tracking=True,
        help='Number of times this pass has been used.')
    last_used_date = fields.Datetime(
        string='Last Used Date', copy=False, tracking=True,
        help='Date and time of the last recorded usage of this pass.')

    # ------------------------------------------------------------------
    # State & notes
    # ------------------------------------------------------------------
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('suspended', 'Suspended'),
        ('cancelled', 'Cancelled'),
    ], string='State', default='draft', required=True,
        tracking=True, index=True, group_expand='_group_expand_states',
        help='Lifecycle state of the pass.')
    notes = fields.Text(
        string='Notes', translate=True,
        help='Internal notes about this pass.')

    _sql_constraints = [
        ('unique_pass_name',
         'unique(name)',
         'Pass reference must be unique!'),
        ('unique_pass_barcode',
         'unique(barcode)',
         'Pass barcode must be unique!'),
        ('check_amount_positive',
         'CHECK(amount >= 0)',
         'Pass amount cannot be negative!'),
    ]

    # ------------------------------------------------------------------
    # Create — auto sequence
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        """Auto-generate the TPS sequence reference for each new pass."""
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.transport.pass') or 'New'
        return super().create(vals_list)

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
        """Activate the pass so it can be used for transport."""
        for rec in self:
            if rec.state not in ('draft', 'suspended'):
                raise UserError(_(
                    "Pass %(name)s cannot be activated from state "
                    "%(state)s.") % {
                    'name': rec.name,
                    'state': rec.state,
                })
            rec.state = 'active'
            rec.message_post(body=_(
                "Pass %(name)s activated for student %(student)s.") % {
                'name': rec.name,
                'student': rec.student_id.display_name,
            })

    def action_suspend(self):
        """Temporarily suspend the pass."""
        for rec in self:
            if rec.state != 'active':
                raise UserError(_(
                    "Only active passes can be suspended. Pass %(name)s is "
                    "%(state)s.") % {
                    'name': rec.name,
                    'state': rec.state,
                })
            rec.state = 'suspended'
            rec.message_post(body=_(
                "Pass %(name)s suspended.") % {'name': rec.name})

    def action_expire(self):
        """Mark the pass as expired (end of subscription period)."""
        for rec in self:
            if rec.state in ('expired', 'cancelled'):
                raise UserError(_(
                    "Pass %(name)s is already %(state)s.") % {
                    'name': rec.name,
                    'state': rec.state,
                })
            rec.state = 'expired'
            rec.message_post(body=_(
                "Pass %(name)s expired.") % {'name': rec.name})

    def action_cancel(self):
        """Cancel the pass permanently."""
        for rec in self:
            if rec.state == 'cancelled':
                raise UserError(_(
                    "Pass %(name)s is already cancelled.") % {
                    'name': rec.name})
            rec.state = 'cancelled'
            rec.message_post(body=_(
                "Pass %(name)s cancelled.") % {'name': rec.name})

    def action_record_usage(self):
        """Record a single usage of the pass.

        Increments the usage counter, stores the current timestamp, and
        posts a message on the pass chatter.
        """
        for rec in self:
            if rec.state != 'active':
                raise UserError(_(
                    "Cannot record usage for pass %(name)s in state "
                    "%(state)s. Only active passes can be used.") % {
                    'name': rec.name,
                    'state': rec.state,
                })
            today = fields.Date.context_today(rec)
            if rec.start_date and today < rec.start_date:
                raise UserError(_(
                    "Pass %(name)s is not yet valid (starts on %(start)s).") % {
                    'name': rec.name,
                    'start': rec.start_date,
                })
            if rec.end_date and today > rec.end_date:
                raise UserError(_(
                    "Pass %(name)s has expired (ended on %(end)s). Please "
                    "renew it before recording usage.") % {
                    'name': rec.name,
                    'end': rec.end_date,
                })
            rec.usage_count = (rec.usage_count or 0) + 1
            rec.last_used_date = fields.Datetime.now()
            rec.message_post(body=_(
                "Usage recorded for pass %(name)s. Total usages: %(n)d.") % {
                'name': rec.name,
                'n': rec.usage_count,
            })

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        """End date must be on or after the start date."""
        for rec in self:
            if rec.start_date and rec.end_date \
                    and rec.end_date < rec.start_date:
                raise ValidationError(_(
                    "Pass %(name)s: end date (%(end)s) cannot be before "
                    "start date (%(start)s).") % {
                    'name': rec.name,
                    'end': rec.end_date,
                    'start': rec.start_date,
                })

    @api.constrains('pickup_stop_id', 'drop_stop_id', 'route_id')
    def _check_stops_on_route(self):
        """Pickup and drop stops must belong to the pass route."""
        for rec in self:
            if rec.pickup_stop_id and rec.route_id \
                    and rec.pickup_stop_id.route_id != rec.route_id:
                raise ValidationError(_(
                    "Pickup stop %(stop)s does not belong to route "
                    "%(route)s for pass %(name)s.") % {
                    'stop': rec.pickup_stop_id.display_name,
                    'route': rec.route_id.display_name,
                    'name': rec.name,
                })
            if rec.drop_stop_id and rec.route_id \
                    and rec.drop_stop_id.route_id != rec.route_id:
                raise ValidationError(_(
                    "Drop stop %(stop)s does not belong to route "
                    "%(route)s for pass %(name)s.") % {
                    'stop': rec.drop_stop_id.display_name,
                    'route': rec.route_id.display_name,
                    'name': rec.name,
                })
            if rec.pickup_stop_id and rec.drop_stop_id \
                    and rec.pickup_stop_id == rec.drop_stop_id:
                raise ValidationError(_(
                    "Pickup and drop stops cannot be the same for pass "
                    "%(name)s.") % {'name': rec.name})

    @api.constrains('route_id', 'university_id')
    def _check_route_university(self):
        """The route must belong to the same university as the student."""
        for rec in self:
            if rec.route_id and rec.university_id \
                    and rec.route_id.university_id \
                    and rec.route_id.university_id != rec.university_id:
                raise ValidationError(_(
                    "Route %(route)s does not belong to the same university "
                    "as student %(student)s.") % {
                    'route': rec.route_id.display_name,
                    'student': rec.student_id.display_name,
                })
