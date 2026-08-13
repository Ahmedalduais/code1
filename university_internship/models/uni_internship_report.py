from odoo import api, fields, models, _


class UniInternshipReport(models.Model):
    _name = 'uni.internship.report'
    _description = 'Internship Report'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'submission_date desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True,
                       default=lambda self: _('New'), index=True)
    internship_id = fields.Many2one('uni.internship', string='Internship', required=True,
                                     ondelete='cascade', tracking=True, index=True)
    student_id = fields.Many2one('uni.student', string='Student', required=True,
                                  ondelete='restrict', tracking=True, index=True)
    student_name = fields.Char(related='student_id.name', string='Student Name',
                                store=True, readonly=True)

    report_type = fields.Selection([
        ('weekly', 'Weekly Report'),
        ('monthly', 'Monthly Report'),
        ('midterm', 'Midterm Report'),
        ('final', 'Final Report'),
        ('special', 'Special Report'),
    ], string='Report Type', default='final', required=True, tracking=True)

    title = fields.Char(string='Report Title', required=True, tracking=True)
    content = fields.Html(string='Report Content', required=True)
    summary = fields.Text(string='Executive Summary')

    submission_date = fields.Datetime(string='Submission Date', default=fields.Datetime.now, tracking=True)

    file = fields.Binary(string='Report File')
    filename = fields.Char(string='Filename')

    supervisor_feedback = fields.Text(string='Supervisor Feedback')
    supervisor_id = fields.Many2one('uni.internship.supervisor', string='Supervisor',
                                     ondelete='set null')

    grade = fields.Float(string='Grade', digits=(5, 2), tracking=True)
    max_grade = fields.Float(string='Max Grade', digits=(5, 2), default=100.0)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('revised', 'Needs Revision'),
    ], string='Status', default='draft', tracking=True, group_expand='_group_expand_states')

    reviewed_by = fields.Many2one('res.users', string='Reviewed By', readonly=True)
    reviewed_date = fields.Datetime(string='Reviewed Date', readonly=True)

    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_report_reference', 'unique(name)', 'Report reference must be unique!'),
    ]

    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in states]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('uni.internship.report') or _('New')
        return super().create(vals_list)

    def action_submit(self):
        for rec in self:
            rec.state = 'submitted'

    def action_review(self):
        for rec in self:
            rec.write({'state': 'under_review', 'reviewed_by': self.env.uid,
                       'reviewed_date': fields.Datetime.now()})

    def action_approve(self):
        for rec in self:
            rec.state = 'approved'

    def action_reject(self):
        for rec in self:
            rec.state = 'rejected'

    def action_revise(self):
        for rec in self:
            rec.state = 'revised'

    def action_draft(self):
        for rec in self:
            rec.state = 'draft'
