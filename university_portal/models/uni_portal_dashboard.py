# -*- coding: utf-8 -*-
import json

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniPortalDashboard(models.Model):
    """لوحة المعلومات — لوحة قابلة للتخصيص لكل مستخدم على البوابة.

    يخزّن هذا النموذج إعدادات لوحة المعلومات الخاصة بكل مستخدم، بما في ذلك
    نوع اللوحة (طالب/عضو تدريس/مشرف)، إعدادات الودجات (JSON)، وحالة آخر
    وصول وعدد مرات الوصول. يدعم النموذج إعادة الضبط للافتراضي واسترجاع
    البيانات الكاملة للوحة عبر ``get_dashboard_data()``.
    """
    _name = 'uni.portal.dashboard'
    _description = 'Portal Dashboard'
    _inherit = ['mail.thread', 'uni.mixin.archivable']
    _order = 'user_id, is_default desc, last_accessed desc'

    # ------------------------------------------------------------------
    # Fields
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Name', required=True, translate=True, tracking=True,
        help='Human-readable name for this dashboard.')
    user_id = fields.Many2one(
        'res.users', string='User', required=True,
        ondelete='cascade', index=True, tracking=True,
        help='The Odoo user this dashboard belongs to.')
    student_id = fields.Many2one(
        'uni.student', string='Student', ondelete='set null',
        help='Optional student reference if the dashboard is for a student.')
    faculty_id = fields.Many2one(
        'uni.faculty', string='Faculty Member', ondelete='set null',
        help='Optional faculty reference if the dashboard is for a faculty member.')
    dashboard_type = fields.Selection([
        ('student', 'Student'),
        ('faculty', 'Faculty'),
        ('admin', 'Admin'),
    ], string='Dashboard Type', default='student', required=True, index=True,
        tracking=True)
    configuration = fields.Text(
        string='Configuration',
        help='JSON configuration of dashboard widgets (layout, theme, widgets).')
    is_default = fields.Boolean(
        string='Default', default=False, copy=False, tracking=True,
        help='Mark this dashboard as the default for the user and type.')
    last_accessed = fields.Datetime(
        string='Last Accessed', readonly=True, copy=False)
    access_count = fields.Integer(
        string='Access Count', default=0, copy=False,
        help='Number of times this dashboard has been accessed.')

    # ------------------------------------------------------------------
    # SQL constraints
    # ------------------------------------------------------------------
    # NOTE: a unique(user_id, dashboard_type, is_default) SQL constraint
    # would prevent having multiple non-default dashboards of the same type
    # for the same user (because False == False). We enforce the "at most
    # one default per user/type" rule via ``_check_single_default`` instead.
    _sql_constraints = []

    # ------------------------------------------------------------------
    # Defaults
    # ------------------------------------------------------------------
    @api.model
    def _get_default_configuration(self):
        """Return the default JSON configuration for a dashboard."""
        config = {
            'widgets': [
                {'key': 'profile', 'type': 'profile',
                 'position': 'top', 'visible': True, 'collapsed': False},
                {'key': 'notifications', 'type': 'notifications',
                 'position': 'right', 'visible': True, 'limit': 5,
                 'collapsed': False},
                {'key': 'quick_links', 'type': 'quick_links',
                 'position': 'bottom', 'visible': True, 'collapsed': False},
            ],
            'theme': 'default',
            'layout': 'two_column',
        }
        return json.dumps(config, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Create — default configuration if not provided
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('configuration'):
                vals['configuration'] = self._get_default_configuration()
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('is_default', 'user_id', 'dashboard_type')
    def _check_single_default(self):
        for rec in self:
            if not rec.is_default:
                continue
            domain = [
                ('user_id', '=', rec.user_id.id),
                ('dashboard_type', '=', rec.dashboard_type),
                ('is_default', '=', True),
                ('id', '!=', rec.id),
            ]
            if self.search_count(domain):
                raise ValidationError(_(
                    "User %s already has a default %s dashboard.")
                    % (rec.user_id.display_name, rec.dashboard_type))

    @api.constrains('dashboard_type', 'student_id', 'faculty_id')
    def _check_dashboard_consistency(self):
        for rec in self:
            if rec.dashboard_type == 'student' and rec.faculty_id:
                raise ValidationError(_(
                    "Student dashboard %s cannot be linked to a faculty member.")
                    % rec.display_name)
            if rec.dashboard_type == 'faculty' and rec.student_id:
                raise ValidationError(_(
                    "Faculty dashboard %s cannot be linked to a student.")
                    % rec.display_name)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def action_reset_dashboard(self):
        """Reset the dashboard configuration to default values."""
        default_config = self._get_default_configuration()
        for rec in self:
            rec.configuration = default_config
            rec.message_post(body=_(
                "Dashboard configuration reset to defaults."))

    def action_mark_accessed(self):
        """Increment access count and update last_accessed timestamp."""
        for rec in self:
            rec.write({
                'access_count': rec.access_count + 1,
                'last_accessed': fields.Datetime.now(),
            })

    def get_dashboard_data(self):
        """Return a dictionary representation of the dashboard.

        Includes parsed configuration, recipient identity and quick stats
        (e.g. unread notifications, student/faculty counts for admin type).
        """
        self.ensure_one()
        config = {}
        if self.configuration:
            try:
                config = json.loads(self.configuration)
            except (ValueError, TypeError):
                config = {}
        return {
            'id': self.id,
            'name': self.name,
            'type': self.dashboard_type,
            'user_id': self.user_id.id,
            'user_name': self.user_id.display_name,
            'student_id': self.student_id.id if self.student_id else False,
            'student_name': self.student_id.display_name if self.student_id else False,
            'faculty_id': self.faculty_id.id if self.faculty_id else False,
            'faculty_name': self.faculty_id.display_name if self.faculty_id else False,
            'configuration': config,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else False,
            'access_count': self.access_count,
            'stats': self._compute_dashboard_stats(),
        }

    def _compute_dashboard_stats(self):
        """Compute quick statistics for the dashboard."""
        self.ensure_one()
        stats = {
            'unread_notifications': 0,
            'student_count': 0,
            'faculty_count': 0,
        }
        Notification = self.env['uni.portal.notification'].sudo()
        if self.user_id:
            stats['unread_notifications'] = Notification.search_count([
                ('user_id', '=', self.user_id.id),
                ('is_read', '=', False),
            ])
        if self.dashboard_type == 'admin':
            stats['student_count'] = self.env['uni.student'].sudo().search_count([])
            stats['faculty_count'] = self.env['uni.faculty'].sudo().search_count([])
        return stats

    # ------------------------------------------------------------------
    # Helper used by controllers
    # ------------------------------------------------------------------
    @api.model
    def get_or_create_for_user(self, user, dashboard_type='student'):
        """Return the default dashboard for a user, creating one if needed.

        :param user: res.users recordset (single)
        :param dashboard_type: 'student' | 'faculty' | 'admin'
        :return: uni.portal.dashboard recordset (single)
        """
        user.ensure_one()
        dashboard = self.search([
            ('user_id', '=', user.id),
            ('dashboard_type', '=', dashboard_type),
            ('is_default', '=', True),
        ], limit=1)
        if not dashboard:
            dashboard = self.search([
                ('user_id', '=', user.id),
                ('dashboard_type', '=', dashboard_type),
            ], limit=1)
        if not dashboard:
            dashboard = self.create({
                'name': _('%s Dashboard') % dashboard_type.title(),
                'user_id': user.id,
                'dashboard_type': dashboard_type,
                'is_default': True,
            })
        return dashboard
