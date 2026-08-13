# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniPortalStudent(models.Model):
    """بوابة الطالب — حساب الوصول إلى البوابة الإلكترونية للطالب.

    يربط هذا النموذج سجل الطالب (``uni.student``) بحساب مستخدم Odoo
    (``res.users``) يُستخدم للدخول إلى البوابة. يدعم النموذج دورة حياة
    كاملة: ``pending`` (بانتظار التفعيل) → ``active`` (مفعّل) ↔ ``blocked``
    (محظور)، مع تتبّع آخر دخول وآخر عنوان IP وإحصائيات الاستخدام.
    """
    _name = 'uni.portal.student'
    _description = 'Student Portal Account'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'registration_date desc, student_id'

    # ------------------------------------------------------------------
    # Identity & links
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Reference', compute='_compute_name', store=True, index=True,
        help='Auto-generated reference combining student code and name.')
    student_id = fields.Many2one(
        'uni.student', string='Student', required=True,
        ondelete='restrict', auto_join=True, index=True, tracking=True,
        help='The student record this portal account is created for.')
    user_id = fields.Many2one(
        'res.users', string='Student User',
        related='student_id.user_id', store=False,
        help='User linked to the student record (via uni.person).')
    portal_user_id = fields.Many2one(
        'res.users', string='Portal Login User',
        ondelete='restrict', index=True, tracking=True,
        help='Odoo user account used to log in to the student portal. '
             'Defaults to the student\'s own user but can be overridden.')
    university_id = fields.Many2one(
        'uni.university', string='University',
        related='student_id.university_id', store=False)
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
        'uni.portal.notification', 'portal_student_id', string='Notifications')
    notification_count = fields.Integer(
        string='Notifications', compute='_compute_notification_count')
    unread_notification_count = fields.Integer(
        string='Unread', compute='_compute_notification_count')
    access_count = fields.Integer(
        string='Portal Accesses', compute='_compute_stats',
        help='Total number of dashboard accesses by this portal user.')
    notes = fields.Text(string='Notes')

    # ------------------------------------------------------------------
    # SQL constraints
    # ------------------------------------------------------------------
    _sql_constraints = [
        ('unique_student_id', 'unique(student_id)',
         'A portal account already exists for this student!'),
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
    @api.depends('student_id', 'student_id.name', 'student_id.student_code')
    def _compute_name(self):
        for rec in self:
            parts = []
            if rec.student_id:
                if rec.student_id.student_code:
                    parts.append(rec.student_id.student_code)
                if rec.student_id.name:
                    parts.append(rec.student_id.name)
            rec.name = ' — '.join(parts) or _('New Student Portal')

    @api.depends('notification_ids.is_read')
    def _compute_notification_count(self):
        for rec in self:
            rec.notification_count = len(rec.notification_ids)
            rec.unread_notification_count = len(
                rec.notification_ids.filtered(lambda n: not n.is_read))

    @api.depends('portal_user_id', 'user_id')
    def _compute_stats(self):
        """Count dashboard accesses as a proxy for portal usage."""
        Dashboard = self.env['uni.portal.dashboard'].sudo()
        for rec in self:
            user = rec.portal_user_id or rec.user_id
            if user:
                dashboards = Dashboard.search([('user_id', '=', user.id)])
                rec.access_count = sum(dashboards.mapped('access_count'))
            else:
                rec.access_count = 0

    # ------------------------------------------------------------------
    # Onchange
    # ------------------------------------------------------------------
    @api.onchange('student_id')
    def _onchange_student_id(self):
        """Default portal_user_id to the student's own user."""
        if self.student_id and not self.portal_user_id:
            self.portal_user_id = self.student_id.user_id

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
                    "Portal user %s is already linked to another student portal.")
                    % rec.portal_user_id.display_name)

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_activate(self):
        """Activate a pending or blocked student portal account."""
        for rec in self:
            if not rec.portal_user_id and not rec.user_id:
                raise ValidationError(_(
                    "Cannot activate portal account %s: no user linked.")
                    % rec.display_name)
            rec.state = 'active'
            rec.message_post(body=_('Student portal account activated.'))

    def action_block(self):
        """Block an active student portal account."""
        for rec in self:
            rec.state = 'blocked'
            rec.message_post(body=_('Student portal account blocked.'))

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
            'domain': [('portal_student_id', '=', self.id)],
            'context': {
                'default_portal_student_id': self.id,
                'default_student_id': self.student_id.id,
                'default_recipient_type': 'student',
            },
        }
