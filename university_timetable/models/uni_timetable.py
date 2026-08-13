# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniTimetable(models.Model):
    """الجدول الدراسي — يمثل جدولاً لفصل دراسي محدد لكلية/قسم/برنامج.

    يحتوي على خطوط الجدول (``uni.timetable.line``) ويمرّ بدورة حياة:
    مسودة ← مفعّل ← مغلق. الكود فريد لكل فصل دراسي.
    """
    _name = 'uni.timetable'
    _description = 'Timetable'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'academic_term_id, college_id, name'

    name = fields.Char(
        string='Timetable Name', required=True, tracking=True, translate=True, index=True)
    code = fields.Char(
        string='Code', required=True, copy=False, tracking=True, index=True,
        help='Unique code identifying this timetable within its academic term.')
    university_id = fields.Many2one(
        'uni.university', string='University',
        required=True, ondelete='restrict', tracking=True, index=True)
    college_id = fields.Many2one(
        'uni.college', string='College',
        ondelete='restrict', tracking=True, index=True)
    department_id = fields.Many2one(
        'uni.department', string='Department',
        ondelete='restrict', tracking=True, index=True)
    program_id = fields.Many2one(
        'uni.program', string='Program',
        ondelete='restrict', tracking=True, index=True)
    academic_term_id = fields.Many2one(
        'uni.academic.term', string='Academic Term',
        required=True, ondelete='restrict', tracking=True, index=True)
    academic_year_id = fields.Many2one(
        'uni.academic.year', string='Academic Year',
        related='academic_term_id.academic_year_id', store=True, readonly=True)
    branch_id = fields.Many2one(
        'uni.branch', string='Branch',
        related='college_id.branch_id', store=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('closed', 'Closed'),
    ], string='Status', default='draft', tracking=True, index=True,
        group_expand='_group_expand_states')
    publish_date = fields.Date(
        string='Publish Date', tracking=True,
        help='Date on which the timetable was published/activated.')
    notes = fields.Text(string='Notes')

    line_ids = fields.One2many(
        'uni.timetable.line', 'timetable_id', string='Timetable Lines', copy=True)
    line_count = fields.Integer(
        compute='_compute_line_count', string='Lines')

    _sql_constraints = [
        ('unique_timetable_code_term',
         'unique(academic_term_id, code)',
         'Timetable code must be unique per academic term!'),
    ]

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in states]

    @api.depends('line_ids')
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    # ------------------------------------------------------------------
    # Onchange — keep hierarchy consistent
    # ------------------------------------------------------------------
    @api.onchange('college_id')
    def _onchange_college_id(self):
        if self.college_id:
            self.university_id = self.college_id.university_id
            self.branch_id = self.college_id.branch_id

    @api.onchange('department_id')
    def _onchange_department_id(self):
        if self.department_id:
            self.college_id = self.department_id.college_id
            self.university_id = self.department_id.university_id
            self.branch_id = self.department_id.branch_id or self.college_id.branch_id

    @api.onchange('academic_term_id')
    def _onchange_academic_term_id(self):
        """عند اختيار الفصل، تُجلب الجامعة المرتبطة به تلقائياً."""
        if self.academic_term_id and not self.university_id:
            self.university_id = self.academic_term_id.university_id

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_activate(self):
        """تفعيل الجدول ونشره — يجب أن يحتوي على خط واحد على الأقل."""
        for rec in self:
            if not rec.line_ids:
                raise ValidationError(_(
                    'Cannot activate timetable %s: it has no lines.') % rec.display_name)
            if not rec.publish_date:
                rec.publish_date = fields.Date.context_today(rec)
            rec.state = 'active'

    def action_close(self):
        """إغلاق الجدول بعد انتهاء الفصل."""
        for rec in self:
            rec.state = 'closed'

    def action_draft(self):
        """إعادة الجدول إلى حالة المسودة."""
        for rec in self:
            rec.state = 'draft'

    # ------------------------------------------------------------------
    # Smart button
    # ------------------------------------------------------------------
    def action_open_lines(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Timetable Lines'),
            'res_model': 'uni.timetable.line',
            'view_mode': 'list,form,pivot',
            'domain': [('timetable_id', '=', self.id)],
            'context': {
                'default_timetable_id': self.id,
                'default_academic_term_id': self.academic_term_id.id,
                'default_university_id': self.university_id.id,
                'default_college_id': self.college_id.id if self.college_id else False,
                'default_department_id': self.department_id.id if self.department_id else False,
                'default_program_id': self.program_id.id if self.program_id else False,
            },
        }
