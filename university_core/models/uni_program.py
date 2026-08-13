# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class UniProgramLevel(models.Model):
    """مستوى البرنامج الدراسي (بكالوريوس، ماجستير، دكتوراه...)."""
    _name = 'uni.program.level'
    _description = 'Program Level'
    _order = 'sequence, name'

    name = fields.Char(string='Level Name', required=True, translate=True)
    code = fields.Char(string='Code', required=True, copy=False, index=True)
    sequence = fields.Integer(string='Sequence', default=10)
    description = fields.Text(string='Description')
    program_ids = fields.One2many('uni.program', 'level_id', string='Programs')
    program_count = fields.Integer(compute='_compute_program_count', string='Programs')

    _sql_constraints = [
        ('unique_program_level_code', 'unique(code)', 'Program level code must be unique!'),
    ]

    @api.depends('program_ids')
    def _compute_program_count(self):
        for rec in self:
            rec.program_count = len(rec.program_ids)


class UniProgram(models.Model):
    """البرنامج الدراسي."""
    _name = 'uni.program'
    _description = 'Academic Program'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'university_id, college_id, name'

    name = fields.Char(string='Program Name', required=True, tracking=True, translate=True)
    code = fields.Char(string='Program Code', required=True, copy=False, tracking=True, index=True)
    university_id = fields.Many2one('uni.university', string='University',
                                    required=True, ondelete='restrict', tracking=True, index=True)
    college_id = fields.Many2one('uni.college', string='College',
                                 required=True, ondelete='restrict', tracking=True, index=True)
    department_id = fields.Many2one('uni.department', string='Department',
                                    ondelete='restrict', tracking=True, index=True)
    branch_id = fields.Many2one('uni.branch', string='Branch',
                                related='college_id.branch_id', store=True, tracking=True)
    level_id = fields.Many2one('uni.program.level', string='Level',
                               required=True, ondelete='restrict', tracking=True, index=True)
    credit_hours = fields.Integer(string='Total Credit Hours', tracking=True)
    duration_years = fields.Integer(string='Duration (Years)', tracking=True)
    coordinator_id = fields.Many2one('res.partner', string='Program Coordinator', tracking=True)
    start_date = fields.Date(string='Start Date', tracking=True)
    end_date = fields.Date(string='End Date', tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('closed', 'Closed'),
    ], string='Status', default='draft', tracking=True, group_expand='_group_expand_states')
    description = fields.Html(string='Description')
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('unique_program_code_college', 'unique(college_id, code)',
         'Program code must be unique per college!'),
    ]

    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in states]

    @api.onchange('college_id')
    def _onchange_college_id(self):
        if self.college_id:
            self.university_id = self.college_id.university_id

    def action_activate(self):
        for rec in self:
            rec.state = 'active'

    def action_suspend(self):
        for rec in self:
            rec.state = 'suspended'

    def action_close(self):
        for rec in self:
            rec.state = 'closed'

    def action_draft(self):
        for rec in self:
            rec.state = 'draft'
