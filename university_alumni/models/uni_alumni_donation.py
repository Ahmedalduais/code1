# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniAlumniDonation(models.Model):
    """تبرعات الخريجين — سجل تبرع من خريج للجامعة.

    يدعم التبرعات النقدية، الشيكات، الحوالات، التبرعات العينية،
    الأسهم، وأنواع أخرى. يمكن أن يكون التبرع لأغراض متعددة
    (عام، منح دراسية، أبحاث، مبانٍ، معدات، أوقاف، برامج محددة).
    كما يدعم التبرعات المتكررة والمجهولة ويسمح بإرسال إشعار الشكر
    وتسجيل وصل الاستلام.
    """
    _name = 'uni.alumni.donation'
    _description = 'Alumni Donation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'donation_date desc, id desc'

    # ------------------------------------------------------------------
    # Identity & reference
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Reference', copy=False, readonly=True, index=True,
        default=lambda self: _('New'), tracking=True,
        help='Auto-generated donation reference (ADN/...).')
    code = fields.Char(
        string='Code', copy=False, index=True, tracking=True,
        help='Optional manual code identifying the donation.')

    # ------------------------------------------------------------------
    # Member & date
    # ------------------------------------------------------------------
    member_id = fields.Many2one(
        'uni.alumni.member', string='Alumni Member',
        required=True, ondelete='restrict', tracking=True, index=True)
    university_id = fields.Many2one(
        'uni.university', string='University',
        related='member_id.university_id', store=True, index=True)
    donation_date = fields.Date(
        string='Donation Date', default=fields.Date.context_today,
        required=True, tracking=True)

    # ------------------------------------------------------------------
    # Amount
    # ------------------------------------------------------------------
    amount = fields.Monetary(
        string='Amount', currency_field='currency_id',
        required=True, tracking=True,
        help='Donation amount in the selected currency.')
    currency_id = fields.Many2one(
        'res.currency', string='Currency', required=True, tracking=True,
        default=lambda self: self.env.company.currency_id)

    # ------------------------------------------------------------------
    # Type & payment
    # ------------------------------------------------------------------
    donation_type = fields.Selection([
        ('cash', 'Cash'),
        ('check', 'Check'),
        ('transfer', 'Bank Transfer'),
        ('in_kind', 'In-Kind'),
        ('stock', 'Stock / Securities'),
        ('other', 'Other'),
    ], string='Donation Type', default='cash', tracking=True, index=True)
    payment_reference = fields.Char(
        string='Payment Reference', tracking=True,
        help='Check number, transaction id, transfer reference, etc.')

    # ------------------------------------------------------------------
    # Purpose
    # ------------------------------------------------------------------
    purpose = fields.Selection([
        ('general', 'General'),
        ('scholarship', 'Scholarship'),
        ('research', 'Research'),
        ('building', 'Building'),
        ('equipment', 'Equipment'),
        ('endowment', 'Endowment'),
        ('specific_program', 'Specific Program'),
        ('other', 'Other'),
    ], string='Purpose', default='general', tracking=True, index=True)
    purpose_details = fields.Char(
        string='Purpose Details', tracking=True,
        help='Specific program name, scholarship name, building name, etc.')

    # ------------------------------------------------------------------
    # Anonymous & recurring
    # ------------------------------------------------------------------
    is_anonymous = fields.Boolean(
        string='Anonymous', default=False, tracking=True,
        help='If set, the donor name will be hidden in public reports.')
    is_recurring = fields.Boolean(
        string='Recurring', default=False, tracking=True,
        help='If set, this donation is part of a recurring schedule.')
    recurrence_frequency = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annual', 'Annual'),
    ], string='Recurrence Frequency', tracking=True)

    # ------------------------------------------------------------------
    # Receipt & acknowledgement
    # ------------------------------------------------------------------
    received_by = fields.Many2one(
        'res.users', string='Received By', tracking=True, index=True,
        default=lambda self: self.env.user)
    acknowledgement_sent = fields.Boolean(
        string='Acknowledgement Sent', default=False, copy=False,
        tracking=True)
    acknowledgement_date = fields.Date(
        string='Acknowledgement Date', copy=False, tracking=True)
    receipt_file = fields.Binary(
        string='Receipt', attachment=True, copy=False,
        help='Upload the donation receipt / proof of payment.')
    receipt_filename = fields.Char(string='Receipt Filename', copy=False)

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------
    state = fields.Selection([
        ('pending', 'Pending'),
        ('received', 'Received'),
        ('cancelled', 'Cancelled'),
    ], string='State', default='pending', tracking=True, index=True,
        group_expand='_group_expand_states')

    # ------------------------------------------------------------------
    # Misc
    # ------------------------------------------------------------------
    notes = fields.Text(string='Notes')
    active = fields.Boolean(string='Active', default=True, tracking=True)
    color = fields.Integer(string='Color Index')

    _sql_constraints = [
        ('unique_donation_code', 'unique(code)',
         'Donation code must be unique!'),
    ]

    # ------------------------------------------------------------------
    # Group expansion
    # ------------------------------------------------------------------
    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in self._fields['state'].selection]

    # ------------------------------------------------------------------
    # Create — auto-sequence the donation reference
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.alumni.donation') or _('ADN-NEW')
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Onchange
    # ------------------------------------------------------------------
    @api.onchange('is_recurring')
    def _onchange_is_recurring(self):
        """Clear recurrence frequency when not recurring."""
        if not self.is_recurring:
            self.recurrence_frequency = False

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_receive(self):
        """Mark the donation as received."""
        for rec in self:
            if rec.state != 'pending':
                raise ValidationError(_(
                    "Only pending donations can be received "
                    "(current: %(s)s for %(n)s).") % {
                    's': rec.state, 'n': rec.display_name})
            if not rec.received_by:
                rec.received_by = self.env.user
            rec.state = 'received'
            rec.message_post(body=_(
                "Donation received. Amount: %(a)s %(c)s.") % {
                'a': rec.amount, 'c': rec.currency_id.symbol or '',
            })

    def action_cancel(self):
        """Cancel the donation."""
        for rec in self:
            if rec.state == 'received' and rec.acknowledgement_sent:
                raise ValidationError(_(
                    "Cannot cancel a received donation after acknowledgement "
                    "has been sent (%s).") % rec.display_name)
            rec.state = 'cancelled'
            rec.message_post(body=_("Donation cancelled."))

    def action_reset_to_pending(self):
        """Reset a cancelled donation back to pending."""
        for rec in self:
            if rec.state != 'cancelled':
                raise ValidationError(_(
                    "Only cancelled donations can be reset to pending "
                    "(current: %(s)s for %(n)s).") % {
                    's': rec.state, 'n': rec.display_name})
            rec.state = 'pending'
            rec.message_post(body=_("Donation reset to pending."))

    def action_send_acknowledgement(self):
        """Mark the acknowledgement as sent (records the date).

        A real implementation could trigger an email template; here we
        simply record the action and post a message in the chatter.
        """
        for rec in self:
            if rec.state != 'received':
                raise ValidationError(_(
                    "Acknowledgement can only be sent for received donations "
                    "(current: %(s)s for %(n)s).") % {
                    's': rec.state, 'n': rec.display_name})
            rec.acknowledgement_sent = True
            rec.acknowledgement_date = fields.Date.context_today(rec)
            donor = _("Anonymous donor") if rec.is_anonymous else rec.member_id.display_name
            rec.message_post(body=_(
                "Acknowledgement sent to %(d)s for donation %(n)s.") % {
                'd': donor, 'n': rec.display_name,
            })

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('amount')
    def _check_amount_positive(self):
        """Donation amount must be strictly greater than zero."""
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(_(
                    "Donation amount must be greater than zero "
                    "(got %(a)s for %(n)s).") % {
                    'a': rec.amount, 'n': rec.display_name})

    @api.constrains('is_recurring', 'recurrence_frequency')
    def _check_recurring_has_frequency(self):
        """Recurring donations must have a frequency set."""
        for rec in self:
            if rec.is_recurring and not rec.recurrence_frequency:
                raise ValidationError(_(
                    "A recurring donation must specify a frequency (%s).")
                    % rec.display_name)

    @api.constrains('acknowledgement_sent', 'acknowledgement_date')
    def _check_acknowledgement_consistency(self):
        """Acknowledgement date can only be set if sent."""
        for rec in self:
            if rec.acknowledgement_date and not rec.acknowledgement_sent:
                raise ValidationError(_(
                    "Acknowledgement date cannot be set before the "
                    "acknowledgement is sent (%s).") % rec.display_name)
