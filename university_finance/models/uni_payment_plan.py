# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniPaymentPlan(models.Model):
    """خطة السداد — تقسيم المبلغ المستحق على الطالب إلى دفعات مجدولة.

    تربط خطة السداد طالباً بفواتير طلابية متعددة وتولّد أقساطاً
    (``uni.payment.plan.line``) على فترات منتظمة (أسبوعية، نصف شهرية،
    شهرية، ربع سنوية). يتم تتبع حالة كل قسط (pending/paid/overdue) ومن
    خلالها يتم تحديث ``paid_amount`` على مستوى الخطة.

    سير الحالة: draft → active → completed / cancelled.
    """
    _name = 'uni.payment.plan'
    _description = 'Payment Plan'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'start_date desc, name'

    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True,
        default=lambda self: _('New'), index=True, tracking=True,
        help='Unique plan reference (auto-generated).')
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

    invoice_ids = fields.Many2many(
        'uni.invoice.student', string='Invoices',
        help='Student invoices covered by this payment plan.')
    total_amount = fields.Float(
        string='Total Amount', digits=(16, 2), default=0.0, tracking=True,
        required=True,
        help='Total amount to be paid through this plan.')
    paid_amount = fields.Float(
        string='Paid Amount', digits=(16, 2), default=0.0,
        compute='_compute_paid_amount', store=True, tracking=True,
        help='Sum of amounts from plan lines marked as paid.')
    remaining_amount = fields.Float(
        string='Remaining', digits=(16, 2), default=0.0,
        compute='_compute_paid_amount', store=True,
        help='Total amount minus paid amount.')
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True, tracking=True)
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company, required=True, index=True)

    installments_count = fields.Integer(
        string='Installments', default=1, required=True, tracking=True,
        help='Number of installments the plan should be split into.')
    start_date = fields.Date(
        string='Start Date', default=fields.Date.context_today,
        required=True, tracking=True,
        help='Date of the first installment.')
    frequency = fields.Selection([
        ('weekly', 'Weekly'),
        ('bi_weekly', 'Bi-Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
    ], string='Frequency', default='monthly', required=True, tracking=True,
        help='Interval between consecutive installments.')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, index=True,
        group_expand='_group_expand_states')

    line_ids = fields.One2many(
        'uni.payment.plan.line', 'plan_id', string='Installment Lines',
        copy=True)
    line_count = fields.Integer(
        compute='_compute_line_count', string='Installments')
    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True, tracking=True)

    _sql_constraints = [
        ('unique_payment_plan_name', 'unique(name)',
         'Payment plan reference must be unique!'),
        ('check_total_positive', 'check(total_amount >= 0)',
         'Total amount cannot be negative!'),
        ('check_installments_positive', 'check(installments_count > 0)',
         'Installments count must be greater than zero!'),
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
                    'uni.payment.plan') or _('PP-NEW')
            if not vals.get('code'):
                vals['code'] = vals.get('name')
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Computed
    # ------------------------------------------------------------------
    @api.depends('line_ids.state', 'line_ids.amount',
                 'line_ids.payment_date')
    def _compute_paid_amount(self):
        """Sum of paid installment amounts."""
        for rec in self:
            paid = sum(rec.line_ids.filtered(
                lambda l: l.state == 'paid').mapped('amount'))
            rec.paid_amount = paid
            rec.remaining_amount = (rec.total_amount or 0.0) - paid

    @api.depends('line_ids')
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    # ------------------------------------------------------------------
    # Onchange
    # ------------------------------------------------------------------
    @api.onchange('student_id')
    def _onchange_student_id(self):
        if self.student_id:
            self.university_id = self.student_id.university_id

    @api.onchange('invoice_ids')
    def _onchange_invoice_ids(self):
        """Pre-fill total_amount from the sum of selected invoices' totals."""
        if self.invoice_ids:
            self.total_amount = sum(self.invoice_ids.mapped('amount_total'))

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def action_activate(self):
        """Activate the plan — generates installments if none exist."""
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError(_(
                    "Only draft payment plans can be activated (%s is %s).")
                    % (rec.display_name, rec.state))
            if not rec.line_ids:
                rec.action_generate_installments()
            if not rec.line_ids:
                raise ValidationError(_(
                    "Cannot activate payment plan %s without installments.")
                    % rec.display_name)
            rec.state = 'active'

    def action_cancel(self):
        """Cancel the payment plan."""
        for rec in self:
            if rec.state == 'cancelled':
                continue
            rec.state = 'cancelled'

    def action_draft(self):
        """Reset a cancelled plan back to draft."""
        for rec in self:
            if rec.state != 'cancelled':
                raise ValidationError(_(
                    "Only cancelled plans can be set back to draft "
                    "(%s is %s).") % (rec.display_name, rec.state))
            rec.state = 'draft'

    def action_complete(self):
        """Mark the plan as completed (when all installments are paid)."""
        for rec in self:
            if rec.state != 'active':
                raise ValidationError(_(
                    "Only active plans can be completed (%s is %s).")
                    % (rec.display_name, rec.state))
            unpaid = rec.line_ids.filtered(lambda l: l.state != 'paid')
            if unpaid:
                raise ValidationError(_(
                    "Cannot complete plan %s: %d installment(s) are not "
                    "yet paid.") % (rec.display_name, len(unpaid)))
            rec.state = 'completed'

    def _mark_overdue_installments(self):
        """Mark installments past their due date (and unpaid) as overdue."""
        today = fields.Date.context_today(self)
        for rec in self:
            for line in rec.line_ids.filtered(
                    lambda l: l.state == 'pending' and l.due_date < today):
                line.state = 'overdue'

    # ------------------------------------------------------------------
    # Installment generation
    # ------------------------------------------------------------------
    def action_generate_installments(self):
        """Generate payment plan lines based on the frequency and count.

        Each installment gets an equal share of the total amount. The
        due date of the first installment is the plan's ``start_date``,
        and subsequent installments are spaced by the ``frequency``.
        """
        from datetime import timedelta
        from dateutil.relativedelta import relativedelta

        freq_delta = {
            'weekly': timedelta(weeks=1),
            'bi_weekly': timedelta(weeks=2),
            'monthly': relativedelta(months=1),
            'quarterly': relativedelta(months=3),
        }
        for rec in self:
            if rec.installments_count <= 0:
                raise ValidationError(_(
                    "Installments count must be greater than zero for "
                    "plan %s.") % rec.display_name)
            # Clear existing generated lines that are still pending
            rec.line_ids.filtered(
                lambda l: l.state == 'pending' and not l.payment_date
            ).unlink()
            # Compute per-installment amount
            per_amount = rec.total_amount / rec.installments_count
            delta = freq_delta.get(rec.frequency, timedelta(days=30))
            current_date = rec.start_date or fields.Date.context_today(rec)
            new_lines = []
            for i in range(rec.installments_count):
                new_lines.append((0, 0, {
                    'sequence': (i + 1) * 10,
                    'due_date': current_date,
                    'amount': per_amount,
                    'state': 'pending',
                }))
                current_date = current_date + delta \
                    if isinstance(delta, timedelta) else \
                    current_date + delta
            rec.line_ids = new_lines
            rec.message_post(body=_(
                "%d installments generated.") % rec.installments_count)

    # ------------------------------------------------------------------
    # Smart-button actions
    # ------------------------------------------------------------------
    def action_view_lines(self):
        self.ensure_one()
        return {
            'name': _('Installments'),
            'type': 'ir.actions.act_window',
            'res_model': 'uni.payment.plan.line',
            'view_mode': 'list,form',
            'domain': [('plan_id', '=', self.id)],
            'context': {'default_plan_id': self.id},
        }

    def action_view_invoices(self):
        self.ensure_one()
        return {
            'name': _('Invoices'),
            'type': 'ir.actions.act_window',
            'res_model': 'uni.invoice.student',
            'view_mode': 'list,form',
            'domain': [('payment_plan_id', '=', self.id)],
        }

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('installments_count')
    def _check_installments_count(self):
        for rec in self:
            if rec.installments_count <= 0:
                raise ValidationError(_(
                    "Installments count must be greater than zero for %s.")
                    % rec.display_name)

    @api.constrains('total_amount', 'line_ids')
    def _check_lines_total_within_plan(self):
        """Soft check: sum of installment amounts should equal total_amount.

        We allow a small floating-point tolerance. Lines that were manually
        adjusted after generation might still be valid; we only raise if
        the difference exceeds 1 unit of currency.
        """
        for rec in self:
            if not rec.line_ids:
                continue
            lines_total = sum(rec.line_ids.mapped('amount'))
            if abs(lines_total - rec.total_amount) > 1.0:
                raise ValidationError(_(
                    "Sum of installment amounts (%(lines).2f) does not match "
                    "the plan total (%(total).2f) for %(plan)s.") % {
                    'lines': lines_total,
                    'total': rec.total_amount,
                    'plan': rec.display_name})


class UniPaymentPlanLine(models.Model):
    """قسط من خطة السداد — دفعة واحدة مجدولة بتاريخ استحقاق."""
    _name = 'uni.payment.plan.line'
    _description = 'Payment Plan Line'
    _order = 'plan_id, sequence, due_date'

    plan_id = fields.Many2one(
        'uni.payment.plan', string='Payment Plan', required=True,
        ondelete='cascade', index=True)
    sequence = fields.Integer(string='Sequence', default=10)
    due_date = fields.Date(
        string='Due Date', required=True, tracking=True,
        help='Date on which the installment becomes payable.')
    amount = fields.Float(
        string='Amount', digits=(16, 2), required=True, default=0.0,
        help='Amount due for this installment.')
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        related='plan_id.currency_id', store=True, readonly=True)
    payment_date = fields.Date(
        string='Payment Date', tracking=True,
        help='Date on which the installment was actually paid.')
    state = fields.Selection([
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
    ], string='State', default='pending', tracking=True, index=True,
        group_expand='_group_expand_state')
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('check_amount_positive', 'check(amount >= 0)',
         'Installment amount cannot be negative!'),
    ]

    # ------------------------------------------------------------------
    # Group expansion helper
    # ------------------------------------------------------------------
    def _group_expand_state(self, states, domain, order):
        return [key for key, _ in self._fields['state'].selection]

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def action_mark_paid(self):
        """Mark this installment as paid — sets the payment date."""
        for rec in self:
            if rec.state == 'paid':
                continue
            rec.write({
                'state': 'paid',
                'payment_date': fields.Date.context_today(rec),
            })

    def action_mark_pending(self):
        """Revert an installment to pending (clears payment date)."""
        for rec in self:
            rec.write({
                'state': 'pending',
                'payment_date': False,
            })

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('state', 'payment_date')
    def _check_paid_has_date(self):
        for rec in self:
            if rec.state == 'paid' and not rec.payment_date:
                raise ValidationError(_(
                    "A paid installment must have a payment date."))
