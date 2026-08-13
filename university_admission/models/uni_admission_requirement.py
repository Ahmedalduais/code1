# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniAdmissionRequirement(models.Model):
    """متطلبات القبول — قائمة قابلة لإعادة الاستخدام من المتطلبات
    (وثائق، اختبارات، مقابلات، مدفوعات...).

    يتم استهلاك هذه المتطلبات على مستوى كل طلب قبول عبر
    ``uni.admission.requirement.line`` التي تربط المتطلب بالطلب
    وتسجّل حالة الاستيفاء والمرفق المرتبط به.
    """
    _name = 'uni.admission.requirement'
    _description = 'Admission Requirement'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'requirement_type, sequence, name'

    name = fields.Char(
        string='Requirement Name', required=True, translate=True, tracking=True,
        help='Human-readable name of the requirement.')
    code = fields.Char(
        string='Code', required=True, copy=False, index=True, tracking=True,
        help='Short unique code identifying this requirement (e.g. HS-TRANSCRIPT).')
    description = fields.Text(string='Description', translate=True)
    requirement_type = fields.Selection([
        ('document', 'Document'),
        ('test', 'Test'),
        ('interview', 'Interview'),
        ('payment', 'Payment'),
        ('other', 'Other'),
    ], string='Type', default='document', required=True, tracking=True, index=True)
    is_mandatory = fields.Boolean(
        string='Mandatory', default=True, tracking=True,
        help='If checked, every application must fulfill this requirement.')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(default=True)
    color = fields.Integer(string='Color Index')

    line_ids = fields.One2many(
        'uni.admission.requirement.line', 'requirement_id', string='Application Lines')
    line_count = fields.Integer(
        compute='_compute_line_count', string='Used In Applications')

    _sql_constraints = [
        ('unique_requirement_code', 'unique(code)',
         'Requirement code must be unique!'),
    ]

    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    def action_open_lines(self):
        """Open the requirement-line records linked to this requirement."""
        self.ensure_one()
        return {
            'name': _('Requirement Lines'),
            'type': 'ir.actions.act_window',
            'res_model': 'uni.admission.requirement.line',
            'view_mode': 'list,form',
            'domain': [('requirement_id', '=', self.id)],
            'context': {'default_requirement_id': self.id},
        }


class UniAdmissionRequirementLine(models.Model):
    """خط متطلب الطلب — ربط بين طلب القبول والمتطلب المطلوب.

    يسجّل حالة الاستيفاء + المرفق المرتبط + ملاحظات المنجز.
    """
    _name = 'uni.admission.requirement.line'
    _description = 'Admission Requirement Line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'application_id, requirement_id'

    application_id = fields.Many2one(
        'uni.admission.application', string='Application',
        required=True, ondelete='cascade', index=True, tracking=True)
    requirement_id = fields.Many2one(
        'uni.admission.requirement', string='Requirement',
        required=True, ondelete='restrict', index=True, tracking=True)
    requirement_type = fields.Selection(
        related='requirement_id.requirement_type', store=True)
    is_mandatory = fields.Boolean(
        related='requirement_id.is_mandatory', store=True)
    is_fulfilled = fields.Boolean(
        string='Fulfilled', default=False, tracking=True,
        help='Whether this requirement has been fulfilled by the applicant.')
    fulfilled_date = fields.Datetime(
        string='Fulfilled Date', tracking=True,
        help='Date and time at which the requirement was marked fulfilled.')
    file = fields.Binary(
        string='Attachment', attachment=True,
        help='Uploaded file evidencing this requirement (e.g. scanned transcript).')
    filename = fields.Char(string='Filename')
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('unique_application_requirement',
         'unique(application_id, requirement_id)',
         'A requirement can only be linked once per application!'),
    ]

    @api.onchange('is_fulfilled')
    def _onchange_is_fulfilled(self):
        """Auto-stamp the fulfilled date when the flag is set."""
        for rec in self:
            if rec.is_fulfilled and not rec.fulfilled_date:
                rec.fulfilled_date = fields.Datetime.now()
            elif not rec.is_fulfilled:
                rec.fulfilled_date = False

    def action_mark_fulfilled(self):
        """Mark the line as fulfilled right now."""
        for rec in self:
            rec.write({
                'is_fulfilled': True,
                'fulfilled_date': fields.Datetime.now(),
            })

    def action_mark_unfulfilled(self):
        """Reset the fulfillment flag."""
        for rec in self:
            rec.write({
                'is_fulfilled': False,
                'fulfilled_date': False,
            })

    @api.constrains('is_fulfilled', 'file', 'requirement_id')
    def _check_document_has_file(self):
        """A document-type requirement cannot be marked fulfilled without a file."""
        for rec in self:
            if rec.is_fulfilled \
                    and rec.requirement_type == 'document' \
                    and not rec.file:
                raise ValidationError(_(
                    "Requirement '%(req)s' is a document and cannot be marked "
                    "fulfilled without an attached file (application %(app)s).")
                    % {'req': rec.requirement_id.display_name,
                       'app': rec.application_id.display_name})
