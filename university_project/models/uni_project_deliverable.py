# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniProjectDeliverable(models.Model):
    _name = 'uni.project.deliverable'
    _description = 'Project Deliverable'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'project_id, due_date'

    name = fields.Char(string='Deliverable Name', required=True, tracking=True)
    project_id = fields.Many2one('uni.project', string='Project', required=True,
                                  ondelete='cascade', tracking=True, index=True)

    milestone_id = fields.Many2one('uni.project.milestone', string='Milestone',
                                    ondelete='set null', index=True)

    # Can be linked to a team or individual member
    team_id = fields.Many2one('uni.project.team', string='Team', ondelete='set null', index=True)
    member_id = fields.Many2one('uni.project.team.member', string='Team Member',
                                 ondelete='set null', index=True)

    deliverable_type = fields.Selection([
        ('report', 'Report'),
        ('code', 'Source Code'),
        ('presentation', 'Presentation'),
        ('demo', 'Demo / Prototype'),
        ('dataset', 'Dataset'),
        ('documentation', 'Documentation'),
        ('video', 'Video'),
        ('other', 'Other'),
    ], string='Deliverable Type', default='report', required=True, tracking=True)

    description = fields.Text(string='Description')

    due_date = fields.Date(string='Due Date', required=True, tracking=True)
    submission_date = fields.Date(string='Submission Date', readonly=True, tracking=True)

    file = fields.Binary(string='File')
    filename = fields.Char(string='Filename')
    url = fields.Char(string='External URL')
    version = fields.Char(string='Version', default='1.0', tracking=True)

    is_submitted = fields.Boolean(string='Submitted', compute='_compute_submitted', store=True, tracking=True)
    is_approved = fields.Boolean(string='Approved', default=False, tracking=True)
    approved_by = fields.Many2one('res.users', string='Approved By', readonly=True, tracking=True)
    approved_date = fields.Date(string='Approved Date', readonly=True, tracking=True)

    feedback = fields.Text(string='Feedback')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('revise', 'Needs Revision'),
    ], string='Status', default='draft', tracking=True, group_expand='_group_expand_states')

    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in states]

    @api.depends('submission_date')
    def _compute_submitted(self):
        for rec in self:
            rec.is_submitted = bool(rec.submission_date)

    @api.constrains('due_date')
    def _check_due_date(self):
        for rec in self:
            if rec.due_date and rec.due_date < fields.Date.context_today(self):
                # Just a warning, not an error — late submissions are allowed
                pass

    def action_submit(self):
        for rec in self:
            rec.write({
                'state': 'submitted',
                'submission_date': fields.Date.context_today(self),
            })

    def action_start_review(self):
        for rec in self:
            rec.state = 'under_review'

    def action_approve(self):
        for rec in self:
            rec.write({
                'state': 'approved',
                'is_approved': True,
                'approved_by': self.env.uid,
                'approved_date': fields.Date.context_today(self),
            })

    def action_reject(self):
        for rec in self:
            rec.state = 'rejected'

    def action_revise(self):
        for rec in self:
            rec.state = 'revise'

    def action_draft(self):
        for rec in self:
            rec.state = 'draft'
