# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniExamSchedule(models.Model):
    """جدول الامتحانات — ينشر جداول الامتحانات لكل فصل دراسي.

    يمثّل هذا النموذج مجموعة من الامتحانات المرتبطة بفصل دراسي محدد والمراد
    نشرها للطلاب وأعضاء هيئة التدريس. يمكن أن يحتوي الفصل الواحد على عدة
    جداول (جدول مبدئي، جدول نهائي، جدول للمحترفين...).

    سير العمل:
        ``draft`` → ``published`` → ``closed``
                  ↩ ``draft`` (إعادة للمراجعة)
    """
    _name = 'uni.exam.schedule'
    _description = 'Exam Schedule'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'academic_term_id desc, name'

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Name', required=True, translate=True, tracking=True,
        help='Display name of the exam schedule, e.g. "Fall 2024 Final Exams".')
    code = fields.Char(
        string='Code', copy=False, index=True, tracking=True,
        help='Optional unique code identifying the schedule.')

    # ------------------------------------------------------------------
    # Academic context
    # ------------------------------------------------------------------
    academic_term_id = fields.Many2one(
        'uni.academic.term', string='Academic Term', required=True,
        ondelete='restrict', tracking=True, index=True)
    academic_year_id = fields.Many2one(
        'uni.academic.year', string='Academic Year', store=True,
        related='academic_term_id.academic_year_id', index=True)
    university_id = fields.Many2one(
        'uni.university', string='University', store=True,
        related='academic_term_id.university_id', tracking=True, index=True)
    college_id = fields.Many2one(
        'uni.college', string='College', ondelete='restrict',
        tracking=True, index=True,
        help='Limit the schedule to a specific college (optional).')
    program_id = fields.Many2one(
        'uni.program', string='Program', ondelete='restrict',
        tracking=True, index=True,
        help='Limit the schedule to a specific program (optional).')

    # ------------------------------------------------------------------
    # Publication & state
    # ------------------------------------------------------------------
    publish_date = fields.Date(
        string='Publish Date', tracking=True,
        help='Date on which the schedule was published.')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('closed', 'Closed'),
    ], string='State', default='draft', tracking=True, index=True,
        group_expand='_group_expand_states')
    notes = fields.Text(string='Notes', translate=True)

    # ------------------------------------------------------------------
    # Relations — Many2many with uni.exam (symmetric)
    # ------------------------------------------------------------------
    exam_ids = fields.Many2many(
        'uni.exam', string='Exams',
        relation='uni_exam_schedule_rel',
        column1='schedule_id', column2='exam_id',
        help='Exams included in this schedule.')
    exam_count = fields.Integer(
        compute='_compute_exam_count', string='Exams Count')

    _sql_constraints = [
        ('unique_term_code', 'unique(academic_term_id, code)',
         'Schedule code must be unique per academic term!'),
    ]

    # ------------------------------------------------------------------
    # Group expansion helper
    # ------------------------------------------------------------------
    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in self._fields['state'].selection]

    # ------------------------------------------------------------------
    # Computed
    # ------------------------------------------------------------------
    @api.depends('exam_ids')
    def _compute_exam_count(self):
        for rec in self:
            rec.exam_count = len(rec.exam_ids)

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_publish(self):
        """Publish the exam schedule — requires at least one exam."""
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError(_(
                    "Only draft schedules can be published (current state: %(state)s).")
                    % {'state': rec.state})
            if not rec.exam_ids:
                raise ValidationError(_(
                    "Cannot publish schedule '%s' without any exams.")
                    % rec.display_name)
            if not rec.publish_date:
                rec.publish_date = fields.Date.context_today(rec)
            rec.state = 'published'
            rec.message_post(body=_('Schedule published on %s.') % rec.publish_date)

    def action_close(self):
        """Close the published schedule."""
        for rec in self:
            if rec.state != 'published':
                raise ValidationError(_(
                    "Only published schedules can be closed (current state: %(state)s).")
                    % {'state': rec.state})
            rec.state = 'closed'
            rec.message_post(body=_('Schedule closed.'))

    def action_draft(self):
        """Reset the schedule to draft state."""
        for rec in self:
            if rec.state == 'closed':
                rec.state = 'draft'
                rec.message_post(body=_('Schedule reset to draft.'))
            elif rec.state == 'published':
                rec.state = 'draft'
                rec.message_post(body=_('Schedule unpublished and reset to draft.'))
            else:
                # Already draft — no-op
                pass

    # ------------------------------------------------------------------
    # Smart-button action
    # ------------------------------------------------------------------
    def action_view_exams(self):
        self.ensure_one()
        return {
            'name': _('Exams'),
            'type': 'ir.actions.act_window',
            'res_model': 'uni.exam',
            'view_mode': 'list,form',
            'domain': [('schedule_ids', 'in', self.id)],
            'context': {'default_academic_term_id': self.academic_term_id.id,
                        'default_schedule_ids': [(6, 0, [self.id])]},
        }

    # ------------------------------------------------------------------
    # Onchange — prefill from academic term
    # ------------------------------------------------------------------
    @api.onchange('academic_term_id')
    def _onchange_academic_term_id(self):
        if self.academic_term_id:
            if not self.university_id and self.academic_term_id.university_id:
                self.university_id = self.academic_term_id.university_id

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('college_id', 'university_id')
    def _check_college_university(self):
        """If a college is set, it must belong to the schedule's university."""
        for rec in self:
            if rec.college_id and rec.university_id and \
                    rec.college_id.university_id.id != rec.university_id.id:
                raise ValidationError(_(
                    "College '%s' does not belong to university '%s'.")
                    % (rec.college_id.display_name, rec.university_id.display_name))

    @api.constrains('program_id', 'college_id')
    def _check_program_college(self):
        """If both college and program are set, they must be consistent."""
        for rec in self:
            if rec.program_id and rec.college_id and \
                    rec.program_id.college_id.id != rec.college_id.id:
                raise ValidationError(_(
                    "Program '%s' does not belong to college '%s'.")
                    % (rec.program_id.display_name, rec.college_id.display_name))
