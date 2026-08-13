# -*- coding: utf-8 -*-
import json
import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class UniDashboardWidget(models.Model):
    """ودجات لوحة المعلومات — عناصر مرئية تُعرض في لوحة المستخدم.

    كل ودجة تُعرّف:
        * نوع العنصر (KPI / رسم / جدول / قائمة / تقويم / مقياس / عداد)
        * مصدر البيانات (نموذج + دالة)
        * إعدادات العرض (موقع، أبعاد، لون، أيقونة، فترة تحديث)

    تُجلب البيانات عبر ``get_widget_data()`` التي تستدعي الدالة المُحدّدة
    في ``data_source_method`` على النموذج ``data_source_model`` وتمرّر
    إعدادات الـ ``configuration`` (JSON) كمعطيات.
    """
    _name = 'uni.dashboard.widget'
    _description = 'University Dashboard Widget'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'user_id, widget_type, sequence, id'

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Name', required=True, translate=True, tracking=True,
        help='Human-readable name of the widget.')
    code = fields.Char(
        string='Code', required=True, copy=False, index=True, tracking=True,
        help='Unique code per user (e.g. STUD-KPI-1).')
    sequence = fields.Integer(
        string='Sequence', default=10,
        help='Order in which widgets are rendered within their type.')

    # ------------------------------------------------------------------
    # Owner
    # ------------------------------------------------------------------
    user_id = fields.Many2one(
        'res.users', string='Owner',
        default=lambda self: self.env.user, ondelete='cascade',
        tracking=True, index=True, required=True)

    # ------------------------------------------------------------------
    # Visual configuration
    # ------------------------------------------------------------------
    widget_type = fields.Selection([
        ('kpi', 'KPI'),
        ('chart', 'Chart'),
        ('table', 'Table'),
        ('list', 'List'),
        ('calendar', 'Calendar'),
        ('gauge', 'Gauge'),
        ('counter', 'Counter'),
    ], string='Widget Type', required=True, default='kpi',
        tracking=True, index=True, group_expand='_group_expand_widget_types')

    data_source_model = fields.Char(
        string='Data Source Model',
        tracking=True,
        help='Technical model name to fetch data from (e.g. uni.student).')
    data_source_method = fields.Char(
        string='Data Source Method',
        tracking=True,
        help='Method name on the data source model to call for data '
             '(must accept ``**kwargs`` and return a dict). '
             'Special value "search_count_default" returns the total '
             'record count of the model as an integer.')

    configuration = fields.Text(
        string='Configuration',
        tracking=True,
        help='JSON configuration passed to the data source method.')

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    position_x = fields.Integer(
        string='Position X', default=0,
        help='Horizontal position on the dashboard grid (column index).')
    position_y = fields.Integer(
        string='Position Y', default=0,
        help='Vertical position on the dashboard grid (row index).')
    width = fields.Integer(
        string='Width', default=4,
        help='Width in grid columns (1-12).')
    height = fields.Integer(
        string='Height', default=1,
        help='Height in grid rows.')

    refresh_interval_seconds = fields.Integer(
        string='Refresh Interval (s)', default=300,
        help='Number of seconds between automatic refreshes. '
             'Set to 0 to disable auto-refresh.')
    is_active = fields.Boolean(
        string='Active', default=True, tracking=True,
        help='If unchecked, the widget will be hidden from the dashboard.')

    color = fields.Char(
        string='Color', default='#6c757d',
        help='Hex color code used to accent the widget header.')
    icon = fields.Char(
        string='Icon', default='fa-th',
        help='FontAwesome icon class (e.g. fa-users, fa-chart-bar).')

    active = fields.Boolean(default=True, tracking=True)

    # ------------------------------------------------------------------
    # Group expand
    # ------------------------------------------------------------------
    def _group_expand_widget_types(self, states, domain, order):
        return [key for key, _ in self._fields['widget_type'].selection]

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    _sql_constraints = [
        ('unique_code_per_user',
         'unique(code, user_id)',
         'The widget code must be unique per user.'),
    ]

    @api.constrains('width', 'height', 'position_x', 'position_y',
                    'refresh_interval_seconds')
    def _check_layout_bounds(self):
        for rec in self:
            if rec.width < 1 or rec.width > 12:
                raise ValidationError(_(
                    "Widget '%s' width must be between 1 and 12.")
                    % rec.display_name)
            if rec.height < 1:
                raise ValidationError(_(
                    "Widget '%s' height must be at least 1.")
                    % rec.display_name)
            if rec.position_x < 0 or rec.position_y < 0:
                raise ValidationError(_(
                    "Widget '%s' position cannot be negative.")
                    % rec.display_name)
            if rec.refresh_interval_seconds < 0:
                raise ValidationError(_(
                    "Widget '%s' refresh interval cannot be negative.")
                    % rec.display_name)

    @api.constrains('configuration')
    def _check_configuration_json(self):
        for rec in self:
            if rec.configuration:
                try:
                    json.loads(rec.configuration)
                except (ValueError, TypeError) as exc:
                    raise ValidationError(_(
                        "Configuration for widget '%s' is not valid JSON: %s")
                        % (rec.display_name, exc))

    @api.constrains('data_source_model', 'data_source_method')
    def _check_data_source(self):
        for rec in self:
            if rec.data_source_model or rec.data_source_method:
                if not (rec.data_source_model and rec.data_source_method):
                    raise ValidationError(_(
                        "Widget '%s' must define both data source model "
                        "and method, or neither.") % rec.display_name)
                if rec.data_source_model not in self.env:
                    raise ValidationError(_(
                        "Widget '%s' references unregistered model '%s'.")
                        % (rec.display_name, rec.data_source_model))
                # ``search_count_default`` is built-in and resolved by
                # ``get_widget_data`` directly — no need to require it on
                # the target model.
                if rec.data_source_method != 'search_count_default':
                    target_model = self.env[rec.data_source_model]
                    method = getattr(target_model, rec.data_source_method, None)
                    if method is None or not callable(method):
                        raise ValidationError(_(
                            "Widget '%s' references unknown method '%s' on "
                            "model '%s'.")
                            % (rec.display_name, rec.data_source_method,
                               rec.data_source_model))

    # ------------------------------------------------------------------
    # Data access
    # ------------------------------------------------------------------
    def _parse_configuration(self):
        """Return the parsed JSON configuration as a dict."""
        self.ensure_one()
        if not self.configuration:
            return {}
        try:
            return json.loads(self.configuration) or {}
        except (ValueError, TypeError):
            return {}

    def get_widget_data(self):
        """Fetch data for the widget by calling the configured method.

        Returns a dict containing at least:
            ``id``       — widget id
            ``name``     — widget name
            ``type``     — widget type
            ``data``     — payload returned by the data source method
            ``meta``     — configuration, color, icon, etc.

        Falls back to an empty ``data`` dict when no data source is set.
        """
        self.ensure_one()
        meta = {
            'color': self.color or '#6c757d',
            'icon': self.icon or 'fa-th',
            'refresh_interval': self.refresh_interval_seconds or 0,
            'configuration': self._parse_configuration(),
        }
        data = {}
        if self.data_source_model and self.data_source_method and \
                self.data_source_model in self.env:
            try:
                target_model = self.env[self.data_source_model]
                # Built-in KPI helper — always available for any model
                if self.data_source_method == 'search_count_default':
                    count = target_model.search_count([])
                    data = {'count': count}
                else:
                    method = getattr(target_model, self.data_source_method)
                    data = method(**meta['configuration']) or {}
            except Exception as exc:
                _logger.exception(
                    "Widget %s data fetch failed: %s",
                    self.display_name, exc)
                data = {'error': str(exc)}
        return {
            'id': self.id,
            'name': self.name,
            'type': self.widget_type,
            'data': data,
            'meta': meta,
        }

    def action_refresh(self):
        """Trigger a refresh of the widget by re-fetching its data.

        Posts a message to the chatter recording the refresh event so
        users can audit when widgets were last refreshed.
        """
        for rec in self:
            try:
                payload = rec.get_widget_data()
                rec.message_post(body=_(
                    "Widget refreshed by %s — %s payload byte(s).") % (
                    self.env.user.name,
                    len(json.dumps(payload, default=str))))
            except Exception as exc:
                _logger.exception(
                    "Widget %s refresh failed: %s", rec.display_name, exc)
                rec.message_post(body=_(
                    "Widget refresh failed: %s") % exc)
        return True

    # ------------------------------------------------------------------
    # KPI helpers — used by dashboard widget defaults
    # ------------------------------------------------------------------
    @api.model
    def get_default_widgets_for_user(self, user=None):
        """Return a default set of dashboard widgets for the given user
        (or the current user).

        Currently returns a curated list of KPI widgets covering core
        university metrics. This is a convenience helper for portal &
        dashboard controllers — calling it does not persist records.
        """
        user = user or self.env.user
        defaults = [
            {
                'name': _('Total Students'),
                'code': 'STUD-COUNT',
                'widget_type': 'kpi',
                'data_source_model': 'uni.student',
                'data_source_method': 'search_count_default',
                'icon': 'fa-users',
                'color': '#0d6efd',
            },
            {
                'name': _('Active Programs'),
                'code': 'PROG-ACTIVE',
                'widget_type': 'kpi',
                'data_source_model': 'uni.program',
                'data_source_method': 'search_count_default',
                'icon': 'fa-graduation-cap',
                'color': '#198754',
            },
            {
                'name': _('Pending Invoices'),
                'code': 'FIN-PENDING',
                'widget_type': 'kpi',
                'data_source_model': 'uni.invoice.student',
                'data_source_method': 'search_count_default',
                'icon': 'fa-file-invoice-dollar',
                'color': '#dc3545',
            },
            {
                'name': _('Active Faculty'),
                'code': 'FAC-ACTIVE',
                'widget_type': 'kpi',
                'data_source_model': 'uni.faculty',
                'data_source_method': 'search_count_default',
                'icon': 'fa-chalkboard-teacher',
                'color': '#6f42c1',
            },
        ]
        # Filter out widgets whose model is not installed
        available = []
        for widget in defaults:
            if widget['data_source_model'] in self.env:
                available.append(widget)
        return available
