# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniAlumniNetwork(models.Model):
    """شبكة الخريجين المهنية — مجموعة خريجين منظمة.

    تنشأ الشبكات حسب الصناعة أو المنطقة أو التخصص الأكاديمي أو
    الاهتمام المشترك. لكل شبكة منسّق وأعضاء وتواريخ اجتماعات
    منتظمة. تمر بدورة حياة بسيطة: مسودة → نشطة → غير نشطة → مغلقة.
    """
    _name = 'uni.alumni.network'
    _description = 'Alumni Network'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Name', required=True, tracking=True, index=True)
    code = fields.Char(
        string='Code', copy=False, index=True, tracking=True,
        help='Unique code identifying the network.')
    description = fields.Text(string='Description')

    network_type = fields.Selection([
        ('industry', 'Industry'),
        ('regional', 'Regional'),
        ('academic', 'Academic'),
        ('professional', 'Professional'),
        ('special_interest', 'Special Interest'),
    ], string='Network Type', default='professional', tracking=True, index=True)

    # ------------------------------------------------------------------
    # Scope
    # ------------------------------------------------------------------
    industry = fields.Char(string='Industry', tracking=True)
    country_id = fields.Many2one(
        'res.country', string='Country', tracking=True, index=True)
    region = fields.Char(string='Region', tracking=True,
                         help='Free-text region (state, province, city area...).')

    # ------------------------------------------------------------------
    # Coordinator & members
    # ------------------------------------------------------------------
    coordinator_id = fields.Many2one(
        'uni.alumni.member', string='Coordinator',
        ondelete='restrict', tracking=True, index=True,
        help='Alumni member who coordinates the network.')
    member_ids = fields.Many2many(
        'uni.alumni.member', 'uni_alumni_network_member_rel',
        'network_id', 'member_id', string='Members')
    member_count = fields.Integer(
        string='Member Count', compute='_compute_member_count', store=True,
        help='Total number of alumni members in the network.')

    # ------------------------------------------------------------------
    # Schedule
    # ------------------------------------------------------------------
    established_date = fields.Date(
        string='Established Date', tracking=True,
        help='Date the network was officially established.')
    meeting_frequency = fields.Selection([
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annual', 'Annual'),
        ('irregular', 'Irregular'),
    ], string='Meeting Frequency', default='quarterly', tracking=True)
    next_meeting_date = fields.Datetime(
        string='Next Meeting', tracking=True)

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('closed', 'Closed'),
    ], string='State', default='draft', tracking=True, index=True,
        group_expand='_group_expand_states')

    # ------------------------------------------------------------------
    # Misc
    # ------------------------------------------------------------------
    notes = fields.Text(string='Notes')
    active = fields.Boolean(string='Active', default=True, tracking=True)
    color = fields.Integer(string='Color Index')

    _sql_constraints = [
        ('unique_network_code', 'unique(code)',
         'Network code must be unique!'),
        ('unique_network_name', 'unique(name)',
         'Network name must be unique!'),
    ]

    # ------------------------------------------------------------------
    # Group expansion
    # ------------------------------------------------------------------
    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in self._fields['state'].selection]

    # ------------------------------------------------------------------
    # Computed
    # ------------------------------------------------------------------
    @api.depends('member_ids')
    def _compute_member_count(self):
        """Count members in the network."""
        for rec in self:
            rec.member_count = len(rec.member_ids)

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_activate(self):
        """Activate the network."""
        for rec in self:
            if rec.state not in ('draft', 'inactive'):
                raise ValidationError(_(
                    "Only draft or inactive networks can be activated "
                    "(current: %(s)s for %(n)s).") % {
                    's': rec.state, 'n': rec.display_name})
            rec.state = 'active'
            rec.message_post(body=_(
                "Network activated with %(n)s members.") % {
                'n': rec.member_count})

    def action_deactivate(self):
        """Deactivate the network (temporary)."""
        for rec in self:
            if rec.state != 'active':
                raise ValidationError(_(
                    "Only active networks can be deactivated "
                    "(current: %(s)s for %(n)s).") % {
                    's': rec.state, 'n': rec.display_name})
            rec.state = 'inactive'
            rec.message_post(body=_("Network deactivated."))

    def action_close(self):
        """Permanently close the network."""
        for rec in self:
            if rec.state in ('closed',):
                raise ValidationError(_(
                    "Network is already closed (%s).") % rec.display_name)
            rec.state = 'closed'
            rec.message_post(body=_("Network permanently closed."))

    def action_reset_to_draft(self):
        """Reset a closed/inactive network back to draft."""
        for rec in self:
            if rec.state not in ('closed', 'inactive'):
                raise ValidationError(_(
                    "Only closed or inactive networks can be reset to draft "
                    "(current: %(s)s for %(n)s).") % {
                    's': rec.state, 'n': rec.display_name})
            rec.state = 'draft'
            rec.message_post(body=_("Network reset to draft."))

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('coordinator_id', 'member_ids')
    def _check_coordinator_is_member(self):
        """The coordinator (if set) must be a member of the network."""
        for rec in self:
            if rec.coordinator_id and rec.coordinator_id not in rec.member_ids:
                raise ValidationError(_(
                    "Coordinator %(c)s must be a member of the network "
                    "%(n)s.") % {
                    'c': rec.coordinator_id.display_name,
                    'n': rec.display_name,
                })
