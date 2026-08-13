# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniFacultyLoad(models.Model):
    """العبء التدريسي لعضو هيئة التدريس خلال فصل دراسي.

    يقسّم العبء إلى ساعات التدريس، ساعات البحث، وساعات الأعمال الإدارية،
    مع حساب آلي للإجمالي وتصنيف نوع العبء السائد.
    """
    _name = 'uni.faculty.load'
    _description = 'Faculty Teaching Load'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'academic_term_id desc, faculty_id'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True,
                      default=lambda self: _('New'), index=True)
    faculty_id = fields.Many2one(
        'uni.faculty', string='Faculty', required=True,
        ondelete='restrict', tracking=True, index=True)
    university_id = fields.Many2one(
        related='faculty_id.university_id', store=True, string='University', index=True)
    academic_term_id = fields.Many2one(
        'uni.academic.term', string='Academic Term',
        required=True, ondelete='restrict', tracking=True, index=True)

    teaching_hours = fields.Float(string='Teaching Hours', default=0.0, tracking=True)
    credit_hours = fields.Float(string='Credit Hours', default=0.0, tracking=True,
                                help='Total credit hours delivered during the term.')
    research_hours = fields.Float(string='Research Hours', default=0.0, tracking=True)
    admin_hours = fields.Float(string='Administrative Hours', default=0.0, tracking=True)
    total_hours = fields.Float(
        compute='_compute_total_hours', store=True, string='Total Hours',
        help='Sum of teaching + research + admin hours.')
    load_type = fields.Selection([
        ('teaching', 'Teaching'),
        ('research', 'Research'),
        ('administrative', 'Administrative'),
    ], string='Load Type', default='teaching', tracking=True, index=True,
        help='Dominant load type for this period (used for reporting).')
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('unique_load_ref', 'unique(name)',
         'Load reference must be unique!'),
        ('unique_faculty_term', 'unique(faculty_id, academic_term_id)',
         'A faculty member can have only one load record per academic term!'),
    ]

    # ------------------------------------------------------------------
    # Computed
    # ------------------------------------------------------------------
    @api.depends('teaching_hours', 'research_hours', 'admin_hours')
    def _compute_total_hours(self):
        for rec in self:
            rec.total_hours = (rec.teaching_hours + rec.research_hours
                               + rec.admin_hours)

    # ------------------------------------------------------------------
    # Create — auto-generate reference
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.faculty.load') or _('LOAD-NEW')
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Onchange — auto-suggest load type from hours
    # ------------------------------------------------------------------
    @api.onchange('teaching_hours', 'research_hours', 'admin_hours')
    def _onchange_suggest_load_type(self):
        for rec in self:
            hours_map = {
                'teaching': rec.teaching_hours,
                'research': rec.research_hours,
                'administrative': rec.admin_hours,
            }
            if any(v > 0 for v in hours_map.values()):
                rec.load_type = max(hours_map, key=hours_map.get)

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('teaching_hours', 'research_hours', 'admin_hours')
    def _check_non_negative(self):
        for rec in self:
            for fname, label in [('teaching_hours', 'Teaching'),
                                 ('research_hours', 'Research'),
                                 ('admin_hours', 'Administrative')]:
                if rec[fname] < 0:
                    raise ValidationError(_(
                        "%s hours cannot be negative for load %s.") % (label, rec.display_name))
