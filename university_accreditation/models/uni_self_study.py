# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniSelfStudy(models.Model):
    """الدراسة الذاتية — وثيقة شاملة تُعِدُّها البرامج لجهة الاعتماد.

    تحتوي على: الرسالة، الرؤية، الأهداف، نواتج التعلم، وصف المنهج،
    أساليب تقييم الطلاب، مؤهلات أعضاء هيئة التدريس، الموارد المادية
    والمكتبية والمالية، هيكل الحوكمة، تحليل SWOT، وخطة التحسين.

    سير العمل:
        draft → in_progress → submitted → accepted / rejected

    يتم حساب نسبة الإكمال تلقائياً (completion_percentage) بناءً على
    عدد الحقول النصية المعبأة.
    """
    _name = 'uni.self.study'
    _description = 'Self Study'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'state, preparation_start_date desc, id'

    # ------------------------------------------------------------------
    # Fields used for completion computation
    # ------------------------------------------------------------------
    _COMPLETION_FIELDS = [
        'mission_statement', 'vision_statement', 'goals',
        'program_learning_outcomes', 'curriculum_description',
        'student_assessment_methods', 'faculty_qualifications',
        'physical_resources', 'library_resources', 'financial_resources',
        'governance_structure', 'strengths', 'weaknesses',
        'opportunities', 'threats', 'improvement_plan',
    ]

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Reference', copy=False, readonly=True, index=True,
        default='New', tracking=True,
        help='Auto-generated reference identifying this self-study.')
    code = fields.Char(
        string='Code', copy=False, tracking=True, index=True,
        help='Optional human-friendly code for this self-study.')

    # ------------------------------------------------------------------
    # Relations
    # ------------------------------------------------------------------
    accreditation_program_id = fields.Many2one(
        'uni.accreditation.program', string='Accreditation Program',
        required=True, ondelete='cascade', tracking=True, index=True,
        help='The accreditation program this self-study belongs to.')
    program_id = fields.Many2one(
        'uni.program', string='Program',
        related='accreditation_program_id.program_id', store=True, index=True)
    university_id = fields.Many2one(
        'uni.university', string='University',
        related='accreditation_program_id.university_id',
        store=True, index=True)

    # ------------------------------------------------------------------
    # Dates
    # ------------------------------------------------------------------
    preparation_start_date = fields.Date(
        string='Preparation Start Date', tracking=True,
        help='Date when preparation of the self-study started.')
    preparation_end_date = fields.Date(
        string='Preparation End Date', tracking=True,
        help='Date when preparation was completed.')
    submission_date = fields.Date(
        string='Submission Date', tracking=True,
        help='Date the self-study was submitted.')

    # ------------------------------------------------------------------
    # Committee
    # ------------------------------------------------------------------
    coordinator_id = fields.Many2one(
        'uni.faculty', string='Coordinator',
        ondelete='restrict', tracking=True, index=True,
        help='Faculty member coordinating the self-study preparation.')
    committee_members_ids = fields.Many2many(
        'uni.faculty', string='Committee Members',
        help='Faculty members forming the self-study committee.')

    # ------------------------------------------------------------------
    # Identity & strategic content
    # ------------------------------------------------------------------
    mission_statement = fields.Text(string='Mission Statement')
    vision_statement = fields.Text(string='Vision Statement')
    goals = fields.Text(string='Goals')
    program_learning_outcomes = fields.Text(string='Program Learning Outcomes')

    # ------------------------------------------------------------------
    # Curriculum & assessment
    # ------------------------------------------------------------------
    curriculum_description = fields.Text(string='Curriculum Description')
    student_assessment_methods = fields.Text(string='Student Assessment Methods')

    # ------------------------------------------------------------------
    # Resources
    # ------------------------------------------------------------------
    faculty_qualifications = fields.Text(string='Faculty Qualifications')
    physical_resources = fields.Text(string='Physical Resources')
    library_resources = fields.Text(string='Library Resources')
    financial_resources = fields.Text(string='Financial Resources')
    governance_structure = fields.Text(string='Governance Structure')

    # ------------------------------------------------------------------
    # SWOT analysis
    # ------------------------------------------------------------------
    strengths = fields.Text(string='Strengths')
    weaknesses = fields.Text(string='Weaknesses')
    opportunities = fields.Text(string='Opportunities')
    threats = fields.Text(string='Threats')

    # ------------------------------------------------------------------
    # Improvement
    # ------------------------------------------------------------------
    improvement_plan = fields.Text(string='Improvement Plan')

    # ------------------------------------------------------------------
    # File attachment
    # ------------------------------------------------------------------
    file = fields.Binary(
        string='Self Study File', attachment=True,
        help='Upload the final compiled self-study document.')
    filename = fields.Char(string='Filename')

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('submitted', 'Submitted'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True, index=True,
        group_expand='_group_expand_states')

    completion_percentage = fields.Float(
        string='Completion', digits=(5, 2), default=0.0,
        compute='_compute_completion', store=True,
        help='Percentage of the strategic content fields that have been filled.')

    notes = fields.Text(string='Notes')

    # ------------------------------------------------------------------
    # Group expansion helper
    # ------------------------------------------------------------------
    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in self._fields['state'].selection]

    # ------------------------------------------------------------------
    # Computed: completion percentage
    # ------------------------------------------------------------------
    @api.depends(*_COMPLETION_FIELDS)
    def _compute_completion(self):
        """Compute the percentage of strategic content fields that are filled.

        Only fields declared in _COMPLETION_FIELDS participate in the
        computation. Each non-empty field counts equally.
        """
        total = len(self._COMPLETION_FIELDS)
        for rec in self:
            filled = 0
            for fname in self._COMPLETION_FIELDS:
                value = rec[fname]
                if value and isinstance(value, str) and value.strip():
                    filled += 1
            rec.completion_percentage = \
                (filled / total * 100.0) if total else 0.0

    # ------------------------------------------------------------------
    # Create — auto-generate reference
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.self.study') or _('SST-NEW')
            if not vals.get('code'):
                program_code = False
                if vals.get('accreditation_program_id'):
                    program = self.env['uni.accreditation.program'].browse(
                        vals['accreditation_program_id'])
                    program_code = program.code or False
                parts = [p for p in ['SST', program_code] if p]
                vals['code'] = '-'.join(parts) if parts else False
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Validations
    # ------------------------------------------------------------------
    @api.constrains('preparation_start_date', 'preparation_end_date',
                    'submission_date')
    def _check_dates(self):
        for rec in self:
            if rec.preparation_start_date and rec.preparation_end_date and \
                    rec.preparation_end_date < rec.preparation_start_date:
                raise ValidationError(_(
                    "Preparation end date cannot be earlier than start date "
                    "for self-study %s.") % rec.display_name)
            if rec.submission_date and rec.preparation_end_date and \
                    rec.submission_date < rec.preparation_end_date:
                raise ValidationError(_(
                    "Submission date cannot be earlier than preparation end "
                    "date for self-study %s.") % rec.display_name)

    @api.constrains('state', 'file')
    def _check_submitted_has_file(self):
        """Submitted self-studies should have a file attached."""
        for rec in self:
            if rec.state in ('submitted', 'accepted') and not rec.file:
                raise ValidationError(_(
                    "Self-study %s cannot be submitted without an attached file.")
                    % rec.display_name)

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_start(self):
        """Start working on the self-study (draft → in_progress)."""
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError(_(
                    "Only draft self-studies can be started (%s).")
                    % rec.display_name)
            rec.state = 'in_progress'
            if not rec.preparation_start_date:
                rec.preparation_start_date = fields.Date.context_today(rec)
            rec.message_post(body=_(
                "Self-study preparation started."))

    def action_submit(self):
        """Submit the self-study to the accreditation body."""
        for rec in self:
            if rec.state not in ('draft', 'in_progress'):
                raise ValidationError(_(
                    "Only draft or in-progress self-studies can be submitted (%s).")
                    % rec.display_name)
            if not rec.file:
                raise ValidationError(_(
                    "Please attach a file before submitting self-study %s.")
                    % rec.display_name)
            if rec.completion_percentage < 50.0:
                raise ValidationError(_(
                    "Self-study %s is only %.2f%% complete. At least 50%% "
                    "completion is required before submission.") %
                    (rec.display_name, rec.completion_percentage))
            rec.state = 'submitted'
            if not rec.submission_date:
                rec.submission_date = fields.Date.context_today(rec)
            if not rec.preparation_end_date:
                rec.preparation_end_date = fields.Date.context_today(rec)
            rec.message_post(body=_(
                "Self-study submitted (completion: %.2f%%).") %
                rec.completion_percentage)

    def action_accept(self):
        """Accept the submitted self-study."""
        for rec in self:
            if rec.state != 'submitted':
                raise ValidationError(_(
                    "Only submitted self-studies can be accepted (%s).")
                    % rec.display_name)
            rec.state = 'accepted'
            rec.message_post(body=_(
                "Self-study accepted."))

    def action_reject(self):
        """Reject the submitted self-study and return it to in_progress."""
        for rec in self:
            if rec.state != 'submitted':
                raise ValidationError(_(
                    "Only submitted self-studies can be rejected (%s).")
                    % rec.display_name)
            rec.state = 'rejected'
            rec.message_post(body=_(
                "Self-study rejected."))

    def action_draft(self):
        """Reset a rejected self-study back to in_progress."""
        for rec in self:
            if rec.state != 'rejected':
                raise ValidationError(_(
                    "Only rejected self-studies can be reset to in_progress (%s).")
                    % rec.display_name)
            rec.state = 'in_progress'
            rec.submission_date = False
            rec.message_post(body=_(
                "Self-study reset to in progress."))
