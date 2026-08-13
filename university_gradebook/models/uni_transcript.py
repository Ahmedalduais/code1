# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniTranscript(models.Model):
    """الكشف الأكاديمي — يمثل كشفاً رسمياً بدرجات الطالب عبر فترات دراسية.

    سير العمل:
        draft → issued → verified → revoked
                       ↘ (يمكن العودة من issued إلى draft)

    يجمع الكشف الدرجات النهائية للطالب (final_ids) من سجلات الدرجات
    ويعرض إجمالي المعدل التراكمي والساعات المعتمدة والموقف الأكاديمي.
    """
    _name = 'uni.transcript'
    _description = 'Academic Transcript'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'issue_date desc, id'

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Reference', copy=False, readonly=True, index=True,
        default='New', tracking=True,
        help='Auto-generated reference identifying this transcript.')
    code = fields.Char(
        string='Code', copy=False, tracking=True, index=True,
        help='Optional human-friendly code (e.g. TRN-2025-0001).')

    # ------------------------------------------------------------------
    # Student context (related for fast access)
    # ------------------------------------------------------------------
    student_id = fields.Many2one(
        'uni.student', string='Student',
        required=True, ondelete='restrict', tracking=True, index=True)
    university_id = fields.Many2one(
        'uni.university', string='University',
        related='student_id.university_id', store=True, index=True)
    program_id = fields.Many2one(
        'uni.program', string='Program',
        related='student_id.program_id', store=True, index=True)

    # ------------------------------------------------------------------
    # Period covered
    # ------------------------------------------------------------------
    academic_year_from = fields.Many2one(
        'uni.academic.year', string='From Year', tracking=True,
        help='Academic year from which the transcript covers grades.')
    academic_year_to = fields.Many2one(
        'uni.academic.year', string='To Year', tracking=True,
        help='Academic year up to which the transcript covers grades.')

    # ------------------------------------------------------------------
    # Issue metadata
    # ------------------------------------------------------------------
    issue_date = fields.Date(
        string='Issue Date', default=fields.Date.context_today, tracking=True)
    issued_by = fields.Many2one(
        'res.users', string='Issued By',
        default=lambda self: self.env.user, tracking=True, index=True)

    # ------------------------------------------------------------------
    # Student academic snapshot (related for display)
    # ------------------------------------------------------------------
    cumulative_gpa = fields.Float(
        string='Cumulative GPA', digits=(4, 2),
        related='student_id.cumulative_gpa', store=True)
    total_credits_earned = fields.Integer(
        string='Credits Earned',
        related='student_id.total_credits_earned', store=True)
    total_credits_required = fields.Integer(
        string='Credits Required',
        related='student_id.total_credits_required', store=True)
    academic_standing = fields.Selection(
        string='Academic Standing',
        related='student_id.academic_standing', store=True)

    # ------------------------------------------------------------------
    # Finals selected for this transcript
    # ------------------------------------------------------------------
    final_ids = fields.Many2many(
        'uni.gradebook.final', string='Final Grades',
        help='Final grade records included in this transcript.')
    final_count = fields.Integer(
        string='Finals Count',
        compute='_compute_final_count',
        help='Number of final grade records included in this transcript.')

    # ------------------------------------------------------------------
    # State & metadata
    # ------------------------------------------------------------------
    state = fields.Selection([
        ('draft', 'Draft'),
        ('issued', 'Issued'),
        ('verified', 'Verified'),
        ('revoked', 'Revoked'),
    ], string='Status', default='draft', tracking=True, index=True,
        group_expand='_group_expand_states')
    official_stamp = fields.Boolean(
        string='Official Stamp', default=False, tracking=True,
        help='Whether this transcript carries the official university stamp.')
    print_count = fields.Integer(
        string='Print Count', default=0, tracking=True,
        help='Number of times this transcript has been printed.')
    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True, tracking=True)

    # ------------------------------------------------------------------
    # Group expansion helper
    # ------------------------------------------------------------------
    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in self._fields['state'].selection]

    # ------------------------------------------------------------------
    # Computed
    # ------------------------------------------------------------------
    @api.depends('final_ids')
    def _compute_final_count(self):
        for rec in self:
            rec.final_count = len(rec.final_ids)

    # ------------------------------------------------------------------
    # Onchange
    # ------------------------------------------------------------------
    @api.onchange('student_id')
    def _onchange_student_id(self):
        """Pre-fill university & program from the student."""
        if self.student_id:
            # Auto-set academic_year_to to the latest academic year if empty
            if not self.academic_year_to:
                latest_year = self.env['uni.academic.year'].search(
                    [('university_id', '=', self.student_id.university_id.id)],
                    limit=1, order='date_start desc')
                if latest_year:
                    self.academic_year_to = latest_year.id

    # ------------------------------------------------------------------
    # Create — auto-generate reference and code
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.transcript') or _('TRN-NEW')
            if not vals.get('code'):
                student_code = False
                if vals.get('student_id'):
                    student = self.env['uni.student'].browse(vals['student_id'])
                    student_code = student.student_code or False
                parts = [p for p in ['TRN', student_code] if p]
                vals['code'] = '-'.join(parts) if parts else False
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_issue(self):
        """Issue the transcript — make it official."""
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError(_(
                    "Only draft transcripts can be issued (%s).") % rec.display_name)
            if not rec.student_id:
                raise ValidationError(_(
                    "Transcript %s must reference a student before issuing.")
                    % rec.display_name)
            if not rec.final_ids:
                # Auto-generate lines if none selected
                rec.action_generate_lines()
            rec.state = 'issued'
            rec.issue_date = fields.Date.context_today(rec)
            rec.issued_by = self.env.user.id
            rec.message_post(body=_(
                "Transcript issued by %s on %s.") % (
                self.env.user.name, rec.issue_date))

    def action_verify(self):
        """Verify the transcript — typically by a registrar."""
        for rec in self:
            if rec.state != 'issued':
                raise ValidationError(_(
                    "Only issued transcripts can be verified (%s).") % rec.display_name)
            rec.state = 'verified'
            rec.official_stamp = True
            rec.message_post(body=_(
                "Transcript verified and stamped by %s.") % self.env.user.name)

    def action_revoke(self):
        """Revoke the transcript — typically when superseded by a newer version."""
        for rec in self:
            if rec.state in ('draft', 'revoked'):
                raise ValidationError(_(
                    "Cannot revoke a transcript in state '%(state)s' (%(name)s).")
                    % {'state': rec.state, 'name': rec.display_name})
            rec.state = 'revoked'
            rec.official_stamp = False
            rec.message_post(body=_(
                "Transcript revoked by %s.") % self.env.user.name)

    def action_draft(self):
        """Reset the transcript to draft (only from issued state)."""
        for rec in self:
            if rec.state in ('verified', 'revoked'):
                raise ValidationError(_(
                    "Cannot reset a %(state)s transcript to draft (%(name)s). "
                    "Create a new transcript instead.")
                    % {'state': rec.state, 'name': rec.display_name})
            rec.state = 'draft'
            rec.official_stamp = False

    def action_print(self):
        """Print the transcript as a PDF report.

        Increments the print_count for each record.
        """
        for rec in self:
            rec.print_count = (rec.print_count or 0) + 1
        return self.env.ref(
            'university_gradebook.action_report_transcript'
        ).report_action(self)

    def action_generate_lines(self):
        """Populate ``final_ids`` with all the student's gradebook.final
        records (filtered by the year range if set).
        """
        for rec in self:
            if not rec.student_id:
                raise ValidationError(_(
                    "A student is required to generate transcript lines."))
            domain = [
                ('student_id', '=', rec.student_id.id),
                ('state', 'in', ('computed', 'locked')),
            ]
            # Optionally filter by academic year range
            if rec.academic_year_from or rec.academic_year_to:
                # Build a domain on the related academic_term_id.academic_year_id
                year_ids = []
                if rec.academic_year_from and rec.academic_year_to:
                    year_ids = self.env['uni.academic.year'].search([
                        ('university_id', '=', rec.student_id.university_id.id),
                        ('date_start', '>=', rec.academic_year_from.date_start),
                        ('date_end', '<=', rec.academic_year_to.date_end),
                    ]).ids
                elif rec.academic_year_from:
                    year_ids = self.env['uni.academic.year'].search([
                        ('university_id', '=', rec.student_id.university_id.id),
                        ('date_start', '>=', rec.academic_year_from.date_start),
                    ]).ids
                elif rec.academic_year_to:
                    year_ids = self.env['uni.academic.year'].search([
                        ('university_id', '=', rec.student_id.university_id.id),
                        ('date_end', '<=', rec.academic_year_to.date_end),
                    ]).ids
                if year_ids:
                    domain.append(('academic_term_id.academic_year_id', 'in', year_ids))
            finals = self.env['uni.gradebook.final'].search(domain)
            rec.final_ids = [(6, 0, finals.ids)]

    def action_view_finals(self):
        self.ensure_one()
        return {
            'name': _('Final Grades'),
            'type': 'ir.actions.act_window',
            'res_model': 'uni.gradebook.final',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.final_ids.ids)],
        }
