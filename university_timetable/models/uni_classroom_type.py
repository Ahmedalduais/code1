# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class UniClassroomType(models.Model):
    """نوع القاعة — يصف فئة القاعات الدراسية ومواصفاتها التقنية.

    يُستخدم لتصنيف القاعات حسب الغرض (محاضرات، مختبرات، قاعات ندوات...)
    مع تحديد السعة الافتراضية والتجهيزات المتوفرة في هذا النوع.
    """
    _name = 'uni.classroom.type'
    _description = 'Classroom Type'
    _inherit = ['mail.thread', 'uni.mixin.archivable']
    _order = 'sequence, name'

    name = fields.Char(string='Type Name', required=True, tracking=True, translate=True, index=True)
    code = fields.Char(string='Code', required=True, copy=False, tracking=True, index=True,
                       help='Short unique code identifying this classroom type.')
    sequence = fields.Integer(string='Sequence', default=10)
    description = fields.Text(string='Description')
    capacity = fields.Integer(
        string='Default Capacity', tracking=True,
        help='Default seating capacity suggested for classrooms of this type.')

    # ------------------------------------------------------------------
    # Facilities / equipment flags
    # ------------------------------------------------------------------
    has_projector = fields.Boolean(string='Projector', default=False, tracking=True)
    has_computer = fields.Boolean(string='Computer', default=False, tracking=True)
    has_ac = fields.Boolean(string='Air Conditioning', default=False, tracking=True)
    has_whiteboard = fields.Boolean(string='Whiteboard', default=True, tracking=True)
    has_sound_system = fields.Boolean(string='Sound System', default=False, tracking=True)

    # ------------------------------------------------------------------
    # Relations
    # ------------------------------------------------------------------
    classroom_ids = fields.One2many(
        'uni.classroom', 'classroom_type_id', string='Classrooms')
    classroom_count = fields.Integer(
        compute='_compute_classroom_count', string='Classrooms')

    _sql_constraints = [
        ('unique_classroom_type_code', 'unique(code)',
         'Classroom type code must be unique!'),
        ('check_capacity_positive', 'check(capacity >= 0)',
         'Default capacity must be positive or zero!'),
    ]

    # ------------------------------------------------------------------
    # Computed helpers
    # ------------------------------------------------------------------
    @api.depends('classroom_ids')
    def _compute_classroom_count(self):
        for rec in self:
            rec.classroom_count = len(rec.classroom_ids)

    # ------------------------------------------------------------------
    # Smart-button action
    # ------------------------------------------------------------------
    def action_open_classrooms(self):
        """فتح القاعات المرتبطة بنوع القاعة."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Classrooms'),
            'res_model': 'uni.classroom',
            'view_mode': 'list,form',
            'domain': [('classroom_type_id', '=', self.id)],
            'context': {'default_classroom_type_id': self.id,
                        'default_capacity': self.capacity},
        }
