# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class UniLibraryFine(models.Model):
    """الغرامة — غرامة مكتبية مرتبطة بسجل استعارة.

    يُنشأ النموذج تلقائياً عند الإرجاع المتأخر لكتاب، كما يمكن إنشاؤه
    يدوياً لغرامات التلف أو الفقد. يوفّر سير اعتماد (معلّق → مدفوع →
    متنازل عنه → ملغى) مع تسجيل طريقة الدفع والمستخدم الذي قام بالتحصيل.

    يوفّر النموذج:
        * توليد رقم تسلسلي تلقائي LFN/%(year)s/00000
        * حقول مرتبطة من borrow_id (borrower_name, student_name, faculty_name)
        * طرق دفع متعددة (cash/transfer/check/online)
        * تتبع تواريخ الإصدار والاستحقاق والدفع
    """
    _name = 'uni.library.fine'
    _description = 'Library Fine'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'issue_date desc, id desc'

    # ------------------------------------------------------------------
    # Identification
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True,
        default='New', tracking=True, index=True,
        help='Unique sequence reference of the fine.')
    code = fields.Char(
        string='Code', copy=False, tracking=True, index=True,
        help='Optional secondary code for manual lookups.')

    # ------------------------------------------------------------------
    # Borrow reference
    # ------------------------------------------------------------------
    borrow_id = fields.Many2one(
        'uni.library.borrow', string='Borrow Record', required=True,
        ondelete='restrict', tracking=True, index=True,
        help='Borrow record that generated this fine.')
    borrower_name = fields.Char(
        string='Borrower Name', related='borrow_id.borrower_name',
        store=True, readonly=True,
        help='Display name of the borrower (inherited from the borrow).')
    student_name = fields.Char(
        string='Student Name', related='borrow_id.student_name',
        store=True, readonly=True, index=True,
        help='Student borrower name (inherited from the borrow).')
    faculty_name = fields.Char(
        string='Faculty Name', related='borrow_id.faculty_name',
        store=True, readonly=True, index=True,
        help='Faculty borrower name (inherited from the borrow).')

    # ------------------------------------------------------------------
    # Fine details
    # ------------------------------------------------------------------
    fine_type = fields.Selection([
        ('overdue', 'Overdue'),
        ('damage', 'Damage'),
        ('lost', 'Lost Book'),
        ('other', 'Other'),
    ], string='Fine Type', default='overdue', required=True,
        tracking=True, index=True,
        help='Reason the fine was issued.')
    amount = fields.Float(
        string='Amount', required=True, digits=(16, 2), default=0.0,
        tracking=True,
        help='Fine amount in the chosen currency.')
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True, tracking=True,
        help='Currency of the fine amount.')
    issue_date = fields.Date(
        string='Issue Date', required=True,
        default=fields.Date.context_today, tracking=True,
        help='Date the fine was issued.')
    due_date = fields.Date(
        string='Payment Due Date', tracking=True,
        help='Date by which the fine must be paid.')
    payment_date = fields.Date(
        string='Payment Date', tracking=True,
        help='Date the fine was actually paid.')
    paid_by = fields.Many2one(
        'res.users', string='Paid By', tracking=True,
        help='User who recorded the payment.')
    description = fields.Text(
        string='Description', translate=True,
        help='Reason or details about the fine.')
    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('transfer', 'Bank Transfer'),
        ('check', 'Check'),
        ('online', 'Online Payment'),
    ], string='Payment Method', tracking=True,
        help='Method used to pay the fine.')

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------
    state = fields.Selection([
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('waived', 'Waived'),
        ('cancelled', 'Cancelled'),
    ], string='State', default='pending', required=True,
        tracking=True, index=True, group_expand='_group_expand_states',
        help='Lifecycle state of the fine.')
    notes = fields.Text(
        string='Notes', translate=True,
        help='Internal notes about this fine.')

    _sql_constraints = [
        ('unique_fine_name', 'unique(name)',
         'Fine reference must be unique!'),
        ('check_amount_non_negative',
         'check(amount >= 0)',
         'Fine amount cannot be negative!'),
    ]

    # ------------------------------------------------------------------
    # Create — auto sequence
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        """Auto-generate the sequence reference for each new fine."""
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.library.fine') or 'New'
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
    def action_pay(self):
        """Mark the fine as paid."""
        for rec in self:
            if rec.state != 'pending':
                raise UserError(_(
                    "Fine %(name)s cannot be paid from state %(state)s.") % {
                    'name': rec.name,
                    'state': rec.state,
                })
            rec.state = 'paid'
            rec.payment_date = fields.Date.context_today(rec)
            rec.paid_by = self.env.user.id
            # Mark the linked borrow's fine as paid
            if rec.borrow_id:
                rec.borrow_id.fine_paid = True
            rec.message_post(body=_(
                "Fine paid on %(date)s by %(user)s.") % {
                'date': rec.payment_date,
                'user': self.env.user.display_name,
            })

    def action_waive(self):
        """Waive the fine — typically for justified cases."""
        for rec in self:
            if rec.state != 'pending':
                raise UserError(_(
                    "Fine %(name)s cannot be waived from state %(state)s.") % {
                    'name': rec.name,
                    'state': rec.state,
                })
            rec.state = 'waived'
            if rec.borrow_id:
                rec.borrow_id.fine_paid = True
            rec.message_post(body=_("Fine waived."))

    def action_cancel(self):
        """Cancel the fine."""
        for rec in self:
            if rec.state == 'paid':
                raise UserError(_(
                    "Cannot cancel a paid fine (%s).") % rec.name)
            rec.state = 'cancelled'
            if rec.borrow_id:
                rec.borrow_id.fine_paid = False
            rec.message_post(body=_("Fine cancelled."))

    def action_reset_pending(self):
        """Reset the fine to pending state."""
        for rec in self:
            rec.state = 'pending'
            rec.payment_date = False
            rec.paid_by = False
            if rec.borrow_id:
                rec.borrow_id.fine_paid = False
            rec.message_post(body=_("Fine reset to pending."))

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('due_date', 'issue_date', 'payment_date')
    def _check_dates(self):
        """Ensure payment and due dates are after the issue date."""
        for rec in self:
            if rec.issue_date and rec.due_date \
                    and rec.due_date < rec.issue_date:
                raise ValidationError(_(
                    "Payment due date (%(due)s) cannot be before issue "
                    "date (%(issue)s) for fine %(name)s.") % {
                    'due': rec.due_date,
                    'issue': rec.issue_date,
                    'name': rec.name,
                })
            if rec.issue_date and rec.payment_date \
                    and rec.payment_date < rec.issue_date:
                raise ValidationError(_(
                    "Payment date (%(paid)s) cannot be before issue date "
                    "(%(issue)s) for fine %(name)s.") % {
                    'paid': rec.payment_date,
                    'issue': rec.issue_date,
                    'name': rec.name,
                })

    @api.constrains('state', 'payment_date', 'paid_by')
    def _check_paid_has_payment_info(self):
        """Paid fines must have a payment date and paid_by user."""
        for rec in self:
            if rec.state == 'paid':
                if not rec.payment_date:
                    raise ValidationError(_(
                        "Paid fine %(name)s must have a payment date.") % {
                        'name': rec.name})
                if not rec.paid_by:
                    raise ValidationError(_(
                        "Paid fine %(name)s must record who paid it.") % {
                        'name': rec.name})
