# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class UniProjectApproval(models.Model):
    """Project Approval — formal approval / sign-off step in the lifecycle.

    Each approval is tied to either a proposal (``proposal_id``) or a project
    (``project_id``) and tracks the approver, decision, conditions, and the
    date of decision. Multiple approvals may exist per project (initial,
    revision, final, ethics, budget).
    """
    _name = 'uni.project.approval'
    _description = 'Project Approval'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'approval_date desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True,
                       default=lambda self: _('New'), index=True)
    proposal_id = fields.Many2one('uni.project.proposal', string='Proposal',
                                  required=True, ondelete='cascade', tracking=True)
    project_id = fields.Many2one('uni.project', string='Project',
                                 ondelete='cascade', tracking=True)

    approval_type = fields.Selection([
        ('initial', 'Initial Approval'),
        ('revision', 'Revision Approval'),
        ('final', 'Final Approval'),
        ('ethics', 'Ethics Approval'),
        ('budget', 'Budget Approval'),
    ], string='Approval Type', required=True, default='initial', tracking=True)

    approver_id = fields.Many2one('res.users', string='Approver', required=True,
                                  default=lambda self: self.env.user, tracking=True)
    approval_date = fields.Datetime(string='Approval Date',
                                    readonly=True, tracking=True)

    decision = fields.Selection([
        ('approved', 'Approved'),
        ('conditional', 'Conditionally Approved'),
        ('rejected', 'Rejected'),
    ], string='Decision', tracking=True)

    conditions = fields.Text(string='Conditions',
                             help='Conditions for conditional approval')
    comments = fields.Text(string='Comments')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('decided', 'Decided'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True,
        group_expand='_group_expand_states')

    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_approval_reference', 'unique(name)',
         'Approval reference must be unique!'),
    ]

    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in states]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.project.approval') or _('New')
        return super().create(vals_list)

    def action_submit(self):
        for rec in self:
            rec.state = 'submitted'

    def action_decide(self):
        for rec in self:
            rec.write({'state': 'decided',
                       'approval_date': fields.Datetime.now()})

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'

    def action_draft(self):
        for rec in self:
            rec.state = 'draft'
