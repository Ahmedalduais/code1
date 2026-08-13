# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class UniHousingContract(models.Model):
    """العقد — عقد سكن جامعي بين الطالب والجامعة.

    يحتوي النموذج على بيانات العقد الكاملة (الطالب، التخصيص المرتبط،
    نوع العقد، تواريخ البدء والانتهاء، المبلغ الإجمالي والمدفوع،
    الإيداع، تكرار الدفع، الشروط والأحكام، التوقيعات) ويدير سير عمل
    العقد من المسودة إلى النشاط ثم الانتهاء أو الفسخ.

    يوفّر النموذج:
        * توليد رقم تسلسلي تلقائي HCT/%(year)s/00000
        * ربط اختياري بالتخصيص
        * تتبع المبلغ المدفوع والإيداع واسترداده
        * توقيع الطالب والموظف وتواريخ التوقيع
        * سير عمل: مسودة → نشط → منتهي/مفسوخ
        * تحقق: end_date بعد start_date
    """
    _name = 'uni.housing.contract'
    _description = 'Housing Contract'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'start_date desc, id desc'

    # ------------------------------------------------------------------
    # Identification
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True,
        default='New', tracking=True, index=True,
        help='Unique sequence reference of the contract.')
    code = fields.Char(
        string='Code', copy=False, tracking=True, index=True,
        help='Optional secondary code for manual lookups.')

    # ------------------------------------------------------------------
    # Student & Allocation
    # ------------------------------------------------------------------
    student_id = fields.Many2one(
        'uni.student', string='Student', required=True,
        ondelete='restrict', tracking=True, index=True,
        help='Student signing the housing contract.')
    university_id = fields.Many2one(
        'uni.university', string='University',
        related='student_id.university_id', store=True, index=True,
        help='University that owns the contract (inherited from the student).')
    allocation_id = fields.Many2one(
        'uni.housing.allocation', string='Allocation',
        ondelete='set null', copy=False,
        domain="[('student_id', '=', student_id)]",
        help='Optional housing allocation linked to this contract.')

    # ------------------------------------------------------------------
    # Contract Type & Dates
    # ------------------------------------------------------------------
    contract_type = fields.Selection([
        ('semester', 'Semester'),
        ('annual', 'Annual'),
        ('monthly', 'Monthly'),
        ('custom', 'Custom'),
    ], string='Contract Type', default='monthly', required=True,
        tracking=True, index=True,
        help='Type of the housing contract period.')
    start_date = fields.Date(
        string='Start Date', required=True, tracking=True,
        help='Date the contract becomes effective.')
    end_date = fields.Date(
        string='End Date', required=True, tracking=True,
        help='Date the contract expires.')

    # ------------------------------------------------------------------
    # Financials
    # ------------------------------------------------------------------
    total_amount = fields.Float(
        string='Total Amount', digits=(16, 2), default=0.0, tracking=True,
        help='Total amount payable under the contract.')
    paid_amount = fields.Float(
        string='Paid Amount', digits=(16, 2), default=0.0, tracking=True,
        help='Amount already paid by the student.')
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
        help='Currency used for all monetary amounts in this contract.')
    payment_frequency = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semester', 'Semester'),
        ('annual', 'Annual'),
    ], string='Payment Frequency', default='monthly', tracking=True,
        help='How often payments are due.')
    deposit_amount = fields.Float(
        string='Deposit Amount', digits=(16, 2), default=0.0, tracking=True,
        help='Security deposit collected at contract signing.')
    deposit_refunded = fields.Boolean(
        string='Deposit Refunded', default=False, tracking=True,
        help='True if the security deposit has been refunded to the student.')

    # ------------------------------------------------------------------
    # Terms & Signatures
    # ------------------------------------------------------------------
    terms_and_conditions = fields.Text(
        string='Terms & Conditions', translate=True,
        help='Full text of the contract terms and conditions.')
    signed_by_student = fields.Boolean(
        string='Signed by Student', default=False, tracking=True,
        help='True if the student has signed the contract.')
    signed_date = fields.Date(
        string='Signed Date', tracking=True,
        help='Date the contract was signed.')
    signed_by = fields.Many2one(
        'res.users', string='Signed By (Staff)', tracking=True,
        help='Staff member who counter-signed the contract.')

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('terminated', 'Terminated'),
    ], string='State', default='draft', required=True,
        tracking=True, index=True, group_expand='_group_expand_states',
        help='Lifecycle state of the contract.')
    notes = fields.Text(
        string='Notes', translate=True,
        help='Internal notes about this contract.')
    active = fields.Boolean(default=True, tracking=True)

    _sql_constraints = [
        ('unique_contract_name', 'unique(name)',
         'Contract reference must be unique!'),
        ('check_total_amount_positive', 'check(total_amount >= 0)',
         'Total amount cannot be negative!'),
        ('check_paid_amount_positive', 'check(paid_amount >= 0)',
         'Paid amount cannot be negative!'),
        ('check_deposit_positive', 'check(deposit_amount >= 0)',
         'Deposit amount cannot be negative!'),
    ]

    # ------------------------------------------------------------------
    # Create — auto sequence
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        """Auto-generate the sequence reference for each new contract."""
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.housing.contract') or 'New'
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
    def action_activate(self):
        """Activate the contract (must be in draft state)."""
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_(
                    "Contract %(name)s cannot be activated from state "
                    "%(state)s.") % {
                    'name': rec.name, 'state': rec.state,
                })
            if not rec.signed_by_student:
                raise UserError(_(
                    "Contract %(name)s cannot be activated until the student "
                    "has signed it.") % {'name': rec.name})
            rec.state = 'active'
            if not rec.signed_date:
                rec.signed_date = fields.Date.context_today(rec)
            if not rec.signed_by:
                rec.signed_by = self.env.uid
            rec.message_post(body=_("Contract activated."))

    def action_terminate(self):
        """Terminate the contract before its end date."""
        for rec in self:
            if rec.state != 'active':
                raise UserError(_(
                    "Contract %(name)s cannot be terminated from state "
                    "%(state)s.") % {
                    'name': rec.name, 'state': rec.state,
                })
            rec.state = 'terminated'
            rec.message_post(body=_("Contract terminated."))

    def action_expire(self):
        """Mark the contract as expired (end date reached)."""
        for rec in self:
            if rec.state != 'active':
                raise UserError(_(
                    "Contract %(name)s cannot be expired from state "
                    "%(state)s.") % {
                    'name': rec.name, 'state': rec.state,
                })
            rec.state = 'expired'
            rec.message_post(body=_("Contract expired."))

    def action_draft(self):
        """Reset a terminated/expired contract back to draft."""
        for rec in self:
            if rec.state in ('terminated', 'expired'):
                rec.state = 'draft'
                rec.message_post(body=_("Contract reset to draft."))

    def action_refund_deposit(self):
        """Mark the deposit as refunded."""
        for rec in self:
            if rec.deposit_amount <= 0:
                raise UserError(_(
                    "Contract %(name)s has no deposit to refund.") % {
                    'name': rec.name})
            rec.deposit_refunded = True
            rec.message_post(body=_(
                "Deposit of %(amount).2f refunded.") % {
                'amount': rec.deposit_amount,
            })

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('start_date', 'end_date')
    def _check_end_after_start(self):
        """End date must be on or after the start date."""
        for rec in self:
            if rec.start_date and rec.end_date \
                    and rec.end_date < rec.start_date:
                raise ValidationError(_(
                    "End date (%(end)s) cannot be before start date "
                    "(%(start)s) for contract %(name)s.") % {
                    'end': rec.end_date,
                    'start': rec.start_date,
                    'name': rec.name,
                })

    @api.constrains('paid_amount', 'total_amount')
    def _check_paid_not_exceed_total(self):
        """Paid amount cannot exceed the total amount."""
        for rec in self:
            if rec.paid_amount > rec.total_amount:
                raise ValidationError(_(
                    "Paid amount (%(paid).2f) cannot exceed total amount "
                    "(%(total).2f) for contract %(name)s.") % {
                    'paid': rec.paid_amount,
                    'total': rec.total_amount,
                    'name': rec.name,
                })

    @api.constrains('deposit_refunded', 'deposit_amount')
    def _check_refund_only_with_deposit(self):
        """Cannot mark deposit refunded if no deposit was collected."""
        for rec in self:
            if rec.deposit_refunded and rec.deposit_amount <= 0:
                raise ValidationError(_(
                    "Cannot refund deposit for contract %(name)s because no "
                    "deposit was collected.") % {'name': rec.name})

    @api.constrains('allocation_id', 'student_id')
    def _check_allocation_student_consistency(self):
        """When linked, the allocation must belong to the same student."""
        for rec in self:
            if rec.allocation_id and rec.student_id \
                    and rec.allocation_id.student_id != rec.student_id:
                raise ValidationError(_(
                    "Allocation %(alloc)s does not belong to student "
                    "%(student)s for contract %(name)s.") % {
                    'alloc': rec.allocation_id.display_name,
                    'student': rec.student_id.display_name,
                    'name': rec.name,
                })
