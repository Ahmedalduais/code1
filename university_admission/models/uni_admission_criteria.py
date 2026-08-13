# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniAdmissionCriteria(models.Model):
    """معايير القبول — قواعد تقييم الطلبات الواردة.

    يمكن ربط المعايير ببرنامج محدد أو كلية محددة، أو تركها فارغة
    لتُطبَّق على جميع الطلبات (المعيار العام). عند التقييم تُفحص
    الحدود الدنيا (المعدل / GPA / درجة الاختبار / العمر) وكذلك
    إلزامية المقابلة، ويُعاد ``True`` فقط إذا اجتاز التطبيق كل الشروط.
    """
    _name = 'uni.admission.criteria'
    _description = 'Admission Criteria'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'university_id, college_id, program_id, sequence'

    name = fields.Char(
        string='Criteria Name', required=True, translate=True, tracking=True)
    code = fields.Char(
        string='Code', required=True, copy=False, index=True, tracking=True)
    sequence = fields.Integer(string='Sequence', default=10)
    description = fields.Text(string='Description', translate=True)

    # ------------------------------------------------------------------
    # Scope — empty means "applies to all"
    # ------------------------------------------------------------------
    university_id = fields.Many2one(
        'uni.university', string='University',
        required=True, ondelete='restrict', tracking=True, index=True)
    college_id = fields.Many2one(
        'uni.college', string='College',
        ondelete='restrict', tracking=True, index=True,
        help='Restrict these criteria to a specific college (optional).')
    program_id = fields.Many2one(
        'uni.program', string='Program',
        ondelete='restrict', tracking=True, index=True,
        help='Restrict these criteria to a specific program (optional).')
    level_id = fields.Many2one(
        'uni.program.level', string='Program Level',
        ondelete='restrict', tracking=True)

    # ------------------------------------------------------------------
    # Thresholds
    # ------------------------------------------------------------------
    min_high_school_grade = fields.Float(
        string='Min High School Grade', digits=(5, 2), tracking=True,
        help='Minimum high school grade (percentage) required.')
    min_gpa = fields.Float(
        string='Min GPA', digits=(4, 2), tracking=True,
        help='Minimum GPA (out of 4.0) required.')
    min_test_score = fields.Float(
        string='Min Test Score', digits=(5, 2), tracking=True,
        help='Minimum score on the standardized test specified below.')
    test_type = fields.Selection([
        ('sat', 'SAT'),
        ('act', 'ACT'),
        ('gre', 'GRE'),
        ('gmat', 'GMAT'),
        ('ielts', 'IELTS'),
        ('toefl', 'TOEFL'),
        ('other', 'Other'),
    ], string='Test Type', tracking=True)
    interview_required = fields.Boolean(
        string='Interview Required', default=False, tracking=True)
    min_age = fields.Integer(
        string='Min Age', default=0, tracking=True,
        help='Minimum age at the time of application (0 = no minimum).')
    max_age = fields.Integer(
        string='Max Age', default=0, tracking=True,
        help='Maximum age at the time of application (0 = no maximum).')

    # ------------------------------------------------------------------
    # Application fee
    # ------------------------------------------------------------------
    application_fee = fields.Float(
        string='Application Fee', digits=(10, 2), default=0.0, tracking=True)
    application_fee_currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
        tracking=True)

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------
    is_active = fields.Boolean(
        string='Active', default=True, tracking=True,
        help='Whether these criteria are currently being used to evaluate applications.')
    active = fields.Boolean(default=True)
    color = fields.Integer(string='Color Index')

    _sql_constraints = [
        ('unique_criteria_code', 'unique(code)',
         'Criteria code must be unique!'),
    ]

    # ------------------------------------------------------------------
    # Onchange — keep hierarchy consistent
    # ------------------------------------------------------------------
    @api.onchange('college_id')
    def _onchange_college_id(self):
        if self.college_id:
            self.university_id = self.college_id.university_id

    @api.onchange('program_id')
    def _onchange_program_id(self):
        if self.program_id:
            self.university_id = self.program_id.university_id
            self.college_id = self.program_id.college_id
            self.level_id = self.program_id.level_id

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('min_age', 'max_age')
    def _check_age_range(self):
        for rec in self:
            if rec.min_age < 0:
                raise ValidationError(_(
                    "Minimum age cannot be negative (criteria %s).")
                    % rec.display_name)
            if rec.max_age > 0 and rec.max_age < rec.min_age:
                raise ValidationError(_(
                    "Maximum age (%(max)d) cannot be lower than minimum age "
                    "(%(min)d) for criteria %(n)s.") % {
                    'max': rec.max_age, 'min': rec.min_age,
                    'n': rec.display_name})

    @api.constrains('min_high_school_grade', 'min_gpa', 'min_test_score')
    def _check_thresholds_non_negative(self):
        for rec in self:
            if rec.min_high_school_grade < 0:
                raise ValidationError(_(
                    "Minimum high school grade cannot be negative (%s).")
                    % rec.display_name)
            if rec.min_gpa < 0:
                raise ValidationError(_(
                    "Minimum GPA cannot be negative (%s).")
                    % rec.display_name)
            if rec.min_test_score < 0:
                raise ValidationError(_(
                    "Minimum test score cannot be negative (%s).")
                    % rec.display_name)

    # ------------------------------------------------------------------
    # Business logic
    # ------------------------------------------------------------------
    def evaluate_application(self, application):
        """Evaluate whether ``application`` meets these criteria.

        :param application: ``uni.admission.application`` recordset (single)
        :return: ``True`` if the application passes, ``False`` otherwise.
        """
        self.ensure_one()
        if not application:
            return False

        # High school grade (only enforced when the criterion is set)
        if self.min_high_school_grade > 0:
            if application.high_school_grade_type != 'percentage':
                return False
            if (application.high_school_grade or 0.0) < self.min_high_school_grade:
                return False

        # GPA threshold (only enforced when criterion is set)
        if self.min_gpa > 0:
            if application.high_school_grade_type != 'gpa':
                return False
            if (application.high_school_grade or 0.0) < self.min_gpa:
                return False

        # Standardized test score (best-effort — relies on the high_school_grade
        # fallback if no dedicated test score field exists)
        if self.min_test_score > 0:
            if (application.high_school_grade or 0.0) < self.min_test_score:
                return False

        # Interview required?
        if self.interview_required and not application.interview_ids:
            return False

        # Age range (uses applicant_birth_date when available)
        if application.applicant_birth_date and (self.min_age > 0 or self.max_age > 0):
            today = fields.Date.context_today(self)
            age = today.year - application.applicant_birth_date.year - (
                (today.month, today.day) <
                (application.applicant_birth_date.month,
                 application.applicant_birth_date.day))
            if self.min_age > 0 and age < self.min_age:
                return False
            if self.max_age > 0 and age > self.max_age:
                return False

        return True

    @api.model
    def _get_applicable_criteria(self, application):
        """Return the most specific criteria applicable to ``application``.

        Preference order: program-level → college-level → university-level.
        """
        domain = [
            ('university_id', '=', application.university_id.id),
            ('is_active', '=', True),
            ('active', '=', True),
        ]
        # Try program-scoped first
        if application.program_id:
            program_crit = self.search(domain + [
                ('program_id', '=', application.program_id.id),
            ], limit=1, order='sequence asc')
            if program_crit:
                return program_crit
        # Then college-scoped
        if application.college_id:
            college_crit = self.search(domain + [
                ('college_id', '=', application.college_id.id),
                ('program_id', '=', False),
            ], limit=1, order='sequence asc')
            if college_crit:
                return college_crit
        # Fallback to university-wide
        return self.search(domain + [
            ('college_id', '=', False),
            ('program_id', '=', False),
        ], limit=1, order='sequence asc')

    def action_evaluate_application(self):
        """Wizard-less helper: evaluate the criteria's matching application.

        When called from the criteria form (single record) and there is an
        active context ``default_application_id``, evaluate it and post a
        message with the result.
        """
        self.ensure_one()
        application_id = self.env.context.get('active_application_id') \
            or self.env.context.get('default_application_id')
        if not application_id:
            return True
        application = self.env['uni.admission.application'].browse(application_id)
        if not application.exists():
            return True
        passed = self.evaluate_application(application)
        self.message_post(body=_(
            "Evaluation for application %(ref)s: %(result)s") % {
            'ref': application.display_name,
            'result': _('PASSED') if passed else _('FAILED')})
        return passed
