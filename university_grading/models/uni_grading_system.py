# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class UniGradingScaleLine(models.Model):
    """خطوط سلم الدرجات — تربط التقديرات بنظام درجات معين."""
    _name = 'uni.grading.scale.line'
    _description = 'Grading Scale Line'
    _order = 'percentage_min desc'

    grading_system_id = fields.Many2one('uni.grading.system', string='Grading System',
                                        required=True, ondelete='cascade', index=True)
    grade_letter_id = fields.Many2one('uni.grade.letter', string='Grade Letter',
                                      required=True, ondelete='restrict', index=True)
    grade_letter_code = fields.Char(string='Grade', related='grade_letter_id.code',
                                    store=True, index=True)
    percentage_min = fields.Float(string='Min %', required=True, digits=(5, 2))
    percentage_max = fields.Float(string='Max %', required=True, digits=(5, 2))
    gpa_value = fields.Float(string='GPA Value', digits=(4, 2),
                             related='grade_letter_id.gpa_value', store=True)
    description = fields.Text(string='Description')

    _sql_constraints = [
        ('check_scale_line_range', 'check(percentage_max >= percentage_min)',
         'Max percentage must be greater than or equal to min percentage!'),
    ]


class UniGradingSystem(models.Model):
    """نظام الدرجات (4.0, 5.0,百分比...)."""
    _name = 'uni.grading.system'
    _description = 'Grading System'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='System Name', required=True, tracking=True, translate=True, index=True)
    code = fields.Char(string='Code', required=True, copy=False, tracking=True, index=True)
    description = fields.Text(string='Description')
    scale_max = fields.Float(string='Scale Maximum', required=True, digits=(5, 2),
                             default=100.0, tracking=True,
                             help='Maximum value on the scale (e.g. 100 for percentage, 4.0 for GPA).')
    passing_grade = fields.Float(string='Passing Grade', required=True, digits=(5, 2),
                                 default=60.0, tracking=True,
                                 help='Minimum grade to pass.')
    gpa_scale = fields.Float(string='GPA Scale', required=True, digits=(4, 2),
                             default=4.0, tracking=True,
                             help='Maximum GPA value (e.g. 4.0, 5.0).')
    system_type = fields.Selection([
        ('percentage', 'Percentage Based'),
        ('gpa', 'GPA Based'),
        ('letter', 'Letter Based'),
        ('hybrid', 'Hybrid'),
    ], string='System Type', default='percentage', required=True, tracking=True)
    scale_line_ids = fields.One2many('uni.grading.scale.line', 'grading_system_id',
                                     string='Grading Scale')
    grade_letter_ids = fields.Many2many('uni.grade.letter', string='Available Grade Letters')
    is_default = fields.Boolean(string='Default System', default=False, tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)

    _sql_constraints = [
        ('unique_grading_system_code', 'unique(code)', 'Grading system code must be unique!'),
        ('check_scale_max_positive', 'check(scale_max > 0)',
         'Scale maximum must be greater than zero!'),
        ('check_gpa_scale_positive', 'check(gpa_scale > 0)',
         'GPA scale must be greater than zero!'),
    ]

    @api.constrains('is_default')
    def _check_is_default(self):
        for rec in self:
            if rec.is_default:
                others = self.search([('is_default', '=', True), ('id', '!=', rec.id)])
                others.write({'is_default': False})

    def action_set_default(self):
        for rec in self:
            rec.is_default = True

    @api.model
    def get_default_system(self):
        """الحصول على نظام الدرجات الافتراضي."""
        default = self.search([('is_default', '=', True), ('active', '=', True)], limit=1)
        if not default:
            default = self.search([('active', '=', True)], limit=1)
        return default

    def get_grade_letter_for_percentage(self, percentage):
        """الحصول على التقدير المناسب لنسبة معينة ضمن هذا النظام."""
        self.ensure_one()
        scale_line = self.scale_line_ids.filtered(
            lambda l: l.percentage_min <= percentage <= l.percentage_max
        )
        if scale_line:
            return scale_line[0].grade_letter_id
        return self.env['uni.grade.letter']

    def compute_gpa_value(self, percentage):
        """حساب قيمة GPA لنسبة معينة ضمن نظام الدرجات."""
        self.ensure_one()
        if self.gpa_scale <= 0:
            return 0.0
        return min((percentage / self.scale_max) * self.gpa_scale, self.gpa_scale)

    @api.onchange('system_type')
    def _onchange_system_type(self):
        if self.system_type == 'gpa':
            self.scale_max = self.gpa_scale
        elif self.system_type == 'percentage':
            self.scale_max = 100.0
