# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class UniAcademicStanding(models.Model):
    """Academic Standing Policy — manages probation, warning, dismissal, honors
    thresholds configurable per university.

    Provides a helper to look up the appropriate standing for a given GPA.
    """
    _name = 'uni.academic.standing'
    _description = 'Academic Standing Policy'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'university_id, sequence'

    name = fields.Char(string='Standing Name', required=True, tracking=True, translate=True)
    code = fields.Char(string='Code', required=True, copy=False, index=True)
    university_id = fields.Many2one('uni.university', string='University',
                                    required=True, ondelete='restrict',
                                    tracking=True, index=True)
    sequence = fields.Integer(string='Sequence', default=10)

    standing_type = fields.Selection([
        ('excellent', 'Excellent'),
        ('very_good', 'Very Good'),
        ('good', 'Good'),
        ('acceptable', 'Acceptable'),
        ('probation', 'Academic Probation'),
        ('warning', 'Academic Warning'),
        ('dismissal', 'Academic Dismissal'),
        ('honors', 'Honors'),
    ], string='Standing Type', required=True, tracking=True)

    min_gpa = fields.Float(string='Minimum GPA', digits=(4, 2), tracking=True,
                           help='Minimum GPA to qualify for this standing.')
    max_gpa = fields.Float(string='Maximum GPA', digits=(4, 2), tracking=True,
                           help='Maximum GPA for this standing (leave 0 for no upper limit).')
    min_credits = fields.Integer(string='Minimum Credits', default=0,
                                  help='Minimum credits attempted to evaluate standing.')

    is_warning = fields.Boolean(string='Is Warning Status', compute='_compute_flags', store=True)
    is_probation = fields.Boolean(string='Is Probation Status', compute='_compute_flags', store=True)
    is_dismissed = fields.Boolean(string='Is Dismissal Status', compute='_compute_flags', store=True)
    is_honors = fields.Boolean(string='Is Honors Status', compute='_compute_flags', store=True)
    is_negative = fields.Boolean(string='Is Negative Standing', compute='_compute_flags', store=True,
                                  help='True if this is a warning/probation/dismissal standing.')

    requires_action = fields.Boolean(string='Requires Action', default=False,
                                      help='If True, student needs to take corrective action.')
    action_description = fields.Text(string='Required Action Description')
    notification_message = fields.Text(string='Notification Message',
                                        help='Message sent to student when this standing is assigned.')

    color = fields.Integer(string='Color Index', default=0)
    description = fields.Text(string='Description')
    active = fields.Boolean(default=True, tracking=True)

    _sql_constraints = [
        ('unique_standing_code', 'unique(code)',
         'Academic standing code must be unique!'),
        ('unique_standing_per_university_type',
         'unique(university_id, standing_type)',
         'Only one standing of each type per university!'),
    ]

    @api.depends('standing_type')
    def _compute_flags(self):
        for rec in self:
            rec.is_warning = rec.standing_type == 'warning'
            rec.is_probation = rec.standing_type == 'probation'
            rec.is_dismissed = rec.standing_type == 'dismissal'
            rec.is_honors = rec.standing_type == 'honors'
            rec.is_negative = rec.standing_type in ('warning', 'probation', 'dismissal')

    @api.model
    def get_standing_for_gpa(self, university_id, gpa, credits_attempted=0):
        """Return the appropriate standing record for a given GPA.

        :param int university_id: ID of the university
        :param float gpa: GPA value to evaluate
        :param int credits_attempted: credits attempted by the student
        :return: uni.academic.standing recordset (may be empty)
        """
        domain = [
            ('university_id', '=', university_id),
            ('min_gpa', '<=', gpa),
            ('active', '=', True),
        ]
        standings = self.search(domain)
        for standing in standings:
            if standing.max_gpa == 0 or gpa <= standing.max_gpa:
                if credits_attempted >= standing.min_credits:
                    return standing
        return self.env['uni.academic.standing']

    def action_send_notification(self):
        """Post a notification message on the chatter for the standing record.

        This is a placeholder action invoked from the form view that simply
        posts the configured notification_message on the standing's own
        chatter, useful for auditing policy updates.
        """
        for rec in self:
            if rec.notification_message:
                rec.message_post(body=rec.notification_message)
        return True
