# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class UniFacultyRank(models.Model):
    """الرتبة الأكاديمية لعضو هيئة التدريس.

    تصنيف هرمي للرتب الأكاديمية (معيد، محاضر، أستاذ مساعد، أستاذ مشارك،
    أستاذ، أستاذ متميز) مع رمز فريد وعدد سنوات الخبرة الأدنى المطلوبة
    للترقية إلى هذه الرتبة.
    """
    _name = 'uni.faculty.rank'
    _description = 'Faculty Academic Rank'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'sequence, name'

    name = fields.Char(string='Rank Name', required=True, translate=True, tracking=True)
    code = fields.Char(string='Code', required=True, copy=False, index=True,
                      help='Short unique code identifying the rank (e.g. PROF, ASPROF).')
    sequence = fields.Integer(string='Sequence', default=10,
                              help="Used to order ranks from junior to senior.")
    description = fields.Text(string='Description')
    min_years_experience = fields.Integer(
        string='Min Years of Experience',
        help='Minimum years of professional experience typically required to hold this rank.')
    salary_grade = fields.Char(string='Salary Grade',
                               help='HR salary grade code associated with this rank.')
    faculty_ids = fields.One2many('uni.faculty', 'faculty_rank_id', string='Faculty Members')
    faculty_count = fields.Integer(compute='_compute_faculty_count', string='Faculty Count')

    _sql_constraints = [
        ('unique_faculty_rank_code', 'unique(code)',
         'Faculty rank code must be unique!'),
    ]

    @api.depends('faculty_ids')
    def _compute_faculty_count(self):
        for rec in self:
            rec.faculty_count = len(rec.faculty_ids)

    def action_toggle_active(self):
        """Toggle the active state of the rank (archive/unarchive)."""
        for rec in self:
            rec.active = not rec.active

    def action_open_faculty(self):
        """Smart-button: open the faculty members holding this rank."""
        self.ensure_one()
        return {
            'name': _('Faculty Members'),
            'type': 'ir.actions.act_window',
            'res_model': 'uni.faculty',
            'view_mode': 'list,form',
            'domain': [('faculty_rank_id', '=', self.id)],
            'context': {'default_faculty_rank_id': self.id},
        }
