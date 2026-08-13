from odoo import api, fields, models, _


class UniInternshipWeeklyReport(models.Model):
    _name = 'uni.internship.weekly.report'
    _description = 'Weekly Report'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'week_number desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True,
                       default=lambda self: _('New'), index=True)
    internship_id = fields.Many2one('uni.internship', string='Internship', required=True,
                                     ondelete='cascade', tracking=True, index=True)
    student_id = fields.Many2one('uni.student', string='Student', required=True,
                                  ondelete='restrict', tracking=True, index=True)
    student_name = fields.Char(related='student_id.name', string='Student Name',
                                store=True, readonly=True)

    week_number = fields.Integer(string='Week Number', required=True, tracking=True)
    start_date = fields.Date(string='Week Start Date', required=True, tracking=True)
    end_date = fields.Date(string='Week End Date', required=True, tracking=True)

    total_hours = fields.Float(string='Total Hours', digits=(5, 2), tracking=True)
    days_present = fields.Integer(string='Days Present', default=5)
    days_absent = fields.Integer(string='Days Absent', default=0)

    activities = fields.Text(string='Activities This Week')
    achievements = fields.Text(string='Achievements')
    challenges = fields.Text(string='Challenges Faced')
    next_week_plan = fields.Text(string='Next Week Plan')

    supervisor_feedback = fields.Text(string='Supervisor Feedback')
    supervisor_id = fields.Many2one('uni.internship.supervisor', string='Supervisor',
                                     ondelete='set null')

    is_submitted = fields.Boolean(string='Submitted', default=False, tracking=True)
    is_reviewed = fields.Boolean(string='Reviewed', default=False, tracking=True)
    reviewed_by = fields.Many2one('res.users', string='Reviewed By', readonly=True)
    reviewed_date = fields.Datetime(string='Reviewed Date', readonly=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('reviewed', 'Reviewed'),
        ('revised', 'Needs Revision'),
    ], string='Status', default='draft', tracking=True, group_expand='_group_expand_states')

    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_weekly_report_reference', 'unique(name)', 'Weekly report reference must be unique!'),
        ('unique_weekly_report_per_week', 'unique(student_id, week_number, start_date)',
         'Only one weekly report per student per week!'),
        ('check_dates', 'check(end_date >= start_date)', 'End date must be after start date!'),
    ]

    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in states]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('uni.internship.weekly.report') or _('New')
        return super().create(vals_list)

    def action_submit(self):
        for rec in self:
            rec.write({'state': 'submitted', 'is_submitted': True})

    def action_review(self):
        for rec in self:
            rec.write({'state': 'reviewed', 'is_reviewed': True,
                       'reviewed_by': self.env.uid, 'reviewed_date': fields.Datetime.now()})

    def action_revise(self):
        for rec in self:
            rec.state = 'revised'

    def action_draft(self):
        for rec in self:
            rec.state = 'draft'
