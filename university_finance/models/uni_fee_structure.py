# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniFeeStructure(models.Model):
    """هيكل الرسوم — القالب المالي المرتبط بالبرنامج والمستوى والفصل.

    يمثّل هذا النموذج عقداً مالياً يحدد الرسوم المفروضة على مجموعة محددة
    من الطلاب (على مستوى الجامعة/الكلية/القسم/البرنامج/المستوى/الفصل).
    يتكوّن الهيكل من:
        * بنود الهيكل (``uni.fee.structure.line``): كل بند يحدّد نوع الرسوم
          ومبلغها
        * الأقساط (``uni.fee.installment``): جدولة المبلغ الإجمالي على دفعات
          مع تواريخ استحقاق وغرامات تأخير

    سير حياة الهيكل: draft → active → closed، مع إمكانية إعادة الفتح للتعديل.
    """
    _name = 'uni.fee.structure'
    _description = 'Fee Structure'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'university_id, college_id, program_id, effective_date desc'

    name = fields.Char(
        string='Structure Name', required=True, tracking=True, translate=True,
        help='Human-readable label of the fee structure.')
    code = fields.Char(
        string='Code', required=True, copy=False, tracking=True, index=True,
        help='Short unique code identifying this fee structure.')

    # ------------------------------------------------------------------
    # Scope: university / college / department / program / level / term
    # ------------------------------------------------------------------
    university_id = fields.Many2one(
        'uni.university', string='University', required=True,
        ondelete='restrict', tracking=True, index=True)
    college_id = fields.Many2one(
        'uni.college', string='College', ondelete='restrict',
        tracking=True, index=True)
    department_id = fields.Many2one(
        'uni.department', string='Department', ondelete='restrict',
        tracking=True, index=True)
    program_id = fields.Many2one(
        'uni.program', string='Program', ondelete='restrict',
        tracking=True, index=True)
    level_id = fields.Many2one(
        'uni.program.level', string='Program Level', ondelete='restrict',
        tracking=True, index=True,
        help='Optional: limit the structure to a specific program level '
             '(e.g. Bachelor, Master).')
    academic_term_id = fields.Many2one(
        'uni.academic.term', string='Academic Term', ondelete='restrict',
        tracking=True, index=True,
        help='Optional: limit the structure to a specific academic term.')
    academic_year_id = fields.Many2one(
        'uni.academic.year', string='Academic Year',
        related='academic_term_id.academic_year_id', store=True,
        help='Academic year (derived from the selected term).')

    # ------------------------------------------------------------------
    # Validity window
    # ------------------------------------------------------------------
    effective_date = fields.Date(
        string='Effective Date', tracking=True,
        help='Date from which this fee structure becomes applicable.')
    expiry_date = fields.Date(
        string='Expiry Date', tracking=True,
        help='Date after which this fee structure is no longer applicable.')

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('closed', 'Closed'),
    ], string='Status', default='draft', tracking=True, index=True,
        group_expand='_group_expand_states')

    # ------------------------------------------------------------------
    # Totals & currency
    # ------------------------------------------------------------------
    total_amount = fields.Float(
        string='Total Amount', digits=(16, 2), default=0.0,
        compute='_compute_total', store=True, tracking=True,
        help='Sum of all fee structure line amounts.')
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True, tracking=True,
        help='Currency used for all amounts in this fee structure.')

    # ------------------------------------------------------------------
    # Relations
    # ------------------------------------------------------------------
    installment_ids = fields.One2many(
        'uni.fee.installment', 'fee_structure_id', string='Installments',
        copy=True)
    line_ids = fields.One2many(
        'uni.fee.structure.line', 'structure_id', string='Fee Lines',
        copy=True)
    line_count = fields.Integer(
        compute='_compute_line_count', string='Fee Lines')
    installment_count = fields.Integer(
        compute='_compute_installment_count', string='Installments')
    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True, tracking=True)

    _sql_constraints = [
        ('unique_fee_structure_code', 'unique(code)',
         'Fee structure code must be unique!'),
        ('check_dates', 'check(expiry_date IS NULL OR effective_date IS NULL '
                        'OR expiry_date >= effective_date)',
         'Expiry date cannot be earlier than effective date!'),
        ('check_total_positive', 'check(total_amount >= 0)',
         'Total amount cannot be negative!'),
    ]

    # ------------------------------------------------------------------
    # Group expansion helper
    # ------------------------------------------------------------------
    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in self._fields['state'].selection]

    # ------------------------------------------------------------------
    # Computed
    # ------------------------------------------------------------------
    @api.depends('line_ids.amount', 'line_ids')
    def _compute_total(self):
        """Sum of all fee structure line amounts."""
        for rec in self:
            rec.total_amount = sum(rec.line_ids.mapped('amount'))

    @api.depends('line_ids')
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    @api.depends('installment_ids')
    def _compute_installment_count(self):
        for rec in self:
            rec.installment_count = len(rec.installment_ids)

    # ------------------------------------------------------------------
    # Onchange — keep university hierarchy consistent
    # ------------------------------------------------------------------
    @api.onchange('college_id')
    def _onchange_college_id(self):
        if self.college_id:
            self.university_id = self.college_id.university_id

    @api.onchange('department_id')
    def _onchange_department_id(self):
        if self.department_id:
            self.college_id = self.department_id.college_id
            self.university_id = self.department_id.university_id

    @api.onchange('program_id')
    def _onchange_program_id(self):
        if self.program_id:
            self.college_id = self.program_id.college_id
            self.department_id = self.program_id.department_id
            self.university_id = self.program_id.university_id
            if self.program_id.level_id:
                self.level_id = self.program_id.level_id

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def action_activate(self):
        """Activate the fee structure so it can be selected on invoices."""
        for rec in self:
            if not rec.line_ids:
                raise ValidationError(_(
                    "Fee structure %s must have at least one fee line "
                    "before it can be activated.") % rec.display_name)
            rec.state = 'active'

    def action_close(self):
        """Close the fee structure — prevents future use."""
        for rec in self:
            rec.state = 'closed'

    def action_draft(self):
        """Re-open the fee structure for editing."""
        for rec in self:
            rec.state = 'draft'

    # ------------------------------------------------------------------
    # Smart-button actions
    # ------------------------------------------------------------------
    def action_view_installments(self):
        self.ensure_one()
        return {
            'name': _('Installments'),
            'type': 'ir.actions.act_window',
            'res_model': 'uni.fee.installment',
            'view_mode': 'list,form',
            'domain': [('fee_structure_id', '=', self.id)],
            'context': {'default_fee_structure_id': self.id,
                        'default_currency_id': self.currency_id.id},
        }

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('effective_date', 'expiry_date')
    def _check_validity_window(self):
        for rec in self:
            if rec.effective_date and rec.expiry_date and \
                    rec.expiry_date < rec.effective_date:
                raise ValidationError(_(
                    "Expiry date cannot be earlier than effective date "
                    "for fee structure %s.") % rec.display_name)

    @api.constrains('line_ids')
    def _check_unique_fee_type_per_structure(self):
        """Prevent the same fee type from appearing twice in one structure."""
        for rec in self:
            seen = set()
            for line in rec.line_ids:
                if not line.fee_type_id:
                    continue
                key = line.fee_type_id.id
                if key in seen:
                    raise ValidationError(_(
                        "Fee type %s appears more than once in fee structure %s."
                        " Each fee type should be listed only once per structure."
                        ) % (line.fee_type_id.display_name, rec.display_name))
                seen.add(key)


class UniFeeStructureLine(models.Model):
    """بند هيكل الرسوم — يحدّد نوع الرسوم ومبلغها داخل هيكل مالي."""
    _name = 'uni.fee.structure.line'
    _description = 'Fee Structure Line'
    _order = 'sequence, fee_type_id'

    structure_id = fields.Many2one(
        'uni.fee.structure', string='Fee Structure', required=True,
        ondelete='cascade', index=True)
    fee_type_id = fields.Many2one(
        'uni.fee.type', string='Fee Type', required=True, ondelete='restrict',
        index=True,
        help='Type of fee being charged by this line.')
    fee_type_code = fields.Char(
        string='Fee Type Code', related='fee_type_id.code', store=True)
    amount = fields.Float(
        string='Amount', digits=(16, 2), required=True, default=0.0,
        help='Amount charged for this fee type in the structure currency.')
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        related='structure_id.currency_id', store=True, readonly=True)
    sequence = fields.Integer(string='Sequence', default=10)
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('check_amount_positive', 'check(amount >= 0)',
         'Amount cannot be negative!'),
    ]

    @api.onchange('fee_type_id')
    def _onchange_fee_type_id(self):
        """Pre-fill amount with the fee type's default amount."""
        if self.fee_type_id and not self.amount:
            self.amount = self.fee_type_id.default_amount

    @api.constrains('amount')
    def _check_amount(self):
        for rec in self:
            if rec.amount < 0:
                raise ValidationError(_(
                    "Amount for fee type %s cannot be negative."
                    ) % (rec.fee_type_id.display_name or _('Unknown')))


class UniFeeInstallment(models.Model):
    """قسط من هيكل الرسوم — يحدّد جدولة المبلغ على دفعات."""
    _name = 'uni.fee.installment'
    _description = 'Fee Installment'
    _order = 'fee_structure_id, sequence, installment_number'

    fee_structure_id = fields.Many2one(
        'uni.fee.structure', string='Fee Structure', required=True,
        ondelete='cascade', index=True)
    name = fields.Char(
        string='Name', required=True, tracking=True,
        help='Display label of the installment (e.g. "First Installment").')
    sequence = fields.Integer(string='Sequence', default=10)
    installment_number = fields.Integer(
        string='Installment #', default=1, tracking=True,
        help='Order of the installment within the structure (1, 2, 3...).')
    due_date = fields.Date(
        string='Due Date', required=True, tracking=True,
        help='Date on which the installment becomes payable.')
    amount = fields.Float(
        string='Amount', digits=(16, 2), required=True, default=0.0,
        help='Fixed amount due for this installment.')
    percentage = fields.Float(
        string='Percentage', digits=(5, 2), default=0.0,
        help='Percentage of the total fee that this installment represents.')
    grace_period_days = fields.Integer(
        string='Grace Period (days)', default=7,
        help='Number of days after the due date during which no late fee '
             'is charged.')
    late_fee_amount = fields.Float(
        string='Late Fee Amount', digits=(16, 2), default=0.0,
        help='Flat late fee charged after the grace period expires.')
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        related='fee_structure_id.currency_id', store=True, readonly=True)
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('check_amount_positive', 'check(amount >= 0)',
         'Installment amount cannot be negative!'),
        ('check_percentage_range',
         'check(percentage >= 0 AND percentage <= 100)',
         'Percentage must be between 0 and 100!'),
        ('check_grace_period', 'check(grace_period_days >= 0)',
         'Grace period cannot be negative!'),
        ('check_installment_number', 'check(installment_number > 0)',
         'Installment number must be greater than zero!'),
    ]

    @api.constrains('due_date')
    def _check_due_date_validity(self):
        """Validate due date against the parent structure's validity window."""
        for rec in self:
            if not rec.due_date:
                continue
            structure = rec.fee_structure_id
            if not structure:
                continue
            if structure.effective_date and rec.due_date < structure.effective_date:
                raise ValidationError(_(
                    "Installment %s due date (%(due)s) cannot be earlier than "
                    "the structure effective date (%(eff)s).") % {
                    'name': rec.name,
                    'due': rec.due_date,
                    'eff': structure.effective_date})
            if structure.expiry_date and rec.due_date > structure.expiry_date:
                raise ValidationError(_(
                    "Installment %s due date (%(due)s) cannot be later than "
                    "the structure expiry date (%(exp)s).") % {
                    'name': rec.name,
                    'due': rec.due_date,
                    'exp': structure.expiry_date})

    @api.constrains('amount', 'percentage')
    def _check_amount_or_percentage(self):
        """Either an amount or a percentage must be provided."""
        for rec in self:
            if rec.amount <= 0 and rec.percentage <= 0:
                raise ValidationError(_(
                    "Installment %s must have either a positive amount or a "
                    "positive percentage.") % rec.display_name)
