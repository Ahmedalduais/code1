# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class UniDepartment(models.Model):
    """القسم العلمي داخل الكلية."""
    _name = 'uni.department'
    _description = 'Department'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'college_id, name'

    name = fields.Char(string='Department Name', required=True, tracking=True, translate=True)
    code = fields.Char(string='Department Code', required=True, copy=False, tracking=True, index=True)
    university_id = fields.Many2one('uni.university', string='University',
                                    required=True, ondelete='restrict', tracking=True, index=True)
    college_id = fields.Many2one('uni.college', string='College',
                                 required=True, ondelete='restrict', tracking=True, index=True)
    branch_id = fields.Many2one('uni.branch', string='Branch',
                                related='college_id.branch_id', store=True, tracking=True)
    head_id = fields.Many2one('res.partner', string='Department Head', tracking=True)
    establishment_date = fields.Date(string='Establishment Date', tracking=True)
    program_ids = fields.One2many('uni.program', 'department_id', string='Programs')
    program_count = fields.Integer(compute='_compute_program_count', string='Programs')
    description = fields.Html(string='Description')
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('unique_department_code_college', 'unique(college_id, code)',
         'Department code must be unique per college!'),
    ]

    @api.depends('program_ids')
    def _compute_program_count(self):
        for rec in self:
            rec.program_count = len(rec.program_ids)

    @api.onchange('college_id')
    def _onchange_college_id(self):
        if self.college_id:
            self.university_id = self.college_id.university_id

    def action_view_programs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Programs'),
            'res_model': 'uni.program',
            'view_mode': 'list,form',
            'domain': [('department_id', '=', self.id)],
            'context': {'default_department_id': self.id,
                        'default_college_id': self.college_id.id,
                        'default_university_id': self.university_id.id},
        }
