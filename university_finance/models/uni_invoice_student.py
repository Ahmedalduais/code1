# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class UniInvoiceStudent(models.Model):
    """الفاتورة الطلابية — فاتورة مالية تصدر للطالب عن فصل دراسي.

    تمثّل هذه الفاتورة الجانب المالي لتسجيل الطالب في فصل دراسي وفق
    هيكل رسوم محدد. تتكوّن من بنود (``uni.invoice.student.line``) كل منها
    يربط نوع رسوم بكمية وسعر وخصم، ويحسب المجموع الفرعي.

    توفّر الفاتورة:
        * ربطاً اختيارياً بهيكل رسوم (``fee_structure_id``) ومنحة (``scholarship_id``)
        * ربطاً اختيارياً بخطة سداد (``payment_plan_id``)
        * ربطاً ثنائي الاتجاه بفاتورة Odoo المحاسبية (``account.move``)
        * سير حالة (draft → confirmed → paid/partial → cancelled)
        * إنشاء فاتورة Odoo تلقائياً عبر ``action_create_account_invoice()``

    مبالغ ``amount_total``/``amount_paid``/``amount_due`` محسوبة ومخزّنة.
    """
    _name = 'uni.invoice.student'
    _description = 'Student Invoice'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'invoice_date desc, name'

    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True,
        default=lambda self: _('New'), index=True, tracking=True,
        help='Unique invoice number (auto-generated via sequence INV/...).')
    code = fields.Char(
        string='Code', copy=False, tracking=True, index=True,
        help='Optional human-friendly code.')

    student_id = fields.Many2one(
        'uni.student', string='Student', required=True, ondelete='restrict',
        tracking=True, index=True)
    university_id = fields.Many2one(
        'uni.university', string='University',
        related='student_id.university_id', store=True, readonly=True,
        tracking=True, index=True)
    academic_term_id = fields.Many2one(
        'uni.academic.term', string='Academic Term', ondelete='restrict',
        tracking=True, index=True)
    fee_structure_id = fields.Many2one(
        'uni.fee.structure', string='Fee Structure', ondelete='restrict',
        tracking=True, index=True,
        help='Fee structure used to populate this invoice. Changing the '
             'structure does not auto-overwrite existing lines.')
    invoice_date = fields.Date(
        string='Invoice Date', default=fields.Date.context_today,
        required=True, tracking=True, index=True)
    due_date = fields.Date(
        string='Due Date', tracking=True,
        help='Date by which the invoice should be fully paid.')

    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True, tracking=True)
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company, required=True, index=True)

    scholarship_id = fields.Many2one(
        'uni.scholarship', string='Scholarship', ondelete='restrict',
        tracking=True, index=True,
        help='Optional scholarship to apply as a discount on this invoice.')
    discount_amount = fields.Float(
        string='Discount Amount', digits=(16, 2), default=0.0, tracking=True,
        help='Total discount applied to the invoice (scholarship + manual).')

    payment_plan_id = fields.Many2one(
        'uni.payment.plan', string='Payment Plan', ondelete='restrict',
        tracking=True, index=True,
        help='Optional payment plan regulating the installments.')

    move_id = fields.Many2one(
        'account.move', string='Accounting Invoice', copy=False,
        ondelete='restrict', tracking=True, index=True,
        help='Linked Odoo accounting invoice (account.move). Created via '
             'the "Create Accounting Invoice" button.')

    # ------------------------------------------------------------------
    # Computed totals (stored for filtering & sorting)
    # ------------------------------------------------------------------
    amount_total = fields.Float(
        string='Total', digits=(16, 2), default=0.0,
        compute='_compute_amounts', store=True, tracking=True)
    amount_paid = fields.Float(
        string='Paid', digits=(16, 2), default=0.0,
        compute='_compute_amounts', store=True, tracking=True)
    amount_due = fields.Float(
        string='Due', digits=(16, 2), default=0.0,
        compute='_compute_amounts', store=True, tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('paid', 'Paid'),
        ('partial', 'Partially Paid'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, index=True,
        group_expand='_group_expand_states')

    line_ids = fields.One2many(
        'uni.invoice.student.line', 'invoice_id', string='Invoice Lines',
        copy=True)
    line_count = fields.Integer(
        compute='_compute_line_count', string='Lines')
    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True, tracking=True)

    # ------------------------------------------------------------------
    # Journal / partner info (for account.move creation)
    # ------------------------------------------------------------------
    partner_id = fields.Many2one(
        'res.partner', string='Customer',
        related='student_id.partner_id', store=True, readonly=True,
        help='Customer partner created from the student record — used as '
             'the partner on the linked account.move.')

    _sql_constraints = [
        ('unique_invoice_name', 'unique(name)',
         'Student invoice reference must be unique!'),
        ('check_amounts_positive',
         'check(amount_total >= 0 AND amount_paid >= 0 AND amount_due >= 0)',
         'Amounts cannot be negative!'),
        ('check_discount_positive', 'check(discount_amount >= 0)',
         'Discount amount cannot be negative!'),
    ]

    # ------------------------------------------------------------------
    # Group expansion helper
    # ------------------------------------------------------------------
    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in self._fields['state'].selection]

    # ------------------------------------------------------------------
    # Create — auto-generate reference
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.invoice.student') or _('INV-NEW')
            if not vals.get('code'):
                vals['code'] = vals.get('name')
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Computed
    # ------------------------------------------------------------------
    @api.depends('line_ids.subtotal', 'line_ids', 'discount_amount',
                 'scholarship_id.discount_percentage',
                 'scholarship_id.discount_amount',
                 'scholarship_id.approval_status',
                 'move_id', 'move_id.amount_total', 'move_id.amount_residual',
                 'move_id.state', 'move_id.payment_state', 'move_id.currency_id')
    def _compute_amounts(self):
        """Compute total / paid / due amounts.

        ``amount_total`` is the sum of line subtotals minus the discount.
        ``amount_paid`` is read from the linked account.move residual
        if a move is posted; otherwise 0.
        ``amount_due`` is the difference.
        """
        for rec in self:
            gross = sum(rec.line_ids.mapped('subtotal'))
            discount = rec.discount_amount or 0.0
            total = gross - discount
            if total < 0:
                total = 0.0
            paid = 0.0
            if rec.move_id and rec.move_id.state == 'posted':
                if rec.move_id.currency_id == rec.currency_id:
                    total = rec.move_id.amount_total
                paid = rec.move_id.amount_total - rec.move_id.amount_residual
                if paid < 0:
                    paid = 0.0
            due = total - paid
            if due < 0:
                due = 0.0
            rec.amount_total = total
            rec.amount_paid = paid
            rec.amount_due = due

    @api.depends('line_ids')
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    # ------------------------------------------------------------------
    # Payment-status sync (separated from compute to avoid recursion)
    # ------------------------------------------------------------------
    def action_sync_payment_status(self):
        """Refresh the invoice state from the linked account.move.

        Called automatically when the linked move is posted/paid/cancelled
        (see the ``account.move`` inheritance in this module) but also
        callable manually from the UI.
        """
        for rec in self:
            if rec.state in ('draft', 'cancelled'):
                continue
            if not rec.move_id:
                # No linked move — keep confirmed
                if rec.state in ('paid', 'partial'):
                    rec.state = 'confirmed'
                continue
            paid = rec.amount_paid or 0.0
            due = rec.amount_due or 0.0
            if paid <= 0:
                new_state = 'confirmed'
            elif due <= 0:
                new_state = 'paid'
            else:
                new_state = 'partial'
            if new_state != rec.state:
                rec.state = new_state

    # ------------------------------------------------------------------
    # Onchange
    # ------------------------------------------------------------------
    @api.onchange('student_id')
    def _onchange_student_id(self):
        if self.student_id:
            self.university_id = self.student_id.university_id

    @api.onchange('fee_structure_id')
    def _onchange_fee_structure_id(self):
        """When a fee structure is set, pre-fill lines from its lines.

        Only fills when the invoice has no existing lines (to avoid wiping
        user-edited data).
        """
        if self.fee_structure_id and not self.line_ids:
            new_lines = []
            for line in self.fee_structure_id.line_ids:
                new_lines.append((0, 0, {
                    'fee_type_id': line.fee_type_id.id,
                    'description': line.fee_type_id.name,
                    'quantity': 1.0,
                    'price_unit': line.amount,
                    'discount': 0.0,
                }))
            self.line_ids = new_lines
            self.currency_id = self.fee_structure_id.currency_id

    @api.onchange('scholarship_id')
    def _onchange_scholarship_id(self):
        """Pre-fill discount amount based on the scholarship."""
        if self.scholarship_id and self.scholarship_id.approval_status == 'active':
            gross = sum(self.line_ids.mapped('subtotal'))
            if self.scholarship_id.discount_percentage > 0:
                self.discount_amount = gross * \
                    (self.scholarship_id.discount_percentage / 100.0)
            else:
                self.discount_amount = self.scholarship_id.discount_amount

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def action_confirm(self):
        """Confirm the student invoice — locks the lines."""
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError(_(
                    "Only draft invoices can be confirmed (%s is %s).")
                    % (rec.display_name, rec.state))
            if not rec.line_ids:
                raise ValidationError(_(
                    "Cannot confirm an invoice without lines (%s).")
                    % rec.display_name)
            if not rec.due_date:
                rec.due_date = fields.Date.context_today(rec)
            rec.state = 'confirmed'

    def action_cancel(self):
        """Cancel the invoice — also cancels the linked account.move."""
        for rec in self:
            if rec.state == 'cancelled':
                continue
            if rec.move_id and rec.move_id.state != 'cancel':
                rec.move_id.sudo().button_cancel()
            rec.state = 'cancelled'

    def action_draft(self):
        """Reset a cancelled invoice back to draft."""
        for rec in self:
            if rec.state != 'cancelled':
                raise ValidationError(_(
                    "Only cancelled invoices can be set back to draft "
                    "(%s is %s).") % (rec.display_name, rec.state))
            rec.state = 'draft'

    # ------------------------------------------------------------------
    # Account.move creation
    # ------------------------------------------------------------------
    def _prepare_account_move_vals(self):
        """Build the values dict for the linked ``account.move``.

        Lines are generated from the student invoice lines: one line per
        fee type using the product (if any) attached to the fee type, or
        a generic revenue line. Discount is applied as a separate line or
        distributed per line; we distribute per line for simplicity.
        """
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_(
                "Student %s has no related partner; cannot create an "
                "accounting invoice.") % self.student_id.display_name)

        # Try to find a sale journal for the company
        journal = self.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', self.company_id.id),
        ], limit=1)
        if not journal:
            raise UserError(_(
                "No sale journal found for company %s. Please configure an "
                "accounting sale journal before creating the invoice.")
                % self.company_id.display_name)

        # Find a default income account (fallback: company's default)
        income_account = self.company_id.account_default_income_account_id or \
            self.env['account.account'].search([
                ('company_id', '=', self.company_id.id),
                ('account_type', '=', 'income'),
            ], limit=1)
        if not income_account:
            raise UserError(_(
                "No income account found for company %s. Please configure an "
                "income account before creating the invoice.")
                % self.company_id.display_name)

        # Build invoice lines. The discount is applied as a per-line
        # percentage so that the resulting account.move reflects the
        # scholarship / manual discount that was applied on the student
        # invoice.
        total_gross = sum(self.line_ids.mapped('subtotal'))
        discount = self.discount_amount or 0.0
        discount_ratio = 0.0
        if total_gross > 0 and discount > 0:
            discount_ratio = discount / total_gross

        move_lines = []
        for line in self.line_ids:
            line_subtotal = line.subtotal
            line_discount = line_subtotal * discount_ratio
            net_amount = line_subtotal - line_discount
            if net_amount == 0:
                continue
            line_discount_pct = (line_discount / line_subtotal * 100.0) \
                if line_subtotal > 0 else 0.0
            account = income_account
            move_lines.append((0, 0, {
                'name': line.description or
                        (line.fee_type_id.name if line.fee_type_id else _('Fee')),
                'quantity': line.quantity,
                'price_unit': line.price_unit,
                'discount': line_discount_pct,
                'account_id': account.id,
            }))

        # If discount was applied but no lines exist, add a discount-only line
        if not move_lines:
            move_lines.append((0, 0, {
                'name': _('Student Invoice %s') % self.name,
                'quantity': 1.0,
                'price_unit': max(total_gross - discount, 0.0),
                'discount': 0.0,
                'account_id': income_account.id,
            }))

        return {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': self.invoice_date,
            'date': self.invoice_date,
            'currency_id': self.currency_id.id,
            'journal_id': journal.id,
            'company_id': self.company_id.id,
            'invoice_line_ids': move_lines,
            'narration': self.notes or '',
            'ref': self.name,
        }

    def action_create_account_invoice(self):
        """Create an ``account.move`` (customer invoice) from this student invoice.

        The created move is linked to the current record via ``move_id``.
        Posting the move is left to the standard Odoo workflow so the user
        can review before posting.
        """
        for rec in self:
            if rec.move_id:
                raise UserError(_(
                    "Invoice %s already has a linked accounting invoice (%s).")
                    % (rec.display_name, rec.move_id.display_name))
            if rec.state == 'cancelled':
                raise UserError(_(
                    "Cannot create an accounting invoice for a cancelled "
                    "student invoice (%s).") % rec.display_name)
            if not rec.line_ids:
                raise ValidationError(_(
                    "Cannot create an accounting invoice without lines (%s).")
                    % rec.display_name)
            move_vals = rec._prepare_account_move_vals()
            # Use sudo so university users (without explicit accounting
            # access) can still create the linked invoice. The created
            # move inherits the company/journal from this student invoice.
            move = self.env['account.move'].sudo().create(move_vals)
            rec.move_id = move.id
            rec.message_post(
                body=_('Accounting invoice %s created.') %
                move.display_name)
            # Refresh payment status (will fall back to 'confirmed' until
            # the move is posted and paid)
            rec.action_sync_payment_status()
        # Open the created move(s) for review
        if len(self) == 1 and self.move_id:
            return {
                'name': _('Accounting Invoice'),
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'res_id': self.move_id.id,
                'view_mode': 'form',
            }
        return True

    # ------------------------------------------------------------------
    # Smart-button actions
    # ------------------------------------------------------------------
    def action_view_account_invoice(self):
        """Open the linked account.move, if any."""
        self.ensure_one()
        if not self.move_id:
            raise UserError(_(
                "Invoice %s has no linked accounting invoice yet.")
                % self.display_name)
        return {
            'name': _('Accounting Invoice'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.move_id.id,
            'view_mode': 'form',
        }

    def action_view_payment(self):
        """Open payments linked to the account.move (if any)."""
        self.ensure_one()
        if not self.move_id:
            raise UserError(_(
                "Invoice %s has no linked accounting invoice; no payments "
                "to display.") % self.display_name)
        # Use sudo so university users (without explicit accounting access)
        # can view the reconciled payments.
        move = self.move_id.sudo()
        payments = move._get_reconciled_payments() \
            if hasattr(move, '_get_reconciled_payments') else \
            self.env['account.payment']
        if not payments:
            raise UserError(_(
                "No payments have been registered on the linked accounting "
                "invoice yet."))
        return {
            'name': _('Payments'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'domain': [('id', 'in', payments.ids)],
        }

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('invoice_date', 'due_date')
    def _check_dates(self):
        for rec in self:
            if rec.invoice_date and rec.due_date and \
                    rec.due_date < rec.invoice_date:
                raise ValidationError(_(
                    "Due date cannot be earlier than invoice date for %s.")
                    % rec.display_name)

    @api.constrains('discount_amount', 'line_ids')
    def _check_discount_within_total(self):
        """Discount cannot exceed the gross total of the invoice."""
        for rec in self:
            gross = sum(rec.line_ids.mapped('subtotal'))
            if rec.discount_amount > gross:
                raise ValidationError(_(
                    "Discount amount (%(disc).2f) cannot exceed the invoice "
                    "gross total (%(gross).2f) for %(inv)s.") % {
                    'disc': rec.discount_amount,
                    'gross': gross,
                    'inv': rec.display_name})

    @api.constrains('scholarship_id', 'student_id')
    def _check_scholarship_student(self):
        """Scholarship must belong to the same student."""
        for rec in self:
            if rec.scholarship_id and rec.student_id and \
                    rec.scholarship_id.student_id != rec.student_id:
                raise ValidationError(_(
                    "Selected scholarship %s does not belong to student %s.")
                    % (rec.scholarship_id.display_name,
                       rec.student_id.display_name))


class UniInvoiceStudentLine(models.Model):
    """بند الفاتورة الطلابية — يحدّد نوع الرسوم والكمية والسعر والخصم."""
    _name = 'uni.invoice.student.line'
    _description = 'Student Invoice Line'
    _order = 'sequence, fee_type_id'

    invoice_id = fields.Many2one(
        'uni.invoice.student', string='Invoice', required=True,
        ondelete='cascade', index=True)
    fee_type_id = fields.Many2one(
        'uni.fee.type', string='Fee Type', ondelete='restrict', index=True,
        help='Type of fee being charged by this line.')
    fee_type_code = fields.Char(
        string='Fee Type Code', related='fee_type_id.code', store=True)
    description = fields.Char(
        string='Description',
        help='Description shown on the invoice line. Defaults to the fee '
             'type name.')
    quantity = fields.Float(
        string='Quantity', digits=(16, 2), default=1.0, required=True,
        help='Number of units (e.g. credit hours for tuition).')
    price_unit = fields.Float(
        string='Unit Price', digits=(16, 2), default=0.0, required=True,
        help='Price per unit in the invoice currency.')
    discount = fields.Float(
        string='Discount %', digits=(5, 2), default=0.0,
        help='Percentage discount applied to this line (0–100).')
    subtotal = fields.Float(
        string='Subtotal', digits=(16, 2), default=0.0,
        compute='_compute_subtotal', store=True,
        help='Quantity × Unit Price × (1 − Discount%).')
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        related='invoice_id.currency_id', store=True, readonly=True)
    sequence = fields.Integer(string='Sequence', default=10)

    _sql_constraints = [
        ('check_quantity_positive', 'check(quantity >= 0)',
         'Quantity cannot be negative!'),
        ('check_price_positive', 'check(price_unit >= 0)',
         'Unit price cannot be negative!'),
        ('check_discount_range',
         'check(discount >= 0 AND discount <= 100)',
         'Discount percentage must be between 0 and 100!'),
    ]

    @api.depends('quantity', 'price_unit', 'discount')
    def _compute_subtotal(self):
        for rec in self:
            gross = (rec.quantity or 0.0) * (rec.price_unit or 0.0)
            disc = (rec.discount or 0.0) / 100.0
            rec.subtotal = gross * (1 - disc)

    @api.onchange('fee_type_id')
    def _onchange_fee_type_id(self):
        """Pre-fill description and unit price from the fee type."""
        if self.fee_type_id:
            if not self.description:
                self.description = self.fee_type_id.name
            if not self.price_unit:
                self.price_unit = self.fee_type_id.default_amount

    @api.constrains('quantity', 'price_unit', 'discount')
    def _check_values(self):
        for rec in self:
            if rec.quantity < 0:
                raise ValidationError(_(
                    "Quantity cannot be negative for line %s.") %
                    rec.display_name)
            if rec.price_unit < 0:
                raise ValidationError(_(
                    "Unit price cannot be negative for line %s.") %
                    rec.display_name)
            if not (0 <= rec.discount <= 100):
                raise ValidationError(_(
                    "Discount percentage must be between 0 and 100 for "
                    "line %s.") % rec.display_name)


class AccountMove(models.Model):
    """Extend ``account.move`` to keep the linked student invoice in sync.

    When an ``account.move`` created from a student invoice is posted,
    cancelled, or has its payment state changed (paid / partial), the
    linked ``uni.invoice.student`` record is updated so that its state
    reflects the latest payment status.
    """
    _inherit = 'account.move'

    def write(self, vals):
        """Detect state / payment_state changes and sync linked invoices."""
        res = super().write(vals)
        sync_keys = {'state', 'payment_state', 'amount_total',
                     'amount_residual'}
        if sync_keys.intersection(vals.keys()):
            # Find student invoices linked to any of the written moves
            invoices = self.env['uni.invoice.student'].sudo().search([
                ('move_id', 'in', self.ids),
            ])
            if invoices:
                invoices.action_sync_payment_status()
        return res

