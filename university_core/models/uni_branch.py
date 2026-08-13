# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class UniBranch(models.Model):
    """فرع الجامعة."""
    _name = 'uni.branch'
    _description = 'University Branch'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'university_id, name'

    name = fields.Char(string='Branch Name', required=True, tracking=True, translate=True)
    code = fields.Char(string='Branch Code', required=True, copy=False, tracking=True, index=True)
    university_id = fields.Many2one('uni.university', string='University',
                                    required=True, ondelete='restrict', tracking=True, index=True)
    partner_id = fields.Many2one('res.partner', string='Address', ondelete='restrict')
    manager_id = fields.Many2one('res.users', string='Branch Manager', tracking=True)
    phone = fields.Char(string='Phone', related='partner_id.phone', store=False)
    email = fields.Char(string='Email', related='partner_id.email', store=False)
    city = fields.Char(string='City', related='partner_id.city', store=False)
    country_id = fields.Many2one('res.country', string='Country',
                                 related='partner_id.country_id', store=False)
    college_ids = fields.One2many('uni.college', 'branch_id', string='Colleges')
    college_count = fields.Integer(compute='_compute_college_count', string='College Count')
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('unique_branch_code_university', 'unique(university_id, code)',
         'Branch code must be unique per university!'),
    ]

    @api.depends('college_ids')
    def _compute_college_count(self):
        for rec in self:
            rec.college_count = len(rec.college_ids)

    def action_view_colleges(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Colleges'),
            'res_model': 'uni.college',
            'view_mode': 'list,form',
            'domain': [('branch_id', '=', self.id)],
            'context': {'default_branch_id': self.id,
                        'default_university_id': self.university_id.id},
        }
