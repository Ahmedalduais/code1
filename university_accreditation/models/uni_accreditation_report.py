# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniAccreditationReport(models.Model):
    """تقرير الاعتماد — يمثل تقريراً يُقدَّم إلى جهة الاعتماد.

    سير العمل:
        draft → submitted → under_review → accepted / rejected

    يدعم أنواع التقارير: الدراسة الذاتية، المرحلية، النهائية،
    الخاصة، والسنوية. يحتوي على ملف التقرير وملخص النتائج والتوصيات.
    """
    _name = 'uni.accreditation.report'
    _description = 'Accreditation Report'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'report_date desc, id'

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Reference', copy=False, readonly=True, index=True,
        default='New', tracking=True,
        help='Auto-generated reference identifying this report.')
    code = fields.Char(
        string='Code', copy=False, tracking=True, index=True,
        help='Optional human-friendly code for this report.')

    # ------------------------------------------------------------------
    # Relations
    # ------------------------------------------------------------------
    accreditation_program_id = fields.Many2one(
        'uni.accreditation.program', string='Accreditation Program',
        required=True, ondelete='cascade', tracking=True, index=True,
        help='The accreditation program this report belongs to.')
    program_id = fields.Many2one(
        'uni.program', string='Program',
        related='accreditation_program_id.program_id', store=True, index=True)
    university_id = fields.Many2one(
        'uni.university', string='University',
        related='accreditation_program_id.university_id', store=True, index=True)
    accreditation_body_id = fields.Many2one(
        'uni.accreditation.body',
        related='accreditation_program_id.accreditation_body_id',
        store=True, index=True)

    # ------------------------------------------------------------------
    # Report classification
    # ------------------------------------------------------------------
    report_type = fields.Selection([
        ('self_study', 'Self Study'),
        ('interim', 'Interim'),
        ('final', 'Final'),
        ('special', 'Special'),
        ('annual', 'Annual'),
    ], string='Report Type', required=True, default='annual',
        tracking=True, index=True,
        help='Type of report being submitted.')

    # ------------------------------------------------------------------
    # Dates
    # ------------------------------------------------------------------
    report_date = fields.Date(
        string='Report Date', default=fields.Date.context_today,
        required=True, tracking=True,
        help='Date the report was produced.')
    submission_date = fields.Date(
        string='Submission Date', tracking=True,
        help='Date the report was submitted to the accreditation body.')
    accepted_date = fields.Date(
        string='Accepted Date', tracking=True, readonly=True,
        help='Date the report was accepted by the accreditation body.')

    # ------------------------------------------------------------------
    # Reviewers
    # ------------------------------------------------------------------
    prepared_by = fields.Many2one(
        'res.users', string='Prepared By',
        default=lambda self: self.env.user, tracking=True, index=True,
        help='User who prepared the report.')
    reviewed_by = fields.Many2one(
        'res.users', string='Reviewed By', tracking=True, index=True,
        help='User who reviewed the report.')

    # ------------------------------------------------------------------
    # File attachment
    # ------------------------------------------------------------------
    file = fields.Binary(
        string='Report File', attachment=True,
        help='Upload the report document (PDF, DOCX, etc.).')
    filename = fields.Char(string='Filename')

    # ------------------------------------------------------------------
    # Content
    # ------------------------------------------------------------------
    summary = fields.Text(
        string='Summary',
        help='Executive summary of the report.')
    findings = fields.Text(
        string='Findings',
        help='Key findings from the report.')
    recommendations = fields.Text(
        string='Recommendations',
        help='Recommendations based on the findings.')

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True, index=True,
        group_expand='_group_expand_states')

    notes = fields.Text(string='Notes')

    # ------------------------------------------------------------------
    # SQL constraints
    # ------------------------------------------------------------------
    _sql_constraints = [
        ('check_dates_order',
         "CHECK (accepted_date IS NULL OR submission_date IS NULL OR "
         "accepted_date >= submission_date)",
         'Accepted date cannot be earlier than submission date!'),
    ]

    # ------------------------------------------------------------------
    # Group expansion helper
    # ------------------------------------------------------------------
    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in self._fields['state'].selection]

    # ------------------------------------------------------------------
    # Create — auto-generate reference and code
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.accreditation.report') or _('ACR-RPT-NEW')
            if not vals.get('code'):
                program_code = False
                if vals.get('accreditation_program_id'):
                    program = self.env['uni.accreditation.program'].browse(
                        vals['accreditation_program_id'])
                    program_code = program.code or False
                report_type = vals.get('report_type', 'annual')
                parts = [p for p in ['ACR-RPT', program_code, report_type] if p]
                vals['code'] = '-'.join(parts) if parts else False
            if not vals.get('prepared_by'):
                vals['prepared_by'] = self.env.user.id
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Validations
    # ------------------------------------------------------------------
    @api.constrains('report_date', 'submission_date', 'accepted_date')
    def _check_dates(self):
        for rec in self:
            if rec.submission_date and rec.report_date and \
                    rec.submission_date < rec.report_date:
                raise ValidationError(_(
                    "Submission date cannot be earlier than report date "
                    "for report %s.") % rec.display_name)
            if rec.accepted_date and rec.submission_date and \
                    rec.accepted_date < rec.submission_date:
                raise ValidationError(_(
                    "Accepted date cannot be earlier than submission date "
                    "for report %s.") % rec.display_name)

    @api.constrains('state', 'file')
    def _check_submitted_has_file(self):
        """Submitted reports should ideally have a file attached."""
        for rec in self:
            if rec.state in ('submitted', 'under_review', 'accepted') \
                    and not rec.file:
                raise ValidationError(_(
                    "Report %s cannot be submitted without an attached file.")
                    % rec.display_name)

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_submit(self):
        """Submit the report to the accreditation body."""
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError(_(
                    "Only draft reports can be submitted (%s).")
                    % rec.display_name)
            if not rec.file:
                raise ValidationError(_(
                    "Please attach a file before submitting report %s.")
                    % rec.display_name)
            rec.state = 'submitted'
            if not rec.submission_date:
                rec.submission_date = fields.Date.context_today(rec)
            rec.message_post(body=_(
                "Report submitted to %s.") %
                (rec.accreditation_body_id.display_name or _('the body')))

    def action_review(self):
        """Start the review of a submitted report."""
        for rec in self:
            if rec.state != 'submitted':
                raise ValidationError(_(
                    "Only submitted reports can be put under review (%s).")
                    % rec.display_name)
            rec.state = 'under_review'
            rec.reviewed_by = self.env.user
            rec.message_post(body=_(
                "Report is now under review by %s.") % self.env.user.name)

    def action_accept(self):
        """Accept the reviewed report."""
        for rec in self:
            if rec.state != 'under_review':
                raise ValidationError(_(
                    "Only reports under review can be accepted (%s).")
                    % rec.display_name)
            rec.state = 'accepted'
            rec.accepted_date = fields.Date.context_today(rec)
            rec.message_post(body=_(
                "Report accepted on %s.") % rec.accepted_date)

    def action_reject(self):
        """Reject the reviewed report and return it to draft."""
        for rec in self:
            if rec.state not in ('submitted', 'under_review'):
                raise ValidationError(_(
                    "Only submitted or under review reports can be rejected (%s).")
                    % rec.display_name)
            rec.state = 'rejected'
            rec.message_post(body=_(
                "Report rejected."))

    def action_draft(self):
        """Reset a rejected report back to draft."""
        for rec in self:
            if rec.state != 'rejected':
                raise ValidationError(_(
                    "Only rejected reports can be reset to draft (%s).")
                    % rec.display_name)
            rec.state = 'draft'
            rec.submission_date = False
            rec.accepted_date = False
            rec.message_post(body=_(
                "Report reset to draft."))
