# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class UniAcademicTerm(models.Model):
    """الفصل الدراسي."""
    _name = 'uni.academic.term'
    _description = 'Academic Term'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'academic_year_id, date_start'

    name = fields.Char(string='Term Name', required=True, tracking=True, copy=False, index=True)
    code = fields.Char(string='Code', required=True, copy=False, index=True)
    university_id = fields.Many2one('uni.university', string='University',
                                    required=True, ondelete='restrict', tracking=True, index=True)
    academic_year_id = fields.Many2one('uni.academic.year', string='Academic Year',
                                       required=True, ondelete='restrict', tracking=True, index=True)
    term_type_id = fields.Many2one('uni.academic.term.type', string='Term Type',
                                   required=True, ondelete='restrict', tracking=True, index=True)
    date_start = fields.Date(string='Start Date', required=True, tracking=True)
    date_end = fields.Date(string='End Date', required=True, tracking=True)
    registration_date_start = fields.Date(string='Registration Start', tracking=True)
    registration_date_end = fields.Date(string='Registration End', tracking=True)
    is_current = fields.Boolean(string='Current Term', default=False, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('registration', 'Registration'),
        ('active', 'Active'),
        ('closed', 'Closed'),
    ], string='Status', default='draft', tracking=True)
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('unique_term_code_year', 'unique(academic_year_id, code)',
         'Term code must be unique per academic year!'),
        ('check_term_dates', 'check(date_end > date_start)',
         'End date must be after start date!'),
    ]

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
            if rec.academic_year_id:
                if rec.date_start < rec.academic_year_id.date_start or \
                   rec.date_end > rec.academic_year_id.date_end:
                    raise ValidationError(_(
                        'Term dates must be within the academic year dates!'))

    def action_open_registration(self):
        for rec in self:
            rec.state = 'registration'

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

    def action_draft(self):
        for rec in self:
            rec.state = 'draft'
