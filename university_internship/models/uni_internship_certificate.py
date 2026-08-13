import uuid

from odoo import api, fields, models, _


class UniInternshipCertificate(models.Model):
    _name = 'uni.internship.certificate'
    _description = 'Internship Certificate'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'issue_date desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True,
                       default=lambda self: _('New'), index=True)
    certificate_number = fields.Char(string='Certificate Number', required=True, copy=False,
                                      readonly=True, index=True)

    student_id = fields.Many2one('uni.student', string='Student', required=True,
                                  ondelete='restrict', tracking=True, index=True)
    student_name = fields.Char(related='student_id.name', string='Student Name',
                                store=True, readonly=True)

    internship_id = fields.Many2one('uni.internship', string='Internship', required=True,
                                     ondelete='cascade', tracking=True, index=True)
    completion_id = fields.Many2one('uni.internship.completion', string='Completion Record',
                                     ondelete='set null')

    training_entity_id = fields.Many2one('uni.internship.training.entity', string='Training Entity',
                                          ondelete='restrict', tracking=True)

    issue_date = fields.Date(string='Issue Date', default=fields.Date.context_today,
                              required=True, tracking=True)
    expiry_date = fields.Date(string='Expiry Date', tracking=True)

    grade = fields.Selection([
        ('excellent', 'Excellent'),
        ('very_good', 'Very Good'),
        ('good', 'Good'),
        ('pass', 'Pass'),
        ('fail', 'Fail'),
    ], string='Grade', tracking=True)

    grade_percentage = fields.Float(string='Grade %', digits=(5, 2), tracking=True)

    hours_completed = fields.Float(string='Hours Completed', digits=(5, 2), tracking=True)

    description = fields.Text(string='Certificate Description')

    signature_ids = fields.Many2many('res.users', string='Signatures',
                                      help='Users who signed the certificate.')
    entity_signature_id = fields.Many2one('uni.internship.entity.supervisor',
                                           string='Entity Signature')

    certificate_file = fields.Binary(string='Certificate File (PDF)')
    certificate_filename = fields.Char(string='Certificate Filename')

    is_verified = fields.Boolean(string='Verified', default=False, tracking=True)
    verification_code = fields.Char(string='Verification Code', readonly=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('issued', 'Issued'),
        ('verified', 'Verified'),
        ('revoked', 'Revoked'),
    ], string='Status', default='draft', tracking=True, group_expand='_group_expand_states')

    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_certificate_reference', 'unique(name)', 'Certificate reference must be unique!'),
        ('unique_certificate_number', 'unique(certificate_number)',
         'Certificate number must be unique!'),
    ]

    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in states]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('uni.internship.certificate') or _('New')
            if not vals.get('certificate_number'):
                vals['certificate_number'] = self.env['ir.sequence'].next_by_code('uni.internship.certificate') or _('New')
            if not vals.get('verification_code'):
                vals['verification_code'] = str(uuid.uuid4())[:8].upper()
        return super().create(vals_list)

    def action_issue(self):
        for rec in self:
            rec.state = 'issued'

    def action_verify(self):
        for rec in self:
            rec.write({'state': 'verified', 'is_verified': True})

    def action_revoke(self):
        for rec in self:
            rec.state = 'revoked'

    def action_draft(self):
        for rec in self:
            rec.state = 'draft'
