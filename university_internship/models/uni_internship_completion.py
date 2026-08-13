from odoo import api, fields, models, _


class UniInternshipCompletion(models.Model):
    _name = 'uni.internship.completion'
    _description = 'Internship Completion'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'completion_date desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True,
                       default=lambda self: _('New'), index=True)
    internship_id = fields.Many2one('uni.internship', string='Internship', required=True,
                                     ondelete='cascade', tracking=True, index=True)
    student_id = fields.Many2one('uni.student', string='Student', required=True,
                                  ondelete='restrict', tracking=True, index=True)
    student_name = fields.Char(related='student_id.name', string='Student Name',
                                store=True, readonly=True)

    completion_date = fields.Date(string='Completion Date', default=fields.Date.context_today,
                                   required=True, tracking=True)

    hours_completed = fields.Float(string='Hours Completed', digits=(5, 2), tracking=True)
    hours_required = fields.Float(string='Hours Required', digits=(5, 2), tracking=True)
    completion_percentage = fields.Float(compute='_compute_percentage', string='Completion %', store=True)

    final_grade = fields.Float(string='Final Grade', digits=(5, 2), tracking=True)
    max_grade = fields.Float(string='Max Grade', digits=(5, 2), default=100.0)
    grade_percentage = fields.Float(compute='_compute_percentage', string='Grade %', store=True)
    grade_letter = fields.Char(string='Grade Letter', tracking=True)

    status = fields.Selection([
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
    ], string='Status', default='pending', tracking=True, group_expand='_group_expand_states')

    approved_by = fields.Many2one('res.users', string='Approved By', readonly=True, tracking=True)
    approved_date = fields.Date(string='Approved Date', readonly=True, tracking=True)

    certificate_issued = fields.Boolean(string='Certificate Issued', default=False, tracking=True)
    certificate_id = fields.Many2one('uni.internship.certificate', string='Certificate', readonly=True)

    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_completion_reference', 'unique(name)', 'Completion reference must be unique!'),
    ]

    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in states]

    @api.depends('hours_completed', 'hours_required', 'final_grade', 'max_grade')
    def _compute_percentage(self):
        for rec in self:
            if rec.hours_required > 0:
                rec.completion_percentage = (rec.hours_completed / rec.hours_required) * 100
            else:
                rec.completion_percentage = 0.0
            if rec.max_grade > 0:
                rec.grade_percentage = (rec.final_grade / rec.max_grade) * 100
            else:
                rec.grade_percentage = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('uni.internship.completion') or _('New')
        return super().create(vals_list)

    def action_approve(self):
        for rec in self:
            rec.write({'status': 'approved', 'approved_by': self.env.uid,
                       'approved_date': fields.Date.context_today(self)})

    def action_reject(self):
        for rec in self:
            rec.status = 'rejected'

    def action_complete(self):
        for rec in self:
            rec.status = 'completed'

    def action_pending(self):
        for rec in self:
            rec.status = 'pending'
