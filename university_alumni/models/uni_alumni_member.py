# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniAlumniMember(models.Model):
    """الخريج — سجل لكل طالب تخرج من الجامعة.

    يربط سجل الخريج بسجل الطالب الأصلي (``uni.student``) ليُورّث
    منه بيانات الهوية والاتصال والانتماء الأكاديمي. يضم بيانات
    التوظيف الحالية وروابط التواصل الاجتماعي وحالة العضوية، إضافة
    إلى ارتباطات بالتبرعات والفعاليات والشبكات المهنية والمسار
    المهني الكامل للخريج.
    """
    _name = 'uni.alumni.member'
    _description = 'Alumni Member'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'graduation_year desc, name'

    # ------------------------------------------------------------------
    # Identity & reference
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Reference', copy=False, readonly=True, index=True,
        default=lambda self: _('New'), tracking=True,
        help='Auto-generated alumni member reference (ALM/...).')
    code = fields.Char(
        string='Code', copy=False, index=True, tracking=True,
        help='Optional manual code identifying the alumnus/alumna.')

    student_id = fields.Many2one(
        'uni.student', string='Student',
        required=True, ondelete='restrict', tracking=True, index=True,
        help='The student record this alumni profile originates from.')

    # ------------------------------------------------------------------
    # Academic affiliation (related from student)
    # ------------------------------------------------------------------
    person_id = fields.Many2one(
        'uni.person', string='Person',
        related='student_id.person_id', store=True, index=True,
        help='Delegated person record (identity & contact).')
    university_id = fields.Many2one(
        'uni.university', string='University',
        related='student_id.university_id', store=True, index=True)
    college_id = fields.Many2one(
        'uni.college', string='College',
        related='student_id.college_id', store=True, index=True)
    department_id = fields.Many2one(
        'uni.department', string='Department',
        related='student_id.department_id', store=True, index=True)
    program_id = fields.Many2one(
        'uni.program', string='Program',
        related='student_id.program_id', store=True, index=True)

    graduation_date = fields.Date(
        string='Graduation Date',
        related='student_id.actual_graduation_date', store=True,
        help='Actual graduation date inherited from the student record.')
    graduation_year = fields.Integer(
        string='Graduation Year',
        compute='_compute_graduation_year', store=True, index=True,
        help='Year extracted from the graduation date, used for cohort reporting.')
    final_gpa = fields.Float(
        string='Final GPA', digits=(4, 2),
        related='student_id.cumulative_gpa', store=True,
        help='Final cumulative GPA from the student record.')
    degree_received = fields.Char(
        string='Degree Received', tracking=True,
        help='Degree title awarded (e.g. B.Sc. Computer Science).')

    # ------------------------------------------------------------------
    # Membership
    # ------------------------------------------------------------------
    membership_date = fields.Date(
        string='Membership Date', default=fields.Date.context_today,
        tracking=True, help='Date the alumni membership started.')
    membership_status = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('honorary', 'Honorary'),
        ('lifetime', 'Lifetime'),
    ], string='Membership Status', default='active',
        tracking=True, index=True, group_expand='_group_expand_membership_status')

    # ------------------------------------------------------------------
    # Current employment
    # ------------------------------------------------------------------
    current_employment_status = fields.Selection([
        ('employed', 'Employed'),
        ('self_employed', 'Self-Employed'),
        ('unemployed', 'Unemployed'),
        ('further_study', 'Further Study'),
        ('other', 'Other'),
    ], string='Employment Status', tracking=True)
    current_job_title = fields.Char(string='Current Job Title', tracking=True)
    current_employer = fields.Char(string='Current Employer', tracking=True)
    industry = fields.Char(string='Industry', tracking=True)
    work_email = fields.Char(string='Work Email', tracking=True)
    work_phone = fields.Char(string='Work Phone', tracking=True)

    # ------------------------------------------------------------------
    # Social links
    # ------------------------------------------------------------------
    linkedin_url = fields.Char(string='LinkedIn URL', tracking=True)
    twitter_url = fields.Char(string='Twitter / X URL', tracking=True)
    facebook_url = fields.Char(string='Facebook URL', tracking=True)
    personal_website = fields.Char(string='Personal Website', tracking=True)

    # ------------------------------------------------------------------
    # Address
    # ------------------------------------------------------------------
    address = fields.Text(string='Address', tracking=True)
    city = fields.Char(string='City', tracking=True)
    country_id = fields.Many2one(
        'res.country', string='Country', tracking=True, index=True)

    # ------------------------------------------------------------------
    # Mentorship & volunteering
    # ------------------------------------------------------------------
    is_mentor = fields.Boolean(
        string='Mentor', default=False, tracking=True,
        help='Check if this alumnus is available as a mentor.')
    mentor_expertise = fields.Char(
        string='Mentor Expertise', tracking=True,
        help='Area(s) of expertise offered as a mentor.')
    is_volunteer = fields.Boolean(
        string='Volunteer', default=False, tracking=True,
        help='Check if this alumnus is available as a volunteer.')

    # ------------------------------------------------------------------
    # Relations
    # ------------------------------------------------------------------
    donation_ids = fields.One2many(
        'uni.alumni.donation', 'member_id', string='Donations')
    event_ids = fields.Many2many(
        'uni.alumni.event', 'uni_alumni_event_member_rel',
        'member_id', 'event_id', string='Events')
    network_ids = fields.Many2many(
        'uni.alumni.network', 'uni_alumni_network_member_rel',
        'member_id', 'network_id', string='Networks')
    career_ids = fields.One2many(
        'uni.alumni.career', 'member_id', string='Career History')

    # ------------------------------------------------------------------
    # Computed
    # ------------------------------------------------------------------
    total_donations = fields.Monetary(
        string='Total Donations', currency_field='currency_id',
        compute='_compute_total_donations', store=True,
        help='Sum of received donations in the member currency.')
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        related='university_id.currency_id', store=True,
        help='Default currency inherited from the university.')
    donation_count = fields.Integer(
        string='Donation Count', compute='_compute_total_donations')
    event_count = fields.Integer(
        string='Event Count', compute='_compute_event_count')
    network_count = fields.Integer(
        string='Network Count', compute='_compute_network_count')
    career_count = fields.Integer(
        string='Career Records', compute='_compute_career_count')

    notes = fields.Text(string='Notes')
    active = fields.Boolean(string='Active', default=True, tracking=True)
    color = fields.Integer(string='Color Index')

    _sql_constraints = [
        ('unique_alumni_code', 'unique(code)',
         'Alumni code must be unique!'),
        ('unique_alumni_student', 'unique(student_id)',
         'A student can only have one alumni record!'),
    ]

    # ------------------------------------------------------------------
    # Group expansion
    # ------------------------------------------------------------------
    def _group_expand_membership_status(self, states, domain, order):
        return [key for key, _ in self._fields['membership_status'].selection]

    # ------------------------------------------------------------------
    # Computed methods
    # ------------------------------------------------------------------
    @api.depends('graduation_date')
    def _compute_graduation_year(self):
        """Extract the year from the graduation date."""
        for rec in self:
            if rec.graduation_date:
                rec.graduation_year = rec.graduation_date.year
            else:
                rec.graduation_year = 0

    @api.depends('donation_ids.amount', 'donation_ids.state', 'donation_ids.currency_id')
    def _compute_total_donations(self):
        """Sum of all received donations.

        Donations in the *received* state are summed at their face value
        in the member's currency. Multi-currency aggregation is left to
        the accounting module when present; here we sum face values.
        """
        for rec in self:
            received = rec.donation_ids.filtered(
                lambda d: d.state == 'received')
            rec.total_donations = sum(received.mapped('amount'))
            rec.donation_count = len(rec.donation_ids)

    @api.depends('event_ids')
    def _compute_event_count(self):
        for rec in self:
            rec.event_count = len(rec.event_ids)

    @api.depends('network_ids')
    def _compute_network_count(self):
        for rec in self:
            rec.network_count = len(rec.network_ids)

    @api.depends('career_ids')
    def _compute_career_count(self):
        for rec in self:
            rec.career_count = len(rec.career_ids)

    # ------------------------------------------------------------------
    # Create — auto-sequence the alumni reference
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.alumni.member') or _('ALM-NEW')
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Membership workflow actions
    # ------------------------------------------------------------------
    def action_activate(self):
        """Mark the alumni membership as active."""
        for rec in self:
            rec.membership_status = 'active'
            rec.message_post(body=_("Alumni membership activated."))

    def action_deactivate(self):
        """Mark the alumni membership as inactive."""
        for rec in self:
            rec.membership_status = 'inactive'
            rec.message_post(body=_("Alumni membership deactivated."))

    def action_make_honorary(self):
        """Promote the alumni member to honorary status."""
        for rec in self:
            rec.membership_status = 'honorary'
            rec.message_post(body=_("Alumni membership set to Honorary."))

    def action_make_lifetime(self):
        """Promote the alumni member to lifetime status."""
        for rec in self:
            rec.membership_status = 'lifetime'
            rec.message_post(body=_("Alumni membership set to Lifetime."))

    # ------------------------------------------------------------------
    # Smart-button actions
    # ------------------------------------------------------------------
    def action_view_donations(self):
        """Open the donations list for this member."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Donations'),
            'res_model': 'uni.alumni.donation',
            'view_mode': 'list,form',
            'domain': [('member_id', '=', self.id)],
            'context': {'default_member_id': self.id},
        }

    def action_view_events(self):
        """Open the events list for this member."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Events'),
            'res_model': 'uni.alumni.event',
            'view_mode': 'list,form',
            'domain': [('member_ids', 'in', self.id)],
        }

    def action_view_networks(self):
        """Open the networks list for this member."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Networks'),
            'res_model': 'uni.alumni.network',
            'view_mode': 'list,form',
            'domain': [('member_ids', 'in', self.id)],
        }

    def action_view_careers(self):
        """Open the career history for this member."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Career History'),
            'res_model': 'uni.alumni.career',
            'view_mode': 'list,form',
            'domain': [('member_id', '=', self.id)],
            'context': {'default_member_id': self.id},
        }

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('student_id')
    def _check_student_graduated(self):
        """The linked student should be in the ``graduated`` state.

        Alumni records are intended for graduated students. We allow
        the link to be created ahead of the state flip (e.g. for a
        graduating cohort) but post an informational message in the
        chatter so the user is aware.
        """
        for rec in self:
            if rec.student_id and rec.student_id.state != 'graduated':
                rec.message_post(body=_(
                    "Note: linked student %(s)s is currently in state "
                    "'%(st)s' (not yet graduated).") % {
                    's': rec.student_id.display_name,
                    'st': rec.student_id.state,
                })
