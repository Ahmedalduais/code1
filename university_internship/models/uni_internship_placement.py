from odoo import api, fields, models, _


class UniInternshipPlacement(models.Model):
    _name = 'uni.internship.placement'
    _description = 'Student Placement'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'placement_date desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True,
                       default=lambda self: _('New'), index=True)
    student_id = fields.Many2one('uni.student', string='Student', required=True,
                                  ondelete='cascade', tracking=True, index=True)
    student_name = fields.Char(related='student_id.name', string='Student Name',
                                store=True, readonly=True)

    opportunity_id = fields.Many2one('uni.internship.opportunity', string='Opportunity',
                                      ondelete='set null', tracking=True)
    application_id = fields.Many2one('uni.internship.application', string='Application',
                                      ondelete='set null', tracking=True)
    internship_id = fields.Many2one('uni.internship', string='Internship Record',
                                     ondelete='set null', tracking=True)

    training_entity_id = fields.Many2one('uni.internship.training.entity', string='Training Entity',
                                          required=True, ondelete='restrict', tracking=True, index=True)

    placement_date = fields.Date(string='Placement Date', default=fields.Date.context_today,
                                  required=True, tracking=True)
    start_date = fields.Date(string='Start Date', tracking=True)
    end_date = fields.Date(string='End Date', tracking=True)

    position = fields.Char(string='Position/Role', tracking=True)
    department = fields.Char(string='Department in Entity', tracking=True)

    is_confirmed = fields.Boolean(string='Confirmed', default=False, tracking=True)
    confirmed_by = fields.Many2one('res.users', string='Confirmed By', readonly=True)
    confirmed_date = fields.Date(string='Confirmed Date', readonly=True)

    status = fields.Selection([
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
        ('completed', 'Completed'),
    ], string='Status', default='pending', tracking=True, group_expand='_group_expand_states')

    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_placement_reference', 'unique(name)', 'Placement reference must be unique!'),
    ]

    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in states]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('uni.internship.placement') or _('New')
        return super().create(vals_list)

    def action_confirm(self):
        for rec in self:
            rec.write({'status': 'confirmed', 'is_confirmed': True,
                       'confirmed_by': self.env.uid, 'confirmed_date': fields.Date.context_today(self)})

    def action_reject(self):
        for rec in self:
            rec.status = 'rejected'

    def action_withdraw(self):
        for rec in self:
            rec.status = 'withdrawn'

    def action_complete(self):
        for rec in self:
            rec.status = 'completed'

    def action_pending(self):
        for rec in self:
            rec.status = 'pending'
