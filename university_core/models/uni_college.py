# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class UniCollege(models.Model):
    """الكلية التابعة للجامعة/الفرع."""
    _name = 'uni.college'
    _description = 'College'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'university_id, name'

    name = fields.Char(string='College Name', required=True, tracking=True, translate=True)
    code = fields.Char(string='College Code', required=True, copy=False, tracking=True, index=True)
    university_id = fields.Many2one('uni.university', string='University',
                                    required=True, ondelete='restrict', tracking=True, index=True)
    branch_id = fields.Many2one('uni.branch', string='Branch',
                                ondelete='restrict', tracking=True, index=True)
    dean_id = fields.Many2one('res.partner', string='Dean', tracking=True)
    partner_id = fields.Many2one('res.partner', string='Contact Address', ondelete='restrict')
    establishment_date = fields.Date(string='Establishment Date', tracking=True)
    department_ids = fields.One2many('uni.department', 'college_id', string='Departments')
    program_ids = fields.One2many('uni.program', 'college_id', string='Programs')
    department_count = fields.Integer(compute='_compute_department_count', string='Departments')
    program_count = fields.Integer(compute='_compute_program_count', string='Programs')
    description = fields.Html(string='Description')
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('unique_college_code_university', 'unique(university_id, code)',
         'College code must be unique per university!'),
    ]

    @api.depends('department_ids')
    def _compute_department_count(self):
        for rec in self:
            rec.department_count = len(rec.department_ids)

    @api.depends('program_ids')
    def _compute_program_count(self):
        for rec in self:
            rec.program_count = len(rec.program_ids)

    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        if self.branch_id and not self.university_id:
            self.university_id = self.branch_id.university_id

    def action_view_departments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Departments'),
            'res_model': 'uni.department',
            'view_mode': 'list,form',
            'domain': [('college_id', '=', self.id)],
            'context': {'default_college_id': self.id,
                        'default_university_id': self.university_id.id},
        }

    def action_view_programs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Programs'),
            'res_model': 'uni.program',
            'view_mode': 'list,form',
            'domain': [('college_id', '=', self.id)],
            'context': {'default_college_id': self.id,
                        'default_university_id': self.university_id.id},
        }
