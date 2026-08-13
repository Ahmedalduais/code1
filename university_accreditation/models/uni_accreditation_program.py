# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniAccreditationProgram(models.Model):
    """اعتماد البرنامج — يمثل طلب/حالة اعتماد برنامج دراسي لدى جهة اعتماد.

    سير العمل:
        pending → in_progress → granted ⇄ probation → revoked / expired

    يحتوي على خطوط تقييم المعايير (standards_line_ids) ويحسب الدرجة
    الكلية (overall_score) كمتوسط موزون بالأوزان لكل معيار.
    """
    _name = 'uni.accreditation.program'
    _description = 'Program Accreditation'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'accreditation_status, expiry_date, id'

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Reference', copy=False, readonly=True, index=True,
        default='New', tracking=True,
        help='Auto-generated reference identifying this accreditation.')
    code = fields.Char(
        string='Code', copy=False, tracking=True, index=True,
        help='Optional human-friendly code for this accreditation.')

    # ------------------------------------------------------------------
    # Program context
    # ------------------------------------------------------------------
    program_id = fields.Many2one(
        'uni.program', string='Program',
        required=True, ondelete='restrict', tracking=True, index=True,
        help='The academic program being accredited.')
    university_id = fields.Many2one(
        'uni.university', string='University',
        related='program_id.university_id', store=True, index=True)
    college_id = fields.Many2one(
        'uni.college', string='College',
        related='program_id.college_id', store=True, index=True)
    department_id = fields.Many2one(
        'uni.department', string='Department',
        related='program_id.department_id', store=True, index=True)

    # ------------------------------------------------------------------
    # Accreditation body
    # ------------------------------------------------------------------
    accreditation_body_id = fields.Many2one(
        'uni.accreditation.body', string='Accreditation Body',
        required=True, ondelete='restrict', tracking=True, index=True,
        help='The accreditation body issuing the accreditation.')

    # ------------------------------------------------------------------
    # Dates / duration
    # ------------------------------------------------------------------
    accreditation_date = fields.Date(
        string='Accreditation Date', tracking=True,
        help='Date the accreditation was officially granted.')
    expiry_date = fields.Date(
        string='Expiry Date', tracking=True,
        help='Date the accreditation expires.')
    duration_years = fields.Integer(
        string='Duration (Years)', default=5, tracking=True,
        help='Number of years the accreditation remains valid.')

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    accreditation_status = fields.Selection([
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('granted', 'Granted'),
        ('probation', 'Probation'),
        ('revoked', 'Revoked'),
        ('expired', 'Expired'),
    ], string='Status', default='pending', tracking=True, index=True,
        group_expand='_group_expand_statuses')

    # ------------------------------------------------------------------
    # Relations
    # ------------------------------------------------------------------
    report_ids = fields.One2many(
        'uni.accreditation.report', 'accreditation_program_id',
        string='Reports')
    report_count = fields.Integer(
        compute='_compute_report_count', string='Reports')
    self_study_id = fields.Many2one(
        'uni.self.study', string='Self Study',
        ondelete='set null', tracking=True,
        help='Self-study document associated with this accreditation.')
    standards_line_ids = fields.One2many(
        'uni.accreditation.program.standard', 'accreditation_program_id',
        string='Standards Assessment', copy=True)

    # ------------------------------------------------------------------
    # Computed
    # ------------------------------------------------------------------
    overall_score = fields.Float(
        string='Overall Score', digits=(5, 2), default=0.0,
        compute='_compute_overall_score', store=True,
        help='Weighted average score across all assessed standards.')
    standard_count = fields.Integer(
        compute='_compute_standard_count', string='Standards')

    notes = fields.Text(string='Notes')

    # ------------------------------------------------------------------
    # SQL constraints
    # ------------------------------------------------------------------
    _sql_constraints = [
        ('unique_program_body',
         'unique(program_id, accreditation_body_id)',
         'An accreditation already exists for this program and body!'),
        ('check_duration_positive',
         'CHECK(duration_years >= 0)',
         'Accreditation duration must be positive or zero!'),
    ]

    # ------------------------------------------------------------------
    # Group expansion helper
    # ------------------------------------------------------------------
    def _group_expand_statuses(self, states, domain, order):
        return [key for key, _ in self._fields['accreditation_status'].selection]

    # ------------------------------------------------------------------
    # Computed: overall score, counts
    # ------------------------------------------------------------------
    @api.depends(
        'standards_line_ids',
        'standards_line_ids.score',
        'standards_line_ids.weight',
        'standards_line_ids.status')
    def _compute_overall_score(self):
        """Compute weighted average of standard scores.

        Only standards with status 'compliant', 'partial', or 'non_compliant'
        contribute to the score. 'not_applicable' standards are excluded
        from both numerator and denominator.
        """
        for rec in self:
            total_weight = 0.0
            weighted_sum = 0.0
            for line in rec.standards_line_ids:
                if line.status == 'not_applicable':
                    continue
                weight = line.weight or 0.0
                score = line.score or 0.0
                total_weight += weight
                weighted_sum += (score * weight)
            if total_weight > 0:
                rec.overall_score = weighted_sum / total_weight
            else:
                rec.overall_score = 0.0

    @api.depends('standards_line_ids')
    def _compute_standard_count(self):
        for rec in self:
            rec.standard_count = len(rec.standards_line_ids)

    @api.depends('report_ids')
    def _compute_report_count(self):
        for rec in self:
            rec.report_count = len(rec.report_ids)

    # ------------------------------------------------------------------
    # Onchange — suggest expiry from duration
    # ------------------------------------------------------------------
    @api.onchange('accreditation_date', 'duration_years')
    def _onchange_dates_duration(self):
        """Suggest expiry_date = accreditation_date + duration_years."""
        if self.accreditation_date and self.duration_years:
            try:
                self.expiry_date = fields.Date.to_date(
                    self.accreditation_date).replace(
                    year=fields.Date.to_date(self.accreditation_date).year
                    + self.duration_years)
            except ValueError:
                # Handle Feb 29 case by falling back to Feb 28
                d = fields.Date.to_date(self.accreditation_date)
                try:
                    self.expiry_date = d.replace(year=d.year + self.duration_years)
                except ValueError:
                    self.expiry_date = d.replace(
                        year=d.year + self.duration_years, day=d.day - 1)

    # ------------------------------------------------------------------
    # Create — auto-generate reference
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.accreditation.program') or _('ACR-NEW')
            if not vals.get('code'):
                program_code = False
                if vals.get('program_id'):
                    program = self.env['uni.program'].browse(vals['program_id'])
                    program_code = program.code or False
                body_code = False
                if vals.get('accreditation_body_id'):
                    body = self.env['uni.accreditation.body'].browse(
                        vals['accreditation_body_id'])
                    body_code = body.code or False
                parts = [p for p in ['ACR', program_code, body_code] if p]
                vals['code'] = '-'.join(parts) if parts else False
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Validations
    # ------------------------------------------------------------------
    @api.constrains('accreditation_date', 'expiry_date')
    def _check_dates(self):
        for rec in self:
            if rec.accreditation_date and rec.expiry_date and \
                    rec.expiry_date < rec.accreditation_date:
                raise ValidationError(_(
                    "Expiry date cannot be earlier than accreditation date "
                    "for accreditation %s.") % rec.display_name)

    @api.constrains('accreditation_status', 'accreditation_date')
    def _check_granted_has_date(self):
        for rec in self:
            if rec.accreditation_status in ('granted', 'probation') and \
                    not rec.accreditation_date:
                raise ValidationError(_(
                    "Accreditation %s cannot be in status '%s' without an "
                    "accreditation date.") %
                    (rec.display_name, dict(
                        self._fields['accreditation_status'].selection
                    ).get(rec.accreditation_status)))

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_start(self):
        """Move accreditation from pending to in_progress."""
        for rec in self:
            if rec.accreditation_status != 'pending':
                raise ValidationError(_(
                    "Only pending accreditations can be started (%s).")
                    % rec.display_name)
            rec.accreditation_status = 'in_progress'
            rec.message_post(body=_(
                "Accreditation process started."))

    def action_grant(self):
        """Grant the accreditation — sets today as accreditation date and
        computes expiry based on duration."""
        for rec in self:
            if rec.accreditation_status not in ('pending', 'in_progress', 'probation'):
                raise ValidationError(_(
                    "Accreditation can only be granted from pending, "
                    "in_progress or probation states (%s).")
                    % rec.display_name)
            rec.accreditation_status = 'granted'
            if not rec.accreditation_date:
                rec.accreditation_date = fields.Date.context_today(rec)
            # Auto-compute expiry if missing
            if not rec.expiry_date and rec.duration_years:
                rec._onchange_dates_duration()
            rec.message_post(body=_(
                "Accreditation granted until %s.") %
                (rec.expiry_date or _('N/A')))

    def action_probation(self):
        """Move a granted accreditation to probation status."""
        for rec in self:
            if rec.accreditation_status != 'granted':
                raise ValidationError(_(
                    "Only granted accreditations can be put on probation (%s).")
                    % rec.display_name)
            rec.accreditation_status = 'probation'
            rec.message_post(body=_(
                "Accreditation put on probation."))

    def action_revoke(self):
        """Revoke the accreditation."""
        for rec in self:
            if rec.accreditation_status not in ('granted', 'probation', 'expired'):
                raise ValidationError(_(
                    "Only granted, probation or expired accreditations can "
                    "be revoked (%s).") % rec.display_name)
            rec.accreditation_status = 'revoked'
            rec.message_post(body=_(
                "Accreditation revoked."))

    def action_expire(self):
        """Mark the accreditation as expired."""
        for rec in self:
            if rec.accreditation_status not in ('granted', 'probation'):
                raise ValidationError(_(
                    "Only granted or probation accreditations can be "
                    "expired (%s).") % rec.display_name)
            rec.accreditation_status = 'expired'
            rec.message_post(body=_(
                "Accreditation expired."))

    def action_reopen(self):
        """Reopen an expired/revoked accreditation back to in_progress."""
        for rec in self:
            if rec.accreditation_status not in ('expired', 'revoked', 'pending'):
                raise ValidationError(_(
                    "Only expired, revoked or pending accreditations can be "
                    "reopened (%s).") % rec.display_name)
            rec.accreditation_status = 'in_progress'
            rec.message_post(body=_(
                "Accreditation reopened."))

    # ------------------------------------------------------------------
    # Smart buttons
    # ------------------------------------------------------------------
    def action_view_reports(self):
        self.ensure_one()
        return {
            'name': _('Reports'),
            'type': 'ir.actions.act_window',
            'res_model': 'uni.accreditation.report',
            'view_mode': 'list,form',
            'domain': [('accreditation_program_id', '=', self.id)],
            'context': {'default_accreditation_program_id': self.id},
        }

    def action_view_standards(self):
        self.ensure_one()
        return {
            'name': _('Standards Assessment'),
            'type': 'ir.actions.act_window',
            'res_model': 'uni.accreditation.program.standard',
            'view_mode': 'list,form',
            'domain': [('accreditation_program_id', '=', self.id)],
            'context': {'default_accreditation_program_id': self.id},
        }

    def action_open_self_study(self):
        """Open the self-study form if linked, otherwise create one."""
        self.ensure_one()
        if self.self_study_id:
            return {
                'name': _('Self Study'),
                'type': 'ir.actions.act_window',
                'res_model': 'uni.self.study',
                'res_id': self.self_study_id.id,
                'view_mode': 'form',
            }
        # Create a new self-study linked to this accreditation
        self_study = self.env['uni.self.study'].create({
            'accreditation_program_id': self.id,
            'program_id': self.program_id.id,
            'name': _('Self Study for %s') % self.display_name,
        })
        self.self_study_id = self_study.id
        return {
            'name': _('Self Study'),
            'type': 'ir.actions.act_window',
            'res_model': 'uni.self.study',
            'res_id': self_study.id,
            'view_mode': 'form',
        }

    # ------------------------------------------------------------------
    # Auto-populate standards from accreditation body
    # ------------------------------------------------------------------
    def action_load_standards(self):
        """Load all top-level standards of the accreditation body into the
        assessment lines. Existing lines are preserved."""
        for rec in self:
            if not rec.accreditation_body_id:
                raise ValidationError(_(
                    "Please set an accreditation body before loading standards."))
            existing_standard_ids = rec.standards_line_ids.mapped('standard_id')
            new_standards = self.env['uni.accreditation.standard'].search([
                ('accreditation_body_id', '=', rec.accreditation_body_id.id),
                ('id', 'not in', existing_standard_ids.ids),
            ])
            lines = []
            for std in new_standards:
                lines.append((0, 0, {
                    'standard_id': std.id,
                    'weight': std.weight,
                    'max_score': 100.0,
                    'status': 'not_applicable',
                }))
            if lines:
                rec.write({'standards_line_ids': lines})
                rec.message_post(body=_(
                    "Loaded %d standards from %s.") %
                    (len(lines), rec.accreditation_body_id.display_name))


class UniAccreditationProgramStandard(models.Model):
    """خط تقييم معيار — يربط اعتماد برنامج بمعيار مع تقييم النتيجة.

    لكل خط: الدرجة المحققة (score)، الدرجة العظمى (max_score)، الوزن
    (weight)، حالة الامتثال (status)، الأدلة، والملاحظات.
    """
    _name = 'uni.accreditation.program.standard'
    _description = 'Program Standard Assessment Line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'accreditation_program_id, standard_id, id'

    # ------------------------------------------------------------------
    # Relations
    # ------------------------------------------------------------------
    accreditation_program_id = fields.Many2one(
        'uni.accreditation.program', string='Accreditation Program',
        required=True, ondelete='cascade', tracking=True, index=True)
    standard_id = fields.Many2one(
        'uni.accreditation.standard', string='Standard',
        required=True, ondelete='restrict', tracking=True, index=True)
    standard_code = fields.Char(
        related='standard_id.code', store=True, index=True)
    standard_name = fields.Char(
        related='standard_id.name', store=True, index=True)
    accreditation_body_id = fields.Many2one(
        'uni.accreditation.body',
        related='standard_id.accreditation_body_id', store=True, index=True)
    minimum_score = fields.Float(
        related='standard_id.minimum_score', string='Minimum Score',
        store=True, digits=(5, 2))

    # ------------------------------------------------------------------
    # Scores
    # ------------------------------------------------------------------
    score = fields.Float(
        string='Score', digits=(5, 2), default=0.0, tracking=True,
        help='Achieved score (0 to max_score).')
    max_score = fields.Float(
        string='Max Score', digits=(5, 2), default=100.0, tracking=True,
        help='Maximum possible score for this standard (usually 100).')
    weight = fields.Float(
        string='Weight', digits=(5, 2), default=1.0, tracking=True,
        help='Weight used in the overall accreditation score computation.')
    percentage = fields.Float(
        string='Percentage', digits=(5, 2), default=0.0,
        compute='_compute_percentage', store=True,
        help='Score as a percentage of max_score.')

    # ------------------------------------------------------------------
    # Status & evidence
    # ------------------------------------------------------------------
    status = fields.Selection([
        ('compliant', 'Compliant'),
        ('partial', 'Partial'),
        ('non_compliant', 'Non Compliant'),
        ('not_applicable', 'Not Applicable'),
    ], string='Status', default='not_applicable',
        tracking=True, index=True,
        help='Compliance status of this standard for the program.')
    is_met = fields.Boolean(
        string='Met', compute='_compute_is_met', store=True,
        help='True if the percentage is at or above the minimum score.')
    evidence = fields.Text(
        string='Evidence', help='Documented evidence of compliance.')
    notes = fields.Text(string='Notes')

    # ------------------------------------------------------------------
    # SQL constraints
    # ------------------------------------------------------------------
    _sql_constraints = [
        ('unique_program_standard',
         'unique(accreditation_program_id, standard_id)',
         'The same standard cannot be assessed twice for one accreditation!'),
        ('check_max_score_positive',
         'CHECK(max_score > 0)',
         'Max score must be strictly positive!'),
        ('check_weight_positive',
         'CHECK(weight >= 0)',
         'Weight must be positive or zero!'),
        ('check_score_range',
         'CHECK(score >= 0 AND score <= max_score)',
         'Score must be between 0 and max_score!'),
    ]

    # ------------------------------------------------------------------
    # Computed
    # ------------------------------------------------------------------
    @api.depends('score', 'max_score')
    def _compute_percentage(self):
        for rec in self:
            if rec.max_score and rec.max_score > 0:
                rec.percentage = (rec.score / rec.max_score) * 100.0
            else:
                rec.percentage = 0.0

    @api.depends('percentage', 'minimum_score', 'status')
    def _compute_is_met(self):
        for rec in self:
            if rec.status == 'not_applicable':
                rec.is_met = True
            elif rec.status in ('compliant',):
                rec.is_met = True
            elif rec.status == 'partial':
                rec.is_met = rec.percentage >= rec.minimum_score
            else:
                # non_compliant
                rec.is_met = False

    # ------------------------------------------------------------------
    # Onchange — pre-fill from standard
    # ------------------------------------------------------------------
    @api.onchange('standard_id')
    def _onchange_standard_id(self):
        """Pre-fill weight, max_score and minimum_score from the standard."""
        if self.standard_id:
            if not self.weight or self.weight == 1.0:
                self.weight = self.standard_id.weight or 1.0
            self.minimum_score = self.standard_id.minimum_score

    @api.onchange('score', 'max_score', 'status')
    def _onchange_score_status(self):
        """Suggest status based on score percentage."""
        if self.status == 'not_applicable':
            return
        if self.max_score > 0:
            pct = (self.score or 0.0) / self.max_score * 100.0
            if pct >= self.minimum_score:
                if pct >= 90:
                    self.status = 'compliant'
                else:
                    self.status = 'partial'
            else:
                self.status = 'non_compliant'

    # ------------------------------------------------------------------
    # Validations
    # ------------------------------------------------------------------
    @api.constrains('accreditation_program_id', 'standard_id')
    def _check_standard_body_consistency(self):
        """The standard must belong to the same accreditation body as the
        accreditation program."""
        for rec in self:
            if rec.accreditation_program_id.accreditation_body_id and \
                    rec.standard_id.accreditation_body_id and \
                    rec.accreditation_program_id.accreditation_body_id \
                    != rec.standard_id.accreditation_body_id:
                raise ValidationError(_(
                    "The standard '%s' does not belong to the accreditation "
                    "body of the program (%s).") %
                    (rec.standard_id.display_name,
                     rec.accreditation_program_id
                     .accreditation_body_id.display_name))
