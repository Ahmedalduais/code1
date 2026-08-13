# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniFaculty(models.Model):
    """عضو هيئة التدريس — التصميم المُصحح.

    يستخدم وراثة التفويض ``_inherits`` من ``uni.person`` (الذي بدوره يفوّض
    ``res.partner``)، بالإضافة إلى ربط ``Many2one`` بـ ``hr.employee`` بدلاً
    من الوراثة المزدوجة المُلغاة.

    يوفّر هذا النموذج إدارة كاملة لدورة حياة عضو هيئة التدريس بما في ذلك:
    الرتبة الأكاديمية، القسم/الكلية، نوع التوظيف، التكليفات التدريسية،
    العبء التدريسي، المنشورات العلمية، وعضوية اللجان.
    """
    _name = 'uni.faculty'
    _description = 'Faculty Member'
    _inherits = {'uni.person': 'person_id'}
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'faculty_code, name'

    # ------------------------------------------------------------------
    # Delegation & HR link (CORRECTED design)
    # ------------------------------------------------------------------
    person_id = fields.Many2one(
        'uni.person', string='Person',
        required=True, ondelete='restrict', auto_join=True, index=True,
        help='Delegated person record holding identity & contact data.')
    hr_employee_id = fields.Many2one(
        'hr.employee', string='HR Employee',
        ondelete='restrict', index=True, tracking=True,
        help='Optional link to the matching HR employee record for payroll/leave integration.')

    # ------------------------------------------------------------------
    # Faculty identity & academic data
    # ------------------------------------------------------------------
    faculty_code = fields.Char(
        string='Faculty Code', copy=False, index=True, tracking=True,
        help='Unique internal code identifying the faculty member.')
    faculty_rank_id = fields.Many2one(
        'uni.faculty.rank', string='Academic Rank',
        ondelete='restrict', tracking=True, index=True)
    department_id = fields.Many2one(
        'uni.department', string='Department',
        ondelete='restrict', tracking=True, index=True)
    college_id = fields.Many2one(
        'uni.college', string='College',
        ondelete='restrict', tracking=True, index=True)
    specialization = fields.Char(string='Specialization', tracking=True,
                                 help='Primary academic specialization (e.g. Machine Learning).')
    research_interests = fields.Text(string='Research Interests')

    # ------------------------------------------------------------------
    # Employment info
    # ------------------------------------------------------------------
    hire_date = fields.Date(string='Hire Date', tracking=True)
    termination_date = fields.Date(string='Termination Date', tracking=True)
    employment_type = fields.Selection([
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('visiting', 'Visiting'),
        ('contract', 'Contract'),
    ], string='Employment Type', default='full_time', tracking=True, index=True)
    office_location = fields.Char(string='Office Location', tracking=True)
    office_phone = fields.Char(string='Office Phone', tracking=True)

    # ------------------------------------------------------------------
    # CV attachment
    # ------------------------------------------------------------------
    cv_file = fields.Binary(string='CV File', attachment=True)
    cv_filename = fields.Char(string='CV Filename')

    # ------------------------------------------------------------------
    # State / lifecycle
    # ------------------------------------------------------------------
    state = fields.Selection([
        ('active', 'Active'),
        ('on_leave', 'On Leave'),
        ('terminated', 'Terminated'),
    ], string='Status', default='active', tracking=True, index=True, group_expand='_group_expand_states')

    # ------------------------------------------------------------------
    # Relations
    # ------------------------------------------------------------------
    assignment_ids = fields.One2many(
        'uni.faculty.assignment', 'faculty_id', string='Teaching Assignments')
    load_ids = fields.One2many(
        'uni.faculty.load', 'faculty_id', string='Teaching Load')
    publication_ids = fields.One2many(
        'uni.faculty.publication', 'faculty_id', string='Publications')
    committee_member_ids = fields.One2many(
        'uni.committee.member', 'faculty_id', string='Committee Memberships')

    # ------------------------------------------------------------------
    # Computed
    # ------------------------------------------------------------------
    total_load_hours = fields.Float(
        compute='_compute_total_load', string='Total Load (Hours)',
        help='Sum of all load hours (teaching + research + admin) for the current term.')
    active_assignment_count = fields.Integer(
        compute='_compute_active_assignment_count', string='Active Assignments')
    publication_count = fields.Integer(
        compute='_compute_publication_count', string='Publications')
    committee_count = fields.Integer(
        compute='_compute_committee_count', string='Committees')

    _sql_constraints = [
        ('unique_faculty_code', 'unique(faculty_code)',
         'Faculty code must be unique!'),
    ]

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------
    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in self._fields['state'].selection]

    @api.depends('load_ids.total_hours')
    def _compute_total_load(self):
        for rec in self:
            rec.total_load_hours = sum(rec.load_ids.mapped('total_hours'))

    @api.depends('assignment_ids.state')
    def _compute_active_assignment_count(self):
        for rec in self:
            rec.active_assignment_count = len(
                rec.assignment_ids.filtered(lambda a: a.state == 'active'))

    @api.depends('publication_ids')
    def _compute_publication_count(self):
        for rec in self:
            rec.publication_count = len(rec.publication_ids)

    @api.depends('committee_member_ids')
    def _compute_committee_count(self):
        for rec in self:
            rec.committee_count = len(rec.committee_member_ids.filtered(lambda m: m.is_active))

    # ------------------------------------------------------------------
    # Onchange helpers — keep hierarchy consistent
    # ------------------------------------------------------------------
    @api.onchange('college_id')
    def _onchange_college_id(self):
        if self.college_id:
            self.university_id = self.college_id.university_id

    @api.onchange('department_id')
    def _onchange_department_id(self):
        if self.department_id:
            self.college_id = self.department_id.college_id
            self.university_id = self.department_id.university_id

    # ------------------------------------------------------------------
    # Create — auto-create uni.person if not provided and set defaults
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Auto-set person_type to faculty for the underlying uni.person
            if not vals.get('person_type'):
                vals['person_type'] = 'faculty'
            # Infer university from college / department if not provided
            if not vals.get('university_id'):
                if vals.get('department_id'):
                    dept = self.env['uni.department'].browse(vals['department_id'])
                    vals['university_id'] = dept.university_id.id
                elif vals.get('college_id'):
                    college = self.env['uni.college'].browse(vals['college_id'])
                    vals['university_id'] = college.university_id.id
            # Auto-generate faculty code if not provided
            if not vals.get('faculty_code'):
                vals['faculty_code'] = self.env['ir.sequence'].next_by_code('uni.faculty') or _('FAC-NEW')
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_activate(self):
        """Mark the faculty member as active (returning from leave, etc.)."""
        for rec in self:
            if rec.state == 'terminated':
                raise ValidationError(_(
                    "Cannot activate a terminated faculty member (%s). "
                    "Re-open the record manually if needed.") % rec.display_name)
            rec.state = 'active'
            if rec.termination_date:
                rec.termination_date = False

    def action_on_leave(self):
        """Place the faculty member on leave."""
        for rec in self:
            if rec.state == 'terminated':
                raise ValidationError(_(
                    "Cannot place a terminated faculty member on leave (%s).") % rec.display_name)
            rec.state = 'on_leave'

    def action_terminate(self):
        """Terminate the faculty member — sets termination date automatically."""
        for rec in self:
            if not rec.termination_date:
                rec.termination_date = fields.Date.context_today(rec)
            rec.state = 'terminated'

    # ------------------------------------------------------------------
    # Smart-button actions
    # ------------------------------------------------------------------
    def action_open_assignments(self):
        self.ensure_one()
        return {
            'name': _('Teaching Assignments'),
            'type': 'ir.actions.act_window',
            'res_model': 'uni.faculty.assignment',
            'view_mode': 'list,form',
            'domain': [('faculty_id', '=', self.id)],
            'context': {'default_faculty_id': self.id},
        }

    def action_open_loads(self):
        self.ensure_one()
        return {
            'name': _('Teaching Load'),
            'type': 'ir.actions.act_window',
            'res_model': 'uni.faculty.load',
            'view_mode': 'list,form',
            'domain': [('faculty_id', '=', self.id)],
            'context': {'default_faculty_id': self.id},
        }

    def action_open_publications(self):
        self.ensure_one()
        return {
            'name': _('Publications'),
            'type': 'ir.actions.act_window',
            'res_model': 'uni.faculty.publication',
            'view_mode': 'list,form',
            'domain': [('faculty_id', '=', self.id)],
            'context': {'default_faculty_id': self.id},
        }

    def action_open_committees(self):
        self.ensure_one()
        return {
            'name': _('Committee Memberships'),
            'type': 'ir.actions.act_window',
            'res_model': 'uni.committee.member',
            'view_mode': 'list,form',
            'domain': [('faculty_id', '=', self.id)],
            'context': {'default_faculty_id': self.id},
        }

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('hire_date', 'termination_date')
    def _check_dates(self):
        for rec in self:
            if rec.hire_date and rec.termination_date and \
                    rec.termination_date < rec.hire_date:
                raise ValidationError(_(
                    "Termination date cannot be earlier than hire date "
                    "for faculty member %s.") % rec.display_name)

    @api.constrains('state', 'termination_date')
    def _check_termination_state(self):
        for rec in self:
            if rec.state == 'terminated' and not rec.termination_date:
                raise ValidationError(_(
                    "A terminated faculty member must have a termination date (%s).")
                    % rec.display_name)
