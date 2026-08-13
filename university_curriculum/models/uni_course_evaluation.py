# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class UniCourseEvaluation(models.Model):
    """تقييم المقرر — هيكل تقييم مكون من أقسام وبنود لكل مقرر/فصل دراسي.

    يجمع الأوزان النهائية لكل عناصر التقييم (اختبارات، واجبات، مشاريع... إلخ)
    ويتحقق من أن مجموع الأوزان يساوي 100 (للنسبة المئوية) أو الحد الأقصى للنقاط.
    """
    _name = 'uni.course.evaluation'
    _description = 'Course Evaluation'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'course_id, academic_term_id, id'

    name = fields.Char(string='Reference', required=True, tracking=True, copy=False,
                       default=lambda self: _('New'), index=True)
    course_id = fields.Many2one('uni.course', string='Course',
                                required=True, ondelete='restrict', tracking=True, index=True)
    university_id = fields.Many2one('uni.university', string='University',
                                    related='course_id.university_id', store=True, index=True)
    college_id = fields.Many2one('uni.college', string='College',
                                 related='course_id.college_id', store=True, index=True)
    academic_term_id = fields.Many2one('uni.academic.term', string='Academic Term',
                                       ondelete='restrict', tracking=True, index=True)
    evaluation_type_id = fields.Many2one('uni.evaluation.type', string='Default Evaluation Type',
                                         ondelete='restrict',
                                         help='Default evaluation type applied to new items.')
    total_weight = fields.Float(string='Total Weight', compute='_compute_total_weight',
                                store=True, tracking=True,
                                help='Sum of all section/item weights. Should be 100 for '
                                     'percentage-based evaluations.')
    weight_complete = fields.Boolean(string='Weight Complete', compute='_compute_weight_complete',
                                     search='_search_weight_complete')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('closed', 'Closed'),
    ], string='Status', default='draft', tracking=True, group_expand='_group_expand_states')
    notes = fields.Text(string='Notes')

    section_ids = fields.One2many('uni.course.evaluation.section', 'evaluation_id',
                                  string='Sections', copy=True)
    section_count = fields.Integer(compute='_compute_section_count', string='Sections')
    item_count = fields.Integer(compute='_compute_item_count', string='Items')

    _sql_constraints = [
        ('unique_evaluation_course_term',
         'unique(course_id, academic_term_id)',
         'Only one evaluation is allowed per course per academic term!'),
    ]

    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in states]

    @api.depends('section_ids.weight', 'section_ids.item_ids.weight')
    def _compute_total_weight(self):
        """مجموع أوزان البنود (الأوزان على مستوى البنود هي المرجع،
        وأوزان الأقسام مجموع محسوب).
        """
        for rec in self:
            total = 0.0
            for section in rec.section_ids:
                total += sum(section.item_ids.mapped('weight'))
            rec.total_weight = total

    @api.depends('total_weight')
    def _compute_weight_complete(self):
        """اعتبار التقييم مكتمل الأوزان إذا كان مجموعها 100 (للنسبة المئوية)."""
        for rec in self:
            rec.weight_complete = abs(rec.total_weight - 100.0) < 0.01

    def _search_weight_complete(self, operator, value):
        """بحث مخصص على weight_complete."""
        if (operator == '=' and value) or (operator == '!=' and not value):
            return [('total_weight', '>=', 99.99), ('total_weight', '<=', 100.01)]
        return ['|',
                ('total_weight', '<', 99.99),
                ('total_weight', '>', 100.01)]

    @api.depends('section_ids')
    def _compute_section_count(self):
        for rec in self:
            rec.section_count = len(rec.section_ids)

    @api.depends('section_ids.item_ids')
    def _compute_item_count(self):
        for rec in self:
            rec.item_count = sum(len(s.item_ids) for s in rec.section_ids)

    @api.model_create_multi
    def create(self, vals_list):
        """إنشاء تسلسل للمقرر/الفصل عند إنشاء التقييم."""
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.course.evaluation') or _('New')
        return super().create(vals_list)

    @api.constrains('section_ids', 'state')
    def _check_total_weight_on_activate(self):
        """عند تفعيل التقييم، يجب أن يكون مجموع الأوزان 100 (للنسبة المئوية)."""
        for rec in self:
            if rec.state == 'active' and rec.section_ids:
                if abs(rec.total_weight - 100.0) > 0.01:
                    raise ValidationError(_(
                        'Cannot activate evaluation %s: total weight (%.2f) must equal 100.',
                        rec.display_name, rec.total_weight))

    def action_activate(self):
        """تفعيل التقييم بعد التحقق من اكتمال الأوزان."""
        for rec in self:
            if rec.section_ids and abs(rec.total_weight - 100.0) > 0.01:
                raise ValidationError(_(
                    'Total weight for evaluation %s is %.2f — must equal 100 before activation.',
                    rec.display_name, rec.total_weight))
            rec.state = 'active'

    def action_close(self):
        """إغلاق التقييم."""
        for rec in self:
            rec.state = 'closed'

    def action_draft(self):
        """إعادة التقييم إلى حالة المسودة."""
        for rec in self:
            rec.state = 'draft'

    def action_view_sections(self):
        """فتح سجل أقسام التقييم."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sections'),
            'res_model': 'uni.course.evaluation.section',
            'view_mode': 'list,form',
            'domain': [('evaluation_id', '=', self.id)],
            'context': {'default_evaluation_id': self.id},
        }

    def action_view_items(self):
        """فتح سجل بنود التقييم."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Items'),
            'res_model': 'uni.course.evaluation.item',
            'view_mode': 'list,form',
            'domain': [('evaluation_id', '=', self.id)],
            'context': {'default_evaluation_id': self.id},
        }


class UniCourseEvaluationSection(models.Model):
    """قسم من أقسام تقييم المقرر — يجمع بنوداً من نفس النوع
    (مثلاً: قسم الاختبارات، قسم الواجبات، قسم المشروع).
    """
    _name = 'uni.course.evaluation.section'
    _description = 'Course Evaluation Section'
    _order = 'evaluation_id, sequence, id'
    _rec_name = 'name'

    evaluation_id = fields.Many2one('uni.course.evaluation', string='Evaluation',
                                    required=True, ondelete='cascade', index=True)
    name = fields.Char(string='Section Name', required=True, translate=True)
    weight = fields.Float(string='Section Weight', compute='_compute_weight',
                          store=True, help='Sum of item weights under this section.')
    sequence = fields.Integer(string='Sequence', default=10)
    item_ids = fields.One2many('uni.course.evaluation.item', 'section_id', string='Items',
                               copy=True)
    item_count = fields.Integer(compute='_compute_item_count', string='Items')

    @api.depends('item_ids.weight')
    def _compute_weight(self):
        for rec in self:
            rec.weight = sum(rec.item_ids.mapped('weight'))

    @api.depends('item_ids')
    def _compute_item_count(self):
        for rec in self:
            rec.item_count = len(rec.item_ids)


class UniCourseEvaluationItem(models.Model):
    """بند تقييم داخل قسم — أصغر وحدة تقييم (مثلاً: واجب 1، اختبار قصير 2)."""
    _name = 'uni.course.evaluation.item'
    _description = 'Course Evaluation Item'
    _order = 'section_id, sequence, id'
    _rec_name = 'name'

    section_id = fields.Many2one('uni.course.evaluation.section', string='Section',
                                 required=True, ondelete='cascade', index=True)
    evaluation_id = fields.Many2one('uni.course.evaluation', string='Evaluation',
                                    related='section_id.evaluation_id', store=True, index=True)
    name = fields.Char(string='Item Name', required=True, translate=True)
    evaluation_type_id = fields.Many2one('uni.evaluation.type', string='Evaluation Type',
                                         ondelete='restrict')
    weight = fields.Float(string='Weight (%)', default=0.0,
                          help='Weight as percentage of total course grade.')
    max_score = fields.Float(string='Max Score', default=100.0,
                             help='Maximum raw score for this item (before weighting).')
    sequence = fields.Integer(string='Sequence', default=10)
    description = fields.Text(string='Description')

    _sql_constraints = [
        ('check_weight_positive',
         'check(weight >= 0)',
         'Weight must be positive or zero!'),
        ('check_max_score_positive',
         'check(max_score > 0)',
         'Max score must be greater than zero!'),
    ]
