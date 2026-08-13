# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class UniHonorsLevel(models.Model):
    """Honor Level — configures honor tiers (Dean's List, President's List,
    graduation honors, etc.) with GPA/credits thresholds per university.
    """
    _name = 'uni.honors.level'
    _description = 'Honor Level'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'university_id, min_gpa desc'

    name = fields.Char(string='Honor Name', required=True, tracking=True, translate=True)
    code = fields.Char(string='Code', required=True, copy=False, index=True)
    university_id = fields.Many2one('uni.university', string='University',
                                    required=True, ondelete='restrict',
                                    tracking=True, index=True)
    sequence = fields.Integer(string='Sequence', default=10)

    level_type = fields.Selection([
        ('deans_list', "Dean's List"),
        ('presidents_list', "President's List"),
        ('graduation_honors', 'Graduation Honors'),
        ('semester_honors', 'Semester Honors'),
        ('distinction', 'Distinction'),
        ('other', 'Other'),
    ], string='Honor Type', required=True, tracking=True)

    min_gpa = fields.Float(string='Minimum GPA', digits=(4, 2), required=True, tracking=True)
    max_gpa = fields.Float(string='Maximum GPA', digits=(4, 2), default=0,
                           help='Maximum GPA (0 = no upper limit).')
    min_credits = fields.Integer(string='Minimum Credits', default=12,
                                  help='Minimum credits in the evaluation period.')
    min_total_credits = fields.Integer(string='Minimum Total Credits', default=0,
                                        help='Minimum total credits for graduation honors.')

    latin_honors = fields.Selection([
        ('none', 'None'),
        ('cum_laude', 'Cum Laude'),
        ('magna_cum_laude', 'Magna Cum Laude'),
        ('summa_cum_laude', 'Summa Cum Laude'),
    ], string='Latin Honors', default='none', tracking=True)

    ceremony_date = fields.Date(string='Ceremony Date', tracking=True)
    recognition_text = fields.Text(string='Recognition Text',
                                    help='Text displayed on transcript/certificate.')
    certificate_template = fields.Char(string='Certificate Template',
                                        help='Reference to certificate template.')

    color = fields.Integer(string='Color Index', default=0)
    description = fields.Text(string='Description')
    active = fields.Boolean(default=True, tracking=True)

    _sql_constraints = [
        ('unique_honors_code', 'unique(code)',
         'Honor level code must be unique!'),
        ('check_min_gpa_positive', 'check(min_gpa >= 0)',
         'Minimum GPA must be positive!'),
    ]

    @api.model
    def get_honor_for_gpa(self, university_id, gpa, credits=0, total_credits=0, level_type=False):
        """Return the appropriate honor level for a given GPA.

        :param int university_id: ID of the university
        :param float gpa: GPA value to evaluate
        :param int credits: credits in the evaluation period
        :param int total_credits: total credits accumulated (for graduation honors)
        :param str level_type: optional level_type to filter on
        :return: uni.honors.level recordset (may be empty)
        """
        domain = [
            ('university_id', '=', university_id),
            ('min_gpa', '<=', gpa),
            ('active', '=', True),
        ]
        if level_type:
            domain.append(('level_type', '=', level_type))
        honors = self.search(domain, order='min_gpa desc')
        for honor in honors:
            if honor.max_gpa == 0 or gpa <= honor.max_gpa:
                if credits >= honor.min_credits and total_credits >= honor.min_total_credits:
                    return honor
        return self.env['uni.honors.level']

    def action_recognize(self):
        """Post the recognition text on the chatter for audit purposes."""
        for rec in self:
            body = rec.recognition_text or _('Honor level recognized: %s') % rec.display_name
            rec.message_post(body=body)
        return True
