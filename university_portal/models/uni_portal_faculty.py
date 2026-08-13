# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniPortalFaculty(models.Model):
    """بوابة عضو هيئة التدريس — حساب الوصول إلى البوابة الإلكترونية للعضو.

    يربط هذا النموذج سجل عضو هيئة التدريس (``uni.faculty``) بحساب مستخدم
    Odoo (``res.users``) يُستخدم للدخول إلى بوابة أعضاء هيئة التدريس.
    يدعم النموذج دورة حياة كاملة: ``pending`` → ``active`` ↔ ``blocked``.
    """
    _name = 'uni.portal.faculty'
    _description = 'Faculty Portal Account'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'registration_date desc, faculty_id'

    # ------------------------------------------------------------------
    # Identity & links
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Reference', compute='_compute_name', store=True, index=True,
        help='Auto-generated reference combining faculty code and name.')
    faculty_id = fields.Many2one(
        'uni.faculty', string='Faculty Member', required=True,
        ondelete='restrict', auto_join=True, index=True, tracking=True,
        help='The faculty record this portal account is created for.')
    user_id = fields.Many2one(
        'res.users', string='Faculty User',
        related='faculty_id.user_id', store=False,
        help='User linked to the faculty record (via uni.person).')
    portal_user_id = fields.Many2one(
        'res.users', string='Portal Login User',
        ondelete='restrict', index=True, tracking=True,
        help='Odoo user account used to log in to the faculty portal. '
             'Defaults to the faculty member\'s own user but can be overridden.')
    university_id = fields.Many2one(
        'uni.university', string='University',
        related='faculty_id.university_id', store=False)
    last_login = fields.Datetime(string='Last Login', tracking=True)
    registration_date = fields.Datetime(
        string='Registration Date', default=fields.Datetime.now, tracking=True)
    state = fields.Selection([
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('blocked', 'Blocked'),
    ], string='Status', default='pending', tracking=True, index=True,
        group_expand='_group_expand_states')
    last_ip = fields.Char(string='Last IP Address', tracking=True)

    # ------------------------------------------------------------------
    # Relations & stats
    # ------------------------------------------------------------------
    notification_ids = fields.One2many(
        'uni.portal.notification', 'portal_faculty_id', string='Notifications')
    notification_count = fields.Integer(
        string='Notifications', compute='_compute_notification_count')
    unread_notification_count = fields.Integer(
        string='Unread', compute='_compute_notification_count')
    notes = fields.Text(string='Notes')

    # ------------------------------------------------------------------
    # SQL constraints
    # ------------------------------------------------------------------
    _sql_constraints = [
        ('unique_faculty_id', 'unique(faculty_id)',
         'A portal account already exists for this faculty member!'),
    ]

    # ------------------------------------------------------------------
    # Group expansion for state selection
    # ------------------------------------------------------------------
    @api.model
    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in self._fields['state'].selection]

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends('faculty_id', 'faculty_id.name', 'faculty_id.faculty_code')
    def _compute_name(self):
        for rec in self:
            parts = []
            if rec.faculty_id:
                if rec.faculty_id.faculty_code:
                    parts.append(rec.faculty_id.faculty_code)
                if rec.faculty_id.name:
                    parts.append(rec.faculty_id.name)
            rec.name = ' — '.join(parts) or _('New Faculty Portal')

    @api.depends('notification_ids.is_read')
    def _compute_notification_count(self):
        for rec in self:
            rec.notification_count = len(rec.notification_ids)
            rec.unread_notification_count = len(
                rec.notification_ids.filtered(lambda n: not n.is_read))

    # ------------------------------------------------------------------
    # Onchange
    # ------------------------------------------------------------------
    @api.onchange('faculty_id')
    def _onchange_faculty_id(self):
        """Default portal_user_id to the faculty's own user."""
        if self.faculty_id and not self.portal_user_id:
            self.portal_user_id = self.faculty_id.user_id

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('portal_user_id')
    def _check_unique_portal_user(self):
        for rec in self:
            if not rec.portal_user_id:
                continue
            domain = [
                ('portal_user_id', '=', rec.portal_user_id.id),
                ('id', '!=', rec.id),
            ]
            if self.search_count(domain):
                raise ValidationError(_(
                    "Portal user %s is already linked to another faculty portal.")
                    % rec.portal_user_id.display_name)

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_activate(self):
        """Activate a pending or blocked faculty portal account."""
        for rec in self:
            if not rec.portal_user_id and not rec.user_id:
                raise ValidationError(_(
                    "Cannot activate portal account %s: no user linked.")
                    % rec.display_name)
            rec.state = 'active'
            rec.message_post(body=_('Faculty portal account activated.'))

    def action_block(self):
        """Block an active faculty portal account."""
        for rec in self:
            rec.state = 'blocked'
            rec.message_post(body=_('Faculty portal account blocked.'))

    def action_reset_password(self):
        """Trigger a password-reset email for the portal user."""
        for rec in self:
            user = rec.portal_user_id or rec.user_id
            if not user:
                raise ValidationError(_(
                    "No user linked to portal account %s.") % rec.display_name)
            user.sudo().action_reset_password()
            rec.message_post(body=_(
                "Password reset email sent to %s.") % (user.email or user.login))

    # ------------------------------------------------------------------
    # Smart-button
    # ------------------------------------------------------------------
    def action_open_notifications(self):
        self.ensure_one()
        return {
            'name': _('Notifications'),
            'type': 'ir.actions.act_window',
            'res_model': 'uni.portal.notification',
            'view_mode': 'list,form',
            'domain': [('portal_faculty_id', '=', self.id)],
            'context': {
                'default_portal_faculty_id': self.id,
                'default_faculty_id': self.faculty_id.id,
                'default_recipient_type': 'faculty',
            },
        }
