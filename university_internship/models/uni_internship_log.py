from odoo import api, fields, models, _


class UniInternshipLog(models.Model):
    _name = 'uni.internship.log'
    _description = 'Internship Daily Log'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True,
                       default=lambda self: _('New'), index=True)
    internship_id = fields.Many2one('uni.internship', string='Internship', required=True,
                                     ondelete='cascade', tracking=True, index=True)

    # Student can be linked directly or via team member
    student_id = fields.Many2one('uni.student', string='Student', required=True,
                                  ondelete='restrict', tracking=True, index=True)
    student_name = fields.Char(related='student_id.name', string='Student Name',
                                store=True, readonly=True)

    team_member_id = fields.Many2one('uni.internship.team.member', string='Team Member',
                                      ondelete='set null')

    date = fields.Date(string='Date', required=True, default=fields.Date.context_today, tracking=True)
    hours = fields.Float(string='Hours', digits=(5, 2), required=True, default=8.0, tracking=True)

    activity = fields.Text(string='Activity Description', required=True)
    achievements = fields.Text(string='Achievements')
    challenges = fields.Text(string='Challenges')

    location = fields.Char(string='Location')
    is_remote = fields.Boolean(string='Remote Work', default=False)

    supervisor_approval = fields.Boolean(string='Academic Supervisor Approved', default=False, tracking=True)
    supervisor_approved_by = fields.Many2one('res.users', string='Approved By', readonly=True)
    supervisor_approved_date = fields.Datetime(string='Approved Date', readonly=True)

    entity_supervisor_approval = fields.Boolean(string='Field Supervisor Approved', default=False, tracking=True)
    entity_supervisor_id = fields.Many2one('uni.internship.entity.supervisor', string='Field Supervisor',
                                            ondelete='set null')
    entity_approved_date = fields.Datetime(string='Field Approved Date', readonly=True)

    is_approved = fields.Boolean(compute='_compute_approved', string='Fully Approved', store=True)

    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_log_reference', 'unique(name)', 'Log reference must be unique!'),
        ('check_hours_positive', 'check(hours >= 0)', 'Hours must be positive!'),
    ]

    @api.depends('supervisor_approval', 'entity_supervisor_approval')
    def _compute_approved(self):
        for rec in self:
            rec.is_approved = rec.supervisor_approval and rec.entity_supervisor_approval

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('uni.internship.log') or _('New')
        return super().create(vals_list)

    def action_approve_supervisor(self):
        for rec in self:
            rec.write({'supervisor_approval': True, 'supervisor_approved_by': self.env.uid,
                       'supervisor_approved_date': fields.Datetime.now()})

    def action_approve_entity(self):
        for rec in self:
            rec.write({'entity_supervisor_approval': True, 'entity_approved_date': fields.Datetime.now()})
