# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class UniPerson(models.Model):
    """نموذج الأشخاص الأساسي — يرث res.partner عبر التفويض."""
    _name = 'uni.person'
    _description = 'University Person'
    _inherits = {'res.partner': 'partner_id'}
    _inherit = ['mail.thread', 'mail.activity.mixin',
                'uni.mixin.archivable', 'uni.person.mixin']
    _order = 'name'

    partner_id = fields.Many2one('res.partner', string='Partner', required=True,
                                 ondelete='restrict', auto_join=True, index=True)
    university_id = fields.Many2one('uni.university', string='University',
                                    required=True, ondelete='restrict', tracking=True, index=True)
    person_type = fields.Selection([
        ('student', 'Student'),
        ('faculty', 'Faculty'),
        ('staff', 'Staff'),
        ('other', 'Other'),
    ], string='Person Type', tracking=True, index=True)
    photo = fields.Image(string='Photo', max_width=1024, max_height=1024)
    address_full = fields.Text(string='Full Address', related='partner_id.contact_address',
                               store=False)
    email = fields.Char(string='Email', related='partner_id.email', store=False)
    phone = fields.Char(string='Phone', related='partner_id.phone', store=False)
    mobile = fields.Char(string='Mobile', related='partner_id.mobile', store=False)
    country_id = fields.Many2one('res.country', string='Country',
                                 related='partner_id.country_id', store=False)
    state_id = fields.Many2one('res.country.state', string='State',
                               related='partner_id.state_id', store=False)
    city = fields.Char(string='City', related='partner_id.city', store=False)
    street = fields.Char(string='Street', related='partner_id.street', store=False)
    street2 = fields.Char(string='Street2', related='partner_id.street2', store=False)
    zip = fields.Char(string='Zip', related='partner_id.zip', store=False)
    user_id = fields.Many2one('res.users', string='Related User', tracking=True)
    emergency_contact_name = fields.Char(string='Emergency Contact Name', tracking=True)
    emergency_contact_phone = fields.Char(string='Emergency Contact Phone', tracking=True)
    emergency_contact_relation = fields.Char(string='Relationship', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('partner_id'):
                partner_vals = {
                    'name': vals.get('name', _('New Person')),
                    'type': 'contact',
                }
                for field_name in ['email', 'phone', 'mobile', 'street', 'street2',
                                   'city', 'zip', 'country_id', 'state_id']:
                    if vals.get(field_name):
                        partner_vals[field_name] = vals[field_name]
                if vals.get('photo'):
                    partner_vals['image_1920'] = vals['photo']
                partner = self.env['res.partner'].create(partner_vals)
                vals['partner_id'] = partner.id
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            partner_vals = {}
            for field_name in ['email', 'phone', 'mobile', 'street', 'street2',
                               'city', 'zip', 'country_id', 'state_id']:
                if field_name in vals:
                    partner_vals[field_name] = vals[field_name]
            if 'photo' in vals:
                partner_vals['image_1920'] = vals['photo']
            if 'name' in vals:
                partner_vals['name'] = vals['name']
            if partner_vals and rec.partner_id:
                rec.partner_id.write(partner_vals)
        return res
