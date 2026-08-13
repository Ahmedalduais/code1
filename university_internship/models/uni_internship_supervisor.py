# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniInternshipSupervisor(models.Model):
    """Internship Supervisor — a faculty member (or external field
    supervisor) assigned to an internship with a specific role
    (academic / field / co-supervisor / external).

    Each supervisor assignment is uniquely identified by a sequence
    reference, has its own start/end dates and workload, and can be
    deactivated independently from the internship itself.
    """
    _name = 'uni.internship.supervisor'
    _description = 'Internship Supervisor'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'internship_id, sequence'

    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True,
        default=lambda self: _('New'), index=True)
    internship_id = fields.Many2one(
        'uni.internship', string='Internship', required=True,
        ondelete='cascade', tracking=True, index=True)

    faculty_id = fields.Many2one(
        'uni.faculty', string='Faculty Member', required=True,
        ondelete='restrict', tracking=True, index=True)
    faculty_name = fields.Char(
        related='faculty_id.name', string='Faculty Name',
        store=True, readonly=True)

    supervisor_type = fields.Selection([
        ('academic', 'Academic Supervisor'),
        ('field', 'Field Supervisor'),
        ('co_supervisor', 'Co-Supervisor'),
        ('external', 'External Supervisor'),
    ], string='Supervisor Type', default='academic',
        required=True, tracking=True)

    entity_supervisor_id = fields.Many2one(
        'uni.internship.entity.supervisor', string='Field Supervisor',
        ondelete='set null', tracking=True,
        help='Optional link to the matching field supervisor at the '
             'training entity for the field-supervisor type.')

    sequence = fields.Integer(string='Sequence', default=10)
    assignment_date = fields.Date(
        string='Assignment Date', default=fields.Date.context_today,
        tracking=True)
    end_date = fields.Date(string='End Date', tracking=True)
    is_active = fields.Boolean(
        string='Active', default=True, tracking=True)

    workload_hours = fields.Float(
        string='Workload (Hours/Week)', default=3, tracking=True)

    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_supervisor_reference', 'unique(name)',
         'Supervisor reference must be unique!'),
        ('unique_faculty_per_internship',
         'unique(internship_id, faculty_id, supervisor_type)',
         'Faculty can only supervise an internship once per type!'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code(
                        'uni.internship.supervisor') or _('New')
                )
        return super().create(vals_list)

    @api.constrains('end_date', 'assignment_date')
    def _check_dates(self):
        for rec in self:
            if (rec.end_date and rec.assignment_date
                    and rec.end_date < rec.assignment_date):
                raise ValidationError(_(
                    'End date must be after assignment date!'))

    @api.constrains('is_active', 'end_date')
    def _check_active_consistency(self):
        for rec in self:
            if rec.end_date and rec.is_active:
                raise ValidationError(_(
                    'A supervisor with an end date cannot be active!'
                ))

    def action_end_supervision(self):
        for rec in self:
            rec.write({
                'is_active': False,
                'end_date': fields.Date.context_today(self),
            })

    def action_reactivate(self):
        for rec in self:
            rec.write({'is_active': True, 'end_date': False})
