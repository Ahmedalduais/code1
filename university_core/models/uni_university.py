# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class UniUniversity(models.Model):
    """كيان الجامعة — يرث res.partner عبر التفويض."""
    _name = 'uni.university'
    _description = 'University'
    _inherits = {'res.partner': 'partner_id'}
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'name'

    partner_id = fields.Many2one('res.partner', string='Partner', required=True,
                                 ondelete='restrict', auto_join=True, index=True)
    code = fields.Char(string='University Code', required=True, copy=False, tracking=True, index=True)
    established_date = fields.Date(string='Established Date', tracking=True)
    accreditation_no = fields.Char(string='Accreditation Number', tracking=True)
    website_url = fields.Char(string='Website', related='partner_id.website', store=False)
    branch_ids = fields.One2many('uni.branch', 'university_id', string='Branches')
    college_ids = fields.One2many('uni.college', 'university_id', string='Colleges')
    branch_count = fields.Integer(compute='_compute_branch_count', string='Branch Count')
    college_count = fields.Integer(compute='_compute_college_count', string='College Count')
    logo = fields.Image(related='partner_id.image_1920', store=False)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)

    _sql_constraints = [
        ('unique_university_code', 'unique(code)', 'University code must be unique!'),
    ]

    @api.depends('branch_ids')
    def _compute_branch_count(self):
        for rec in self:
            rec.branch_count = len(rec.branch_ids)

    @api.depends('college_ids')
    def _compute_college_count(self):
        for rec in self:
            rec.college_count = len(rec.college_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('partner_id'):
                partner_vals = {
                    'name': vals.get('name', _('New University')),
                    'is_company': True,
                    'type': 'contact',
                }
                if vals.get('email'):
                    partner_vals['email'] = vals['email']
                if vals.get('phone'):
                    partner_vals['phone'] = vals['phone']
                partner = self.env['res.partner'].create(partner_vals)
                vals['partner_id'] = partner.id
        return super().create(vals_list)

    def action_view_branches(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Branches'),
            'res_model': 'uni.branch',
            'view_mode': 'list,form',
            'domain': [('university_id', '=', self.id)],
            'context': {'default_university_id': self.id},
        }

    def action_view_colleges(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Colleges'),
            'res_model': 'uni.college',
            'view_mode': 'list,form',
            'domain': [('university_id', '=', self.id)],
            'context': {'default_university_id': self.id},
        }
