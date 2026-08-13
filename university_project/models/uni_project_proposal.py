# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class UniProjectProposal(models.Model):
    """Project Proposal — submitted by a team prior to project creation.

    Captures the project idea, team composition (as free-text since the team
    may not yet exist as ``uni.project.team`` records), academic affiliation,
    and the workflow of submission → review → approval/rejection.
    A proposal may optionally be linked to a created ``uni.project`` record
    via ``project_id`` once approved.
    """
    _name = 'uni.project.proposal'
    _description = 'Project Proposal'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'submission_date desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True,
                       default=lambda self: _('New'), index=True)
    title = fields.Char(string='Project Title', required=True, tracking=True)
    project_id = fields.Many2one('uni.project', string='Linked Project',
                                 ondelete='set null', tracking=True)
    theme_id = fields.Many2one('uni.project.theme', string='Theme',
                               ondelete='restrict', tracking=True)

    # Team info (team may not exist yet at proposal stage)
    team_name = fields.Char(string='Team Name', tracking=True)
    team_leader_name = fields.Char(string='Team Leader Name', tracking=True)
    team_leader_code = fields.Char(string='Team Leader Code', tracking=True)
    member_names = fields.Text(string='Team Members',
                               help='List of all team member names')

    university_id = fields.Many2one('uni.university', string='University',
                                    required=True, ondelete='restrict', tracking=True)
    college_id = fields.Many2one('uni.college', string='College',
                                 ondelete='restrict', tracking=True)
    department_id = fields.Many2one('uni.department', string='Department',
                                    ondelete='restrict', tracking=True)
    program_id = fields.Many2one('uni.program', string='Program',
                                 ondelete='restrict', tracking=True)
    academic_term_id = fields.Many2one('uni.academic.term', string='Academic Term',
                                       ondelete='restrict', tracking=True)

    proposal_date = fields.Date(string='Proposal Date',
                                default=fields.Date.context_today, tracking=True)
    submission_date = fields.Datetime(string='Submission Date',
                                      readonly=True, tracking=True)

    abstract = fields.Text(string='Abstract', required=True)
    objectives = fields.Text(string='Objectives', required=True)
    methodology = fields.Text(string='Methodology')
    expected_outcomes = fields.Text(string='Expected Outcomes')
    timeline_summary = fields.Text(string='Timeline Summary')
    budget_estimate = fields.Float(string='Estimated Budget', digits=(12, 2))
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)
    references = fields.Text(string='References')

    proposal_file = fields.Binary(string='Proposal Document')
    proposal_filename = fields.Char(string='Filename')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('revise', 'Needs Revision'),
    ], string='Status', default='draft', tracking=True,
        group_expand='_group_expand_states')

    reviewed_by = fields.Many2one('res.users', string='Reviewed By',
                                  readonly=True, tracking=True)
    reviewed_date = fields.Datetime(string='Reviewed Date', readonly=True)
    review_comments = fields.Text(string='Review Comments')
    approved_by = fields.Many2one('res.users', string='Approved By',
                                  readonly=True, tracking=True)
    approved_date = fields.Datetime(string='Approved Date', readonly=True)

    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_proposal_reference', 'unique(name)',
         'Proposal reference must be unique!'),
    ]

    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in states]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.project.proposal') or _('New')
        return super().create(vals_list)

    def action_submit(self):
        for rec in self:
            rec.write({'state': 'submitted',
                       'submission_date': fields.Datetime.now()})

    def action_start_review(self):
        for rec in self:
            rec.write({'state': 'under_review',
                       'reviewed_by': self.env.uid,
                       'reviewed_date': fields.Datetime.now()})

    def action_approve(self):
        for rec in self:
            rec.write({'state': 'approved',
                       'approved_by': self.env.uid,
                       'approved_date': fields.Datetime.now()})

    def action_reject(self):
        for rec in self:
            rec.state = 'rejected'

    def action_revise(self):
        for rec in self:
            rec.state = 'revise'

    def action_draft(self):
        for rec in self:
            rec.state = 'draft'
