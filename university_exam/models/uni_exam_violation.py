# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniExamViolation(models.Model):
    """مخالفة الامتحان — مخالفة يرتكبها طالب أثناء امتحان.

    يوثّق هذا النموذج كل مخالفة مع:
        * الامتحان والطالب ونوع المخالفة (غش، انتحال صفة، تأخّر، إلخ)
        * درجة الخطورة (بسيطة/كبيرة/حرجة)
        * المبلّغ والملاحظات والأدلّة (ملف مرفق)
        * الإجراء المتّخذ (تحذير، صفر، إيقاف، فصل، إعادة، لا شيء)
        * تفاصيل الإجراء

    سير العمل:
        ``reported`` → ``investigated`` → ``decided`` → ``closed``
    """
    _name = 'uni.exam.violation'
    _description = 'Exam Violation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'violation_date desc, name'

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Reference', required=True, copy=False, default=_('New'),
        tracking=True, index=True,
        help='Auto-generated reference for the violation (VIO/...).')
    code = fields.Char(
        string='Code', copy=False, index=True, tracking=True,
        help='Optional human-readable code for the violation.')

    # ------------------------------------------------------------------
    # Relations
    # ------------------------------------------------------------------
    exam_id = fields.Many2one(
        'uni.exam', string='Exam', required=True, ondelete='restrict',
        tracking=True, index=True)
    student_name = fields.Char(
        string='Student Name', required=True, tracking=True, index=True,
        help='Name of the student who committed the violation. Stored as '
             'plain text to avoid a hard dependency on university_student.')
    student_code = fields.Char(
        string='Student Code', copy=False, index=True, tracking=True,
        help='Internal code of the student (e.g. STU/2025/00001). Optional.')
    university_id = fields.Many2one(
        'uni.university', string='University', store=True,
        related='exam_id.university_id', index=True)
    academic_term_id = fields.Many2one(
        'uni.academic.term', string='Academic Term', store=True,
        related='exam_id.academic_term_id', index=True)
    course_id = fields.Many2one(
        'uni.course', string='Course', store=True,
        related='exam_id.course_id', index=True)
    reported_by = fields.Many2one(
        'res.users', string='Reported By', default=lambda self: self.env.user,
        ondelete='restrict', tracking=True, index=True)

    # ------------------------------------------------------------------
    # Violation details
    # ------------------------------------------------------------------
    violation_type = fields.Selection([
        ('cheating', 'Cheating'),
        ('impersonation', 'Impersonation'),
        ('late_arrival', 'Late Arrival'),
        ('early_departure', 'Early Departure'),
        ('disruption', 'Disruption'),
        ('use_of_phone', 'Use of Phone'),
        ('bringing_unauthorized_materials', 'Unauthorized Materials'),
        ('other', 'Other'),
    ], string='Violation Type', default='cheating', required=True, tracking=True,
        index=True)
    violation_date = fields.Datetime(
        string='Violation Date', default=fields.Datetime.now, tracking=True,
        index=True)
    description = fields.Text(
        string='Description', translate=True, required=True,
        help='Detailed description of what happened.')
    severity = fields.Selection([
        ('minor', 'Minor'),
        ('major', 'Major'),
        ('critical', 'Critical'),
    ], string='Severity', default='minor', required=True, tracking=True, index=True)

    # ------------------------------------------------------------------
    # Action taken
    # ------------------------------------------------------------------
    action_taken = fields.Selection([
        ('warning', 'Warning'),
        ('zero_score', 'Zero Score'),
        ('suspension', 'Suspension'),
        ('expulsion', 'Expulsion'),
        ('reschedule', 'Reschedule'),
        ('no_action', 'No Action'),
    ], string='Action Taken', tracking=True, index=True)
    action_details = fields.Text(
        string='Action Details', translate=True,
        help='Detailed description of the action taken.')

    # ------------------------------------------------------------------
    # Evidence
    # ------------------------------------------------------------------
    evidence_file = fields.Binary(
        string='Evidence File', attachment=True,
        help='Uploaded evidence (photo, document, video...) supporting the report.')
    evidence_filename = fields.Char(string='Evidence Filename')

    # ------------------------------------------------------------------
    # State & notes
    # ------------------------------------------------------------------
    state = fields.Selection([
        ('reported', 'Reported'),
        ('investigated', 'Investigated'),
        ('decided', 'Decided'),
        ('closed', 'Closed'),
    ], string='State', default='reported', tracking=True, index=True,
        group_expand='_group_expand_states')
    notes = fields.Text(string='Notes', translate=True)

    _sql_constraints = [
        ('unique_exam_student_type',
         'unique(exam_id, student_name, student_code, violation_type)',
         'A student cannot have two violations of the same type in one exam!'),
    ]

    # ------------------------------------------------------------------
    # Group expansion helper
    # ------------------------------------------------------------------
    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in self._fields['state'].selection]

    # ------------------------------------------------------------------
    # Create — auto-generate reference from ir.sequence
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('uni.exam.violation') or _('VIO-NEW')
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_investigate(self):
        """Move the violation into the investigated state."""
        for rec in self:
            if rec.state != 'reported':
                raise ValidationError(_(
                    "Only reported violations can be investigated (current state: %(state)s).")
                    % {'state': rec.state})
            rec.state = 'investigated'
            rec.message_post(body=_('Investigation started.'))

    def action_decide(self):
        """Mark a decision as taken — requires an action_taken value."""
        for rec in self:
            if rec.state != 'investigated':
                raise ValidationError(_(
                    "Only investigated violations can be decided (current state: %(state)s).")
                    % {'state': rec.state})
            if not rec.action_taken:
                raise ValidationError(_(
                    "Cannot decide violation '%s' without specifying an action taken.")
                    % rec.display_name)
            rec.state = 'decided'
            rec.message_post(body=_('Decision recorded: %s.') % dict(
                self._fields['action_taken'].selection).get(rec.action_taken, rec.action_taken))

    def action_close(self):
        """Close the violation."""
        for rec in self:
            if rec.state != 'decided':
                raise ValidationError(_(
                    "Only decided violations can be closed (current state: %(state)s).")
                    % {'state': rec.state})
            rec.state = 'closed'
            rec.message_post(body=_('Violation closed.'))

    def action_reopen(self):
        """Reopen a closed or decided violation for further investigation."""
        for rec in self:
            if rec.state not in ('decided', 'closed'):
                raise ValidationError(_(
                    "Only decided or closed violations can be reopened."))
            rec.state = 'investigated'
            rec.message_post(body=_('Violation reopened for further investigation.'))

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    # (Previously a cross-affiliation constraint ``_check_student_in_exam``
    # lived here, validating that the student record's university matched
    # the exam's university. It was removed because ``student_id`` has been
    # converted to plain-text ``student_name`` + ``student_code`` fields to
    # avoid a hard dependency on ``university_student``; cross-checking a
    # Char against ``uni.exam.university_id`` is not meaningful.)

    @api.constrains('severity', 'action_taken')
    def _check_critical_severity_action(self):
        """Critical violations must receive a non-trivial action."""
        for rec in self:
            if rec.severity == 'critical' and rec.action_taken == 'no_action':
                raise ValidationError(_(
                    "A critical violation cannot be resolved with 'No Action' "
                    "(violation %s).") % rec.display_name)
