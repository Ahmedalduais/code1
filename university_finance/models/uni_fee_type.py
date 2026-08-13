# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniFeeType(models.Model):
    """نوع الرسوم — يصف صنفاً واحداً من الرسوم الجامعية.

    يُستخدم هذا النموذج كمرجع رئيسي لجميع أنواع الرسوم التي قد تُفرض على
    الطلاب (رسوم دراسية، مختبر، مكتبة، نشاط، تسجيل، تخرج، سكن، نقل،
    غرامة تأخير، أخرى). تُربط الأنواع بهياكل الرسوم والفواتير الطلابية.

    يوفّر النموذج:
        * تصنيفاً موحداً للرسوم عبر الحقل ``fee_category``
        * دعماً للرسوم المتكررة (سنوية/فصلية) عبر ``is_recurring``
        * مبلغاً افتراضياً يُقترح عند الإنشاء (``default_amount``)
        * عملة افتراضية مستمدة من الشركة الحالية
    """
    _name = 'uni.fee.type'
    _description = 'Fee Type'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'fee_category, sequence, name'

    name = fields.Char(
        string='Fee Type Name', required=True, tracking=True, translate=True,
        help='Human-readable label of the fee type (e.g. "Tuition Fee").')
    code = fields.Char(
        string='Code', required=True, copy=False, tracking=True, index=True,
        help='Short internal code used in invoices and reports (e.g. TUITION).')
    description = fields.Text(string='Description', translate=True)
    fee_category = fields.Selection([
        ('tuition', 'Tuition'),
        ('lab', 'Lab Fee'),
        ('library', 'Library Fee'),
        ('activity', 'Activity Fee'),
        ('registration', 'Registration Fee'),
        ('graduation', 'Graduation Fee'),
        ('housing', 'Housing Fee'),
        ('transport', 'Transport Fee'),
        ('late_penalty', 'Late Payment Penalty'),
        ('other', 'Other'),
    ], string='Fee Category', required=True, default='tuition',
        tracking=True, index=True,
        help='Functional classification of the fee type.')
    is_recurring = fields.Boolean(
        string='Recurring', default=False, tracking=True,
        help='Check if this fee is charged every term or year '
             '(e.g. tuition, library). One-off fees (graduation, '
             'registration) should remain unchecked.')
    default_amount = fields.Float(
        string='Default Amount', digits=(16, 2), default=0.0, tracking=True,
        help='Suggested amount used when a fee of this type is added to '
             'a fee structure or a student invoice. The amount can be '
             'overridden on each individual line.')
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True, tracking=True,
        help='Currency used for the default amount.')
    sequence = fields.Integer(string='Sequence', default=10,
                              help='Used to order fee types in lists.')
    active = fields.Boolean(default=True, tracking=True)

    _sql_constraints = [
        ('unique_fee_type_code', 'unique(code)',
         'Fee type code must be unique!'),
        ('check_default_amount_positive',
         'check(default_amount >= 0)',
         'Default amount cannot be negative!'),
    ]

    @api.constrains('code')
    def _check_code_nonempty(self):
        for rec in self:
            if not rec.code or not rec.code.strip():
                raise ValidationError(_(
                    "Fee type code cannot be empty for %s.") % rec.display_name)

    def _compute_display_name(self):
        """Show code alongside the name for clarity in selections."""
        for rec in self:
            rec.display_name = _('%(name)s [%(code)s]') % {
                'name': rec.name, 'code': rec.code}
