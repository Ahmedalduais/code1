# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniAccreditationBody(models.Model):
    """جهة الاعتماد — يمثل جهة اعتماد أكاديمي (وطنية / إقليمية / دولية / مهنية).

    تربط الجهة بالمعايير التي تصدرها وببرامج الاعتماد المرتبطة بها.
    تستخدم res.partner عبر partner_id لتخزين بيانات التواصل القياسية.
    """
    _name = 'uni.accreditation.body'
    _description = 'Accreditation Body'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'accreditation_type, name'

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Name', required=True, tracking=True, translate=True, index=True,
        help='Official name of the accreditation body.')
    code = fields.Char(
        string='Code', required=True, tracking=True, copy=False, index=True,
        help='Short unique code identifying the accreditation body '
             '(e.g. NCAAA, ABET, AACSB).')
    partner_id = fields.Many2one(
        'res.partner', string='Contact Partner',
        ondelete='restrict', tracking=True,
        help='Contact partner holding address, phone, email and country.')
    country_id = fields.Many2one(
        'res.country', string='Country',
        related='partner_id.country_id', store=True, index=True,
        help='Country of the accreditation body (derived from the partner).')
    website = fields.Char(
        string='Website', tracking=True,
        help='Official website URL of the accreditation body.')

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------
    accreditation_type = fields.Selection([
        ('national', 'National'),
        ('regional', 'Regional'),
        ('international', 'International'),
        ('professional', 'Professional'),
    ], string='Accreditation Type', required=True, default='national',
        tracking=True, index=True,
        help='Classification of the accreditation body scope.')

    # ------------------------------------------------------------------
    # Contact details (also stored on partner, but kept here for quick access)
    # ------------------------------------------------------------------
    contact_person = fields.Char(
        string='Contact Person', tracking=True,
        help='Name of the primary contact person at the accreditation body.')
    contact_email = fields.Char(
        string='Contact Email', tracking=True,
        help='Email address of the primary contact.')
    contact_phone = fields.Char(
        string='Contact Phone', tracking=True,
        help='Phone number of the primary contact.')

    # ------------------------------------------------------------------
    # Misc
    # ------------------------------------------------------------------
    establishment_date = fields.Date(
        string='Establishment Date', tracking=True,
        help='Date when the accreditation body was officially established.')
    description = fields.Text(string='Description')

    # ------------------------------------------------------------------
    # Relations (computed counts for smart buttons)
    # ------------------------------------------------------------------
    standard_ids = fields.One2many(
        'uni.accreditation.standard', 'accreditation_body_id',
        string='Standards')
    standard_count = fields.Integer(
        compute='_compute_standard_count', string='Standards')
    program_ids = fields.One2many(
        'uni.accreditation.program', 'accreditation_body_id',
        string='Accredited Programs')
    program_count = fields.Integer(
        compute='_compute_program_count', string='Programs')

    # ------------------------------------------------------------------
    # SQL constraints
    # ------------------------------------------------------------------
    _sql_constraints = [
        ('unique_code',
         'unique(code)',
         'The accreditation body code must be unique!'),
        ('unique_name',
         'unique(name)',
         'The accreditation body name must be unique!'),
    ]

    # ------------------------------------------------------------------
    # Computed counts
    # ------------------------------------------------------------------
    @api.depends('standard_ids')
    def _compute_standard_count(self):
        for rec in self:
            rec.standard_count = len(rec.standard_ids)

    @api.depends('program_ids')
    def _compute_program_count(self):
        for rec in self:
            rec.program_count = len(rec.program_ids)

    # ------------------------------------------------------------------
    # Onchange — keep contact in sync with partner if available
    # ------------------------------------------------------------------
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """Pre-fill contact details from the chosen partner."""
        if self.partner_id:
            if not self.contact_email and self.partner_id.email:
                self.contact_email = self.partner_id.email
            if not self.contact_phone and self.partner_id.phone:
                self.contact_phone = self.partner_id.phone
            if not self.website and self.partner_id.website:
                self.website = self.partner_id.website

    # ------------------------------------------------------------------
    # Validations
    # ------------------------------------------------------------------
    @api.constrains('contact_email')
    def _check_contact_email(self):
        for rec in self:
            if rec.contact_email and '@' not in rec.contact_email:
                raise ValidationError(_(
                    "The contact email '%s' is not a valid email address "
                    "for accreditation body %s.") %
                    (rec.contact_email, rec.display_name))

    @api.constrains('establishment_date')
    def _check_establishment_date(self):
        for rec in self:
            if rec.establishment_date and rec.establishment_date > fields.Date.context_today(rec):
                raise ValidationError(_(
                    "Establishment date cannot be in the future "
                    "for accreditation body %s.") % rec.display_name)

    # ------------------------------------------------------------------
    # Smart buttons
    # ------------------------------------------------------------------
    def action_view_standards(self):
        self.ensure_one()
        return {
            'name': _('Standards'),
            'type': 'ir.actions.act_window',
            'res_model': 'uni.accreditation.standard',
            'view_mode': 'list,form',
            'domain': [('accreditation_body_id', '=', self.id)],
            'context': {'default_accreditation_body_id': self.id},
        }

    def action_view_programs(self):
        self.ensure_one()
        return {
            'name': _('Accredited Programs'),
            'type': 'ir.actions.act_window',
            'res_model': 'uni.accreditation.program',
            'view_mode': 'list,form',
            'domain': [('accreditation_body_id', '=', self.id)],
            'context': {'default_accreditation_body_id': self.id},
        }
