# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class UniAcademicYear(models.Model):
    """السنة الأكاديمية."""
    _name = 'uni.academic.year'
    _description = 'Academic Year'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'date_start desc'

    name = fields.Char(string='Academic Year', required=True, tracking=True, copy=False, index=True)
    code = fields.Char(string='Code', required=True, copy=False, index=True)
    university_id = fields.Many2one('uni.university', string='University',
                                    required=True, ondelete='restrict', tracking=True, index=True)
    date_start = fields.Date(string='Start Date', required=True, tracking=True)
    date_end = fields.Date(string='End Date', required=True, tracking=True)
    term_ids = fields.One2many('uni.academic.term', 'academic_year_id', string='Terms')
    term_count = fields.Integer(compute='_compute_term_count', string='Terms')
    is_current = fields.Boolean(string='Current Year', default=False, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('closed', 'Closed'),
    ], string='Status', default='draft', tracking=True)
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('unique_academic_year_code_university', 'unique(university_id, code)',
         'Academic year code must be unique per university!'),
        ('check_academic_year_dates', 'check(date_end > date_start)',
         'End date must be after start date!'),
    ]

    @api.depends('term_ids')
    def _compute_term_count(self):
        for rec in self:
            rec.term_count = len(rec.term_ids)

    @api.constrains('is_current')
    def _check_is_current(self):
        for rec in self:
            if rec.is_current:
                others = self.search([
                    ('university_id', '=', rec.university_id.id),
                    ('is_current', '=', True),
                    ('id', '!=', rec.id),
                ])
                others.write({'is_current': False})

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for rec in self:
            if rec.date_start and rec.date_end and rec.date_end <= rec.date_start:
                raise ValidationError(_('End date must be after start date!'))

    def action_activate(self):
        for rec in self:
            rec.state = 'active'

    def action_close(self):
        for rec in self:
            rec.state = 'closed'

    def action_set_current(self):
        for rec in self:
            rec.is_current = True
            rec.state = 'active'

    def action_view_terms(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Terms'),
            'res_model': 'uni.academic.term',
            'view_mode': 'list,form',
            'domain': [('academic_year_id', '=', self.id)],
            'context': {'default_academic_year_id': self.id,
                        'default_university_id': self.university_id.id},
        }
