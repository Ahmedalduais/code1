# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniScholarshipType(models.Model):
    """نوع المنحة — يصنّف المنح الدراسية حسب طبيعتها.

    يوفّر النموذج مرجعاً موحداً لأنواع المنح (كاملة، جزئية، استحقاق،
    احتياج، رياضة، تابعين موظفين...) مع نسبة افتراضية ومبلغ افتراضي
    يُقترحان عند إنشاء منحة جديدة.
    """
    _name = 'uni.scholarship.type'
    _description = 'Scholarship Type'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'sequence, name'

    name = fields.Char(
        string='Scholarship Type', required=True, tracking=True, translate=True,
        help='Human-readable label of the scholarship type.')
    code = fields.Char(
        string='Code', required=True, copy=False, tracking=True, index=True,
        help='Short unique code identifying the scholarship type.')
    description = fields.Text(string='Description', translate=True)
    scholarship_nature = fields.Selection([
        ('full', 'Full Scholarship'),
        ('partial', 'Partial Scholarship'),
        ('merit', 'Merit-Based'),
        ('need_based', 'Need-Based'),
        ('sports', 'Sports Scholarship'),
        ('employee_dependent', 'Employee Dependent'),
    ], string='Nature', required=True, default='full',
        tracking=True, index=True,
        help='Functional classification of the scholarship.')
    default_percentage = fields.Float(
        string='Default Percentage', digits=(5, 2), default=100.0,
        tracking=True,
        help='Default discount percentage suggested on new scholarships '
             'of this type (0–100).')
    default_amount = fields.Float(
        string='Default Amount', digits=(16, 2), default=0.0, tracking=True,
        help='Default fixed discount amount suggested on new scholarships.')
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True, tracking=True)
    sequence = fields.Integer(string='Sequence', default=10)
    is_active = fields.Boolean(
        string='Currently Offered', default=True, tracking=True,
        help='Indicates whether this scholarship type is currently offered '
             'to students. Untick to retire a scholarship type without '
             'deleting existing scholarships.')
    active = fields.Boolean(default=True, tracking=True)

    _sql_constraints = [
        ('unique_scholarship_type_code', 'unique(code)',
         'Scholarship type code must be unique!'),
        ('check_default_percentage',
         'check(default_percentage >= 0 AND default_percentage <= 100)',
         'Default percentage must be between 0 and 100!'),
        ('check_default_amount_positive',
         'check(default_amount >= 0)',
         'Default amount cannot be negative!'),
    ]


class UniScholarship(models.Model):
    """المنحة الدراسية — خصم مالي ممنوح لطالب على فترة محددة.

    تربط المنحة طالباً بنوع منحة، وتحدّد نسبة الخصم أو مبلغه الثابت،
    وأنواع الرسوم التي تغطّيها. تمر المنحة بسير اعتماد كامل:
    ``draft → pending → approved → active → terminated``، مع رفض ممكن في
    الطور ``pending``.

    عند تفعيل المنحة، يمكن استخدامها كخصم على فاتورة الطالب الطلابية.
    """
    _name = 'uni.scholarship'
    _description = 'Scholarship'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'academic_term_id desc, student_id'

    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True,
        default=lambda self: _('New'), index=True, tracking=True,
        help='Unique reference number (auto-generated via sequence SCH/...).')
    code = fields.Char(
        string='Code', copy=False, tracking=True, index=True,
        help='Optional human-friendly code; if left empty, the reference '
             'is used.')

    student_id = fields.Many2one(
        'uni.student', string='Student', required=True, ondelete='restrict',
        tracking=True, index=True)
    scholarship_type_id = fields.Many2one(
        'uni.scholarship.type', string='Scholarship Type', required=True,
        ondelete='restrict', tracking=True, index=True)
    university_id = fields.Many2one(
        'uni.university', string='University',
        related='student_id.university_id', store=True, readonly=True,
        tracking=True, index=True)
    academic_term_id = fields.Many2one(
        'uni.academic.term', string='Academic Term', ondelete='restrict',
        tracking=True, index=True)
    academic_year_id = fields.Many2one(
        'uni.academic.year', string='Academic Year', ondelete='restrict',
        tracking=True, index=True,
        help='Academic year the scholarship applies to.')

    start_date = fields.Date(string='Start Date', tracking=True)
    end_date = fields.Date(string='End Date', tracking=True,
                           help='Date after which the scholarship expires.')

    discount_percentage = fields.Float(
        string='Discount %', digits=(5, 2), default=100.0, tracking=True,
        help='Percentage of the covered fees to be discounted (0–100).')
    discount_amount = fields.Float(
        string='Discount Amount', digits=(16, 2), default=0.0, tracking=True,
        help='Optional fixed discount amount (used when percentage is 0).')
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True, tracking=True)

    covered_fee_type_ids = fields.Many2many(
        'uni.fee.type', string='Covered Fee Types',
        help='Fee types covered by this scholarship. Leave empty to cover '
             'all fee types.')
    reason = fields.Text(string='Reason', tracking=True,
                         help='Justification for granting this scholarship.')

    approval_status = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('active', 'Active'),
        ('terminated', 'Terminated'),
    ], string='Approval Status', default='draft', tracking=True, index=True,
        group_expand='_group_expand_approval_status')
    approved_by = fields.Many2one(
        'res.users', string='Approved By', copy=False, readonly=True,
        tracking=True)
    approved_date = fields.Datetime(
        string='Approved Date', copy=False, readonly=True, tracking=True)
    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True, tracking=True)

    # ------------------------------------------------------------------
    # Relations & counts
    # ------------------------------------------------------------------
    invoice_ids = fields.One2many(
        'uni.invoice.student', 'scholarship_id', string='Linked Invoices')
    invoice_count = fields.Integer(
        compute='_compute_invoice_count', string='Invoices')

    _sql_constraints = [
        ('unique_scholarship_name', 'unique(name)',
         'Scholarship reference must be unique!'),
        ('check_discount_percentage',
         'check(discount_percentage >= 0 AND discount_percentage <= 100)',
         'Discount percentage must be between 0 and 100!'),
        ('check_discount_amount_positive',
         'check(discount_amount >= 0)',
         'Discount amount cannot be negative!'),
        ('check_dates',
         'check(end_date IS NULL OR start_date IS NULL '
                'OR end_date >= start_date)',
         'End date cannot be earlier than start date!'),
    ]

    # ------------------------------------------------------------------
    # Group expansion helper
    # ------------------------------------------------------------------
    def _group_expand_approval_status(self, states, domain, order):
        return [key for key, _ in self._fields['approval_status'].selection]

    # ------------------------------------------------------------------
    # Create — auto-generate reference
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.scholarship') or _('SCH-NEW')
            if not vals.get('code'):
                vals['code'] = vals.get('name')
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Onchange — pre-fill discount values from the scholarship type
    # ------------------------------------------------------------------
    @api.onchange('scholarship_type_id')
    def _onchange_scholarship_type_id(self):
        if self.scholarship_type_id:
            t = self.scholarship_type_id
            if not self.discount_percentage:
                self.discount_percentage = t.default_percentage
            if not self.discount_amount:
                self.discount_amount = t.default_amount

    @api.onchange('student_id')
    def _onchange_student_id(self):
        if self.student_id:
            self.university_id = self.student_id.university_id

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def action_submit(self):
        """Submit the scholarship for approval."""
        for rec in self:
            if rec.approval_status != 'draft':
                raise ValidationError(_(
                    "Only draft scholarships can be submitted for approval "
                    "(%s is %s).") % (rec.display_name, rec.approval_status))
            rec.approval_status = 'pending'

    def action_approve(self):
        """Approve the scholarship — sets approver and timestamp."""
        for rec in self:
            if rec.approval_status != 'pending':
                raise ValidationError(_(
                    "Only scholarships pending approval can be approved "
                    "(%s is %s).") % (rec.display_name, rec.approval_status))
            rec.write({
                'approval_status': 'approved',
                'approved_by': self.env.uid,
                'approved_date': fields.Datetime.now(),
            })

    def action_reject(self):
        """Reject the scholarship — only pending scholarships can be rejected."""
        for rec in self:
            if rec.approval_status != 'pending':
                raise ValidationError(_(
                    "Only scholarships pending approval can be rejected "
                    "(%s is %s).") % (rec.display_name, rec.approval_status))
            rec.approval_status = 'rejected'

    def action_activate(self):
        """Activate the scholarship so it can be applied on invoices."""
        for rec in self:
            if rec.approval_status != 'approved':
                raise ValidationError(_(
                    "Only approved scholarships can be activated "
                    "(%s is %s).") % (rec.display_name, rec.approval_status))
            if not rec.start_date:
                rec.start_date = fields.Date.context_today(rec)
            rec.approval_status = 'active'

    def action_terminate(self):
        """Terminate an active scholarship — ends the discount early."""
        for rec in self:
            if rec.approval_status != 'active':
                raise ValidationError(_(
                    "Only active scholarships can be terminated "
                    "(%s is %s).") % (rec.display_name, rec.approval_status))
            if not rec.end_date:
                rec.end_date = fields.Date.context_today(rec)
            rec.approval_status = 'terminated'

    def action_draft(self):
        """Reset a rejected scholarship back to draft."""
        for rec in self:
            if rec.approval_status != 'rejected':
                raise ValidationError(_(
                    "Only rejected scholarships can be set back to draft "
                    "(%s is %s).") % (rec.display_name, rec.approval_status))
            rec.approval_status = 'draft'

    # ------------------------------------------------------------------
    # Smart-button actions
    # ------------------------------------------------------------------
    def action_view_invoices(self):
        self.ensure_one()
        return {
            'name': _('Linked Invoices'),
            'type': 'ir.actions.act_window',
            'res_model': 'uni.invoice.student',
            'view_mode': 'list,form',
            'domain': [('scholarship_id', '=', self.id)],
            'context': {'default_scholarship_id': self.id,
                        'default_student_id': self.student_id.id},
        }

    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = len(rec.invoice_ids)

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for rec in self:
            if rec.start_date and rec.end_date and \
                    rec.end_date < rec.start_date:
                raise ValidationError(_(
                    "Scholarship end date cannot be earlier than start date "
                    "for %s.") % rec.display_name)

    @api.constrains('discount_percentage')
    def _check_discount_percentage(self):
        for rec in self:
            if not (0 <= rec.discount_percentage <= 100):
                raise ValidationError(_(
                    "Discount percentage for scholarship %s must be between "
                    "0 and 100.") % rec.display_name)

    @api.constrains('approval_status', 'start_date', 'end_date')
    def _check_active_dates(self):
        """Active scholarships must have a start date."""
        for rec in self:
            if rec.approval_status == 'active' and not rec.start_date:
                raise ValidationError(_(
                    "Active scholarship %s must have a start date.")
                    % rec.display_name)
