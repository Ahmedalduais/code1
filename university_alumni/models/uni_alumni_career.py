# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniAlumniCareer(models.Model):
    """المسار المهني للخريج — منصب وظيفي في سجل الخريج.

    يمثّل كل سجل منصباً وظيفياً شغله الخريج (أو يشغله حالياً) مع
    تفاصيل الراتب والمسؤوليات والمهارات. يسمح ببناء المسار المهني
    الكامل للخريج عبر الزمن، ويمكن استخدام البيانات لإحصاءات
    التوظيف ودعم التوجيه المهني للطلاب الحاليين.
    """
    _name = 'uni.alumni.career'
    _description = 'Alumni Career'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_date desc, id desc'

    # ------------------------------------------------------------------
    # Identity & reference
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Reference', copy=False, readonly=True, index=True,
        default=lambda self: _('New'), tracking=True,
        help='Auto-generated career record reference (ACR/...).')
    code = fields.Char(
        string='Code', copy=False, index=True, tracking=True,
        help='Optional manual code identifying the career record.')

    # ------------------------------------------------------------------
    # Member & job
    # ------------------------------------------------------------------
    member_id = fields.Many2one(
        'uni.alumni.member', string='Alumni Member',
        required=True, ondelete='cascade', tracking=True, index=True)
    university_id = fields.Many2one(
        'uni.university', string='University',
        related='member_id.university_id', store=True, index=True)

    job_title = fields.Char(
        string='Job Title', required=True, tracking=True, index=True)
    employer = fields.Char(
        string='Employer', required=True, tracking=True, index=True)
    industry = fields.Char(string='Industry', tracking=True)

    employment_type = fields.Selection([
        ('full_time', 'Full-Time'),
        ('part_time', 'Part-Time'),
        ('contract', 'Contract'),
        ('internship', 'Internship'),
        ('freelance', 'Freelance'),
    ], string='Employment Type', default='full_time', tracking=True, index=True)

    # ------------------------------------------------------------------
    # Dates
    # ------------------------------------------------------------------
    start_date = fields.Date(
        string='Start Date', required=True, tracking=True,
        default=fields.Date.context_today)
    end_date = fields.Date(
        string='End Date', tracking=True,
        help='Date the position ended (leave empty for current position).')
    is_current = fields.Boolean(
        string='Current Position', default=True, tracking=True,
        help='Check if this is the current active position.')

    # ------------------------------------------------------------------
    # Location & compensation
    # ------------------------------------------------------------------
    location = fields.Char(string='Location', tracking=True)
    country_id = fields.Many2one(
        'res.country', string='Country', tracking=True, index=True)
    salary_range = fields.Selection([
        ('entry', 'Entry Level'),
        ('junior', 'Junior'),
        ('mid', 'Mid-Level'),
        ('senior', 'Senior'),
        ('executive', 'Executive'),
    ], string='Salary Range', tracking=True, index=True,
        help='Approximate salary band for statistical purposes only.')

    # ------------------------------------------------------------------
    # Description
    # ------------------------------------------------------------------
    responsibilities = fields.Text(string='Responsibilities')
    achievements = fields.Text(string='Achievements')
    skills_used = fields.Char(
        string='Skills Used', tracking=True,
        help='Comma-separated list of skills applied in this role.')

    mentor_available = fields.Boolean(
        string='Mentor Available', default=False, tracking=True,
        help='If set, the alumnus is willing to mentor students in this role.')

    # ------------------------------------------------------------------
    # Misc
    # ------------------------------------------------------------------
    notes = fields.Text(string='Notes')
    active = fields.Boolean(string='Active', default=True, tracking=True)
    color = fields.Integer(string='Color Index')

    _sql_constraints = [
        ('unique_career_code', 'unique(code)',
         'Career code must be unique!'),
    ]

    # ------------------------------------------------------------------
    # Create — auto-sequence the career record reference
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.alumni.career') or _('ACR-NEW')
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Onchange
    # ------------------------------------------------------------------
    @api.onchange('is_current')
    def _onchange_is_current(self):
        """Clear end date when marking as current position."""
        if self.is_current:
            self.end_date = False

    @api.onchange('end_date')
    def _onchange_end_date(self):
        """If end date is set, the position is no longer current."""
        if self.end_date:
            self.is_current = False

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_end_position(self):
        """End the current position.

        Sets ``is_current`` to False and ``end_date`` to today.
        """
        for rec in self:
            if not rec.is_current:
                raise ValidationError(_(
                    "Position %(n)s is already ended.") % {
                    'n': rec.display_name})
            rec.is_current = False
            if not rec.end_date:
                rec.end_date = fields.Date.context_today(rec)
            rec.message_post(body=_(
                "Position '%(t)s' at %(e)s ended on %(d)s.") % {
                't': rec.job_title,
                'e': rec.employer,
                'd': rec.end_date,
            })

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        """End date must be on or after start date."""
        for rec in self:
            if rec.start_date and rec.end_date and rec.end_date < rec.start_date:
                raise ValidationError(_(
                    "End date (%(e)s) must be on or after start date "
                    "(%(s)s) for career record %(n)s.") % {
                    'e': rec.end_date, 's': rec.start_date,
                    'n': rec.display_name})

    @api.constrains('is_current', 'end_date')
    def _check_current_has_no_end_date(self):
        """A current position should not have an end date."""
        for rec in self:
            if rec.is_current and rec.end_date:
                raise ValidationError(_(
                    "A current position cannot have an end date (%(n)s, "
                    "end date: %(e)s).") % {
                    'n': rec.display_name,
                    'e': rec.end_date,
                })

    @api.constrains('member_id', 'is_current')
    def _check_single_current_position(self):
        """Only one current position is allowed per alumni member."""
        for rec in self:
            if not rec.is_current:
                continue
            domain = [
                ('member_id', '=', rec.member_id.id),
                ('is_current', '=', True),
                ('id', '!=', rec.id),
            ]
            if self.search_count(domain):
                raise ValidationError(_(
                    "Alumni member %(m)s already has an active current "
                    "position. Please end the existing position before "
                    "marking a new one as current.") % {
                    'm': rec.member_id.display_name})
