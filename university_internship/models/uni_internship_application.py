# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class UniInternshipApplication(models.Model):
    _name = 'uni.internship.application'
    _description = 'Internship Application'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'application_date desc'

    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True,
        default=lambda self: _('New'), index=True)
    student_id = fields.Many2one(
        'uni.student', string='Student', required=True,
        ondelete='cascade', tracking=True, index=True)
    student_name = fields.Char(
        related='student_id.name', string='Student Name',
        store=True, readonly=True)
    student_code = fields.Char(
        related='student_id.student_code', string='Student Code',
        store=True, readonly=True)

    opportunity_id = fields.Many2one(
        'uni.internship.opportunity', string='Opportunity',
        required=True, ondelete='restrict', tracking=True, index=True)
    entity_id = fields.Many2one(
        'uni.internship.training.entity',
        related='opportunity_id.entity_id',
        string='Training Entity', store=True, readonly=True)

    university_id = fields.Many2one(
        'uni.university', related='student_id.university_id',
        string='University', store=True, readonly=True)
    college_id = fields.Many2one(
        'uni.college', related='student_id.college_id',
        string='College', store=True, readonly=True)
    department_id = fields.Many2one(
        'uni.department', related='student_id.department_id',
        string='Department', store=True, readonly=True)

    application_date = fields.Date(
        string='Application Date', default=fields.Date.context_today,
        required=True, tracking=True)

    preferred_start_date = fields.Date(
        string='Preferred Start Date', tracking=True)

    cv_file = fields.Binary(string='CV/Resume')
    cv_filename = fields.Char(string='CV Filename')
    cover_letter = fields.Text(string='Cover Letter')
    additional_documents = fields.Binary(string='Additional Documents')
    additional_documents_filename = fields.Char(
        string='Documents Filename')

    student_statement = fields.Text(
        string='Student Statement',
        help='Why the student is interested in this opportunity.')

    status = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('interview_scheduled', 'Interview Scheduled'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
    ], string='Status', default='draft', tracking=True,
        group_expand='_group_expand_states')

    reviewed_by = fields.Many2one(
        'res.users', string='Reviewed By', readonly=True, tracking=True)
    reviewed_date = fields.Datetime(
        string='Reviewed Date', readonly=True, tracking=True)
    review_comments = fields.Text(string='Review Comments')

    rejection_reason = fields.Text(string='Rejection Reason')

    interview_ids = fields.One2many(
        'uni.internship.application.interview', 'application_id',
        string='Interviews')

    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_application_reference', 'unique(name)',
         'Application reference must be unique!'),
        ('unique_student_opportunity', 'unique(student_id, opportunity_id)',
         'Student can only apply once per opportunity!'),
    ]

    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in states]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.internship.application') or _('New')
        return super().create(vals_list)

    def action_submit(self):
        for rec in self:
            rec.status = 'submitted'

    def action_review(self):
        for rec in self:
            rec.write({
                'status': 'under_review',
                'reviewed_by': self.env.uid,
                'reviewed_date': fields.Datetime.now(),
            })

    def action_schedule_interview(self):
        for rec in self:
            rec.status = 'interview_scheduled'

    def action_accept(self):
        for rec in self:
            rec.status = 'accepted'

    def action_reject(self):
        for rec in self:
            rec.status = 'rejected'

    def action_withdraw(self):
        for rec in self:
            rec.status = 'withdrawn'

    def action_draft(self):
        for rec in self:
            rec.status = 'draft'
