# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class UniGradebookApproval(models.Model):
    """سير عمل اعتماد الدرجات قبل النشر.

    يمر الطلب بمراحل:
        draft → submitted → under_review → approved → published
                                  ↘ rejected
                                  ↘ cancelled
    يدعم أنواعاً متعددة من الطلبات (تقديم، مراجعة، اعتماد نهائي، نشر،
    تعديل) مع تتبّع تواريخ ومسؤولي كل مرحلة، أولوية، وموعد نهائي،
    بالإضافة إلى حساب آلي لحقل "متأخر".
    """
    _name = 'uni.gradebook.approval'
    _description = 'Gradebook Approval Workflow'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'gradebook_id, request_date desc'

    # ------------------------------------------------------------------
    # Identity & linkage
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Approval Reference', required=True, copy=False, readonly=True,
        default=lambda self: _('New'), index=True)
    gradebook_id = fields.Many2one(
        'uni.gradebook', string='Gradebook', required=True,
        ondelete='cascade', tracking=True, index=True)
    course_id = fields.Many2one(
        'uni.course', related='gradebook_id.course_id',
        string='Course', store=True, readonly=True)
    academic_term_id = fields.Many2one(
        'uni.academic.term', related='gradebook_id.academic_term_id',
        string='Term', store=True, readonly=True)

    approval_type = fields.Selection([
        ('submission', 'Grade Submission'),
        ('review', 'Department Review'),
        ('approval', 'Final Approval'),
        ('publication', 'Grade Publication'),
        ('modification', 'Grade Modification'),
    ], string='Approval Type', required=True, tracking=True, default='submission')

    # ------------------------------------------------------------------
    # Request
    # ------------------------------------------------------------------
    request_date = fields.Datetime(
        string='Request Date', default=fields.Datetime.now,
        readonly=True, tracking=True)
    requested_by = fields.Many2one(
        'res.users', string='Requested By', required=True,
        default=lambda self: self.env.user, readonly=True, tracking=True)

    request_comments = fields.Text(string='Request Comments')
    request_data = fields.Text(
        string='Request Data (JSON)',
        help='Snapshot of grades at submission time.')

    # ------------------------------------------------------------------
    # Review
    # ------------------------------------------------------------------
    reviewed_by = fields.Many2one(
        'res.users', string='Reviewed By', readonly=True, tracking=True)
    reviewed_date = fields.Datetime(
        string='Reviewed Date', readonly=True, tracking=True)
    review_comments = fields.Text(string='Review Comments')

    # ------------------------------------------------------------------
    # Approval
    # ------------------------------------------------------------------
    approved_by = fields.Many2one(
        'res.users', string='Approved By', readonly=True, tracking=True)
    approved_date = fields.Datetime(
        string='Approved Date', readonly=True, tracking=True)
    approval_comments = fields.Text(string='Approval Comments')

    # ------------------------------------------------------------------
    # Publication
    # ------------------------------------------------------------------
    published_by = fields.Many2one(
        'res.users', string='Published By', readonly=True, tracking=True)
    published_date = fields.Datetime(
        string='Published Date', readonly=True, tracking=True)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('published', 'Published'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True,
        group_expand='_group_expand_states')

    rejection_reason = fields.Text(string='Rejection Reason')
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'High'),
        ('2', 'Urgent'),
    ], string='Priority', default='0', tracking=True)

    deadline = fields.Datetime(string='Approval Deadline', tracking=True)
    is_overdue = fields.Boolean(
        string='Is Overdue', compute='_compute_overdue', store=True)

    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_approval_reference', 'unique(name)',
         'Approval reference must be unique!'),
    ]

    # ------------------------------------------------------------------
    # Group expansion helper
    # ------------------------------------------------------------------
    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in states]

    # ------------------------------------------------------------------
    # Computed
    # ------------------------------------------------------------------
    @api.depends('deadline', 'state')
    def _compute_overdue(self):
        now = fields.Datetime.now()
        for rec in self:
            rec.is_overdue = (
                rec.deadline and rec.deadline < now
                and rec.state not in ('approved', 'published', 'cancelled')
            )

    # ------------------------------------------------------------------
    # Create — auto-generate reference via ir.sequence
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.gradebook.approval') or _('New')
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_submit(self):
        """Submit for review."""
        for rec in self:
            rec.write({
                'state': 'submitted',
                'request_date': fields.Datetime.now(),
            })
            rec.gradebook_id.message_post(
                body=_('Grade approval request %s submitted by %s') % (
                    rec.name, rec.requested_by.name))

    def action_start_review(self):
        """Start the review process."""
        for rec in self:
            rec.write({
                'state': 'under_review',
                'reviewed_by': self.env.uid,
                'reviewed_date': fields.Datetime.now(),
            })

    def action_approve(self):
        """Approve the request."""
        for rec in self:
            rec.write({
                'state': 'approved',
                'approved_by': self.env.uid,
                'approved_date': fields.Datetime.now(),
            })

    def action_reject(self):
        """Reject the request — opens a wizard to capture reason,
        but for simplicity set state."""
        for rec in self:
            rec.state = 'rejected'

    def action_publish(self):
        """Publish the grades."""
        for rec in self:
            rec.write({
                'state': 'published',
                'published_by': self.env.uid,
                'published_date': fields.Datetime.now(),
            })
            # Lock the gradebook if not already locked
            if rec.gradebook_id.state != 'locked':
                rec.gradebook_id.action_lock()

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'

    def action_reset_to_draft(self):
        for rec in self:
            rec.state = 'draft'
