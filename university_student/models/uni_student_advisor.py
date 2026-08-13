# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniStudentAdvisor(models.Model):
    """علاقة المرشد الأكاديمي بالطالب مع تتبّع تاريخي.

    بما أن وحدة ``university_student`` لا يمكنها الإشارة إلى ``uni.faculty``
    (قاعدة الاعتماديات)، يتم تخزين بيانات المرشد كحقول ``Char`` مستقلة،
    مع إمكانية ربطها لاحقاً بالنظام الخارجي (HR) عبر ``advisor_employee_code``.
    يدعم النموذج عدة أدوار للمرشد (أكاديمي، مشرف رسالة، مشرف مشروع، منسّق...).
    """
    _name = 'uni.student.advisor'
    _description = 'Student Academic Advisor'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'student_id, start_date desc'

    # ------------------------------------------------------------------
    # Identity & linkage
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True,
        default=lambda self: _('New'), index=True)
    student_id = fields.Many2one(
        'uni.student', string='Student', required=True,
        ondelete='cascade', tracking=True, index=True)
    student_code = fields.Char(
        related='student_id.student_code', string='Student Code',
        store=True, readonly=True)

    # ------------------------------------------------------------------
    # Advisor info (Char fields — dependency rule prevents M2o to uni.faculty)
    # ------------------------------------------------------------------
    advisor_name = fields.Char(
        string='Advisor Name', required=True, tracking=True,
        help='Full name of the academic advisor')
    advisor_email = fields.Char(string='Advisor Email', tracking=True)
    advisor_phone = fields.Char(string='Advisor Phone', tracking=True)
    advisor_employee_code = fields.Char(
        string='Advisor Employee Code', tracking=True,
        help='Employee code of the advisor in HR system')

    advisor_role = fields.Selection([
        ('academic', 'Academic Advisor'),
        ('thesis', 'Thesis Supervisor'),
        ('co_supervisor', 'Co-Supervisor'),
        ('project', 'Project Supervisor'),
        ('coordinator', 'Program Coordinator'),
        ('mentor', 'Mentor'),
    ], string='Advisor Role', default='academic', required=True, tracking=True)

    # ------------------------------------------------------------------
    # Academic context
    # ------------------------------------------------------------------
    program_id = fields.Many2one(
        'uni.program', string='Program',
        related='student_id.program_id', store=True, readonly=True)
    academic_term_id = fields.Many2one(
        'uni.academic.term', string='Academic Term',
        ondelete='restrict', tracking=True)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    start_date = fields.Date(
        string='Start Date', required=True,
        default=fields.Date.context_today, tracking=True)
    end_date = fields.Date(string='End Date', tracking=True)
    is_current = fields.Boolean(
        string='Currently Active', default=True, tracking=True)

    assignment_reason = fields.Text(string='Assignment Reason')
    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_advisor_reference', 'unique(name)',
         'Advisor reference must be unique!'),
        ('check_dates', 'check(end_date is null or end_date >= start_date)',
         'End date must be after start date!'),
    ]

    # ------------------------------------------------------------------
    # Create — auto-generate reference via ir.sequence
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.student.advisor') or _('New')
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_end_advisory(self):
        """End the current advisory relationship."""
        for rec in self:
            rec.write({
                'end_date': fields.Date.context_today(self),
                'is_current': False,
            })

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('is_current', 'student_id')
    def _check_single_current_advisor(self):
        """Ensure only one current advisor per role per student."""
        for rec in self:
            if rec.is_current:
                existing = self.search([
                    ('student_id', '=', rec.student_id.id),
                    ('advisor_role', '=', rec.advisor_role),
                    ('is_current', '=', True),
                    ('id', '!=', rec.id),
                ])
                if existing:
                    role_label = dict(
                        self._fields['advisor_role'].selection
                    ).get(rec.advisor_role, rec.advisor_role)
                    raise ValidationError(_(
                        'Student already has a current %s advisor. '
                        'Please end the existing one first.'
                    ) % role_label)
