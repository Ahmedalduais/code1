# -*- coding: utf-8 -*-
import base64
import io
import json
import time
import logging
import csv
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class UniReportBuilder(models.Model):
    """منشئ التقارير — يجمع القالب والفلاتر والتكوينات لإنتاج تقرير.

    سير العمل:
        draft → ready → running → completed
                            ↘ error

    عند ``action_run()`` يتم:
        1. تحويل الحالة إلى ``running`` وتسجيل وقت البدء
        2. تنفيذ التقرير عبر الـ wizard (إن وجد) أو إجراء QWeb أو استعلام
           نموذج الإطار مباشرة
        3. تخزين النتيجة في ``saved_result`` كملف Binary
        4. تحديث ``last_run_date`` و``last_run_duration_seconds`` و
           ``result_count`` وتحويل الحالة إلى ``completed`` (أو ``error``)

    عند الفشل يتم تسجيل رسالة الخطأ في الـ chatter وتحويل الحالة إلى
    ``error`` دون رفع استثناء لقطع التنفيذ المجدول.
    """
    _name = 'uni.report.builder'
    _description = 'University Report Builder'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'last_run_date desc, id'

    # ------------------------------------------------------------------
    # Identity / sequence
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Reference', copy=False, readonly=True, index=True,
        default='New', tracking=True,
        help='Auto-generated reference identifying this builder instance.')
    code = fields.Char(
        string='Code', copy=False, tracking=True, index=True,
        help='Optional human-friendly code for this builder.')
    name_custom = fields.Char(
        string='Custom Title', tracking=True,
        help='User-defined title for the generated report.')

    # ------------------------------------------------------------------
    # Links
    # ------------------------------------------------------------------
    template_id = fields.Many2one(
        'uni.report.template', string='Template',
        required=True, ondelete='restrict', tracking=True, index=True)
    user_id = fields.Many2one(
        'res.users', string='Owner',
        default=lambda self: self.env.user, ondelete='restrict',
        tracking=True, index=True)

    # ------------------------------------------------------------------
    # Configuration (JSON-encoded)
    # ------------------------------------------------------------------
    filters_configuration = fields.Text(
        string='Filters Configuration', tracking=True,
        help='JSON object describing the applied filters '
             '(e.g. {"college_id": 3, "academic_term_id": 7}).')
    group_by = fields.Char(
        string='Group By', tracking=True,
        help='Field name(s) used to group the result rows.')
    sort_by = fields.Char(
        string='Sort By', tracking=True,
        help='Field name(s) used to sort the result rows.')
    columns_configuration = fields.Text(
        string='Columns Configuration', tracking=True,
        help='JSON list of selected columns, each '
             '{"name": "field", "label": "Header", "type": "text|number|date"}.')

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------
    chart_type = fields.Selection([
        ('none', 'None'),
        ('bar', 'Bar'),
        ('line', 'Line'),
        ('pie', 'Pie'),
        ('donut', 'Donut'),
        ('area', 'Area'),
        ('radar', 'Radar'),
    ], string='Chart Type', default='none', tracking=True)
    output_format = fields.Selection([
        ('pdf', 'PDF'),
        ('xlsx', 'XLSX'),
        ('csv', 'CSV'),
        ('html', 'HTML'),
        ('screen', 'On Screen'),
    ], string='Output Format', default='pdf', required=True, tracking=True)

    # ------------------------------------------------------------------
    # Execution metadata
    # ------------------------------------------------------------------
    last_run_date = fields.Datetime(
        string='Last Run Date', readonly=True, tracking=True)
    last_run_duration_seconds = fields.Float(
        string='Last Run Duration (s)', digits=(10, 3), readonly=True,
        help='Wall-clock duration of the last execution in seconds.')
    result_count = fields.Integer(
        string='Result Count', default=0, readonly=True,
        help='Number of rows returned by the last execution.')
    saved_result = fields.Binary(
        string='Saved Result', readonly=True, attachment=False,
        help='Last saved result file (PDF/XLSX/CSV/HTML).')
    saved_result_filename = fields.Char(
        string='Saved Result Filename', readonly=True)

    # ------------------------------------------------------------------
    # Scheduling
    # ------------------------------------------------------------------
    is_scheduled = fields.Boolean(
        string='Scheduled', default=False, tracking=True,
        help='If set, this builder runs on a schedule defined by '
             '``schedule_id``.')
    schedule_id = fields.Many2one(
        'uni.report.schedule', string='Schedule',
        ondelete='set null', tracking=True,
        help='Schedule that drives this builder (when ``is_scheduled``).')

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------
    state = fields.Selection([
        ('draft', 'Draft'),
        ('ready', 'Ready'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('error', 'Error'),
    ], string='Status', default='draft', tracking=True, index=True,
        group_expand='_group_expand_states')
    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True, tracking=True)

    # ------------------------------------------------------------------
    # Group expand
    # ------------------------------------------------------------------
    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in self._fields['state'].selection]

    # ------------------------------------------------------------------
    # Onchange
    # ------------------------------------------------------------------
    @api.onchange('template_id')
    def _onchange_template_id(self):
        """When a template is chosen, pre-fill model name & output defaults."""
        if self.template_id:
            if not self.name_custom:
                self.name_custom = self.template_id.name
            if not self.filters_configuration:
                self.filters_configuration = '{}'
            if not self.columns_configuration:
                self.columns_configuration = '[]'
            self.state = 'ready'

    # ------------------------------------------------------------------
    # Create — auto-generate reference & code
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.report.builder') or _('RPB-NEW')
            if not vals.get('code'):
                vals['code'] = vals['name']
            # Move directly to ready when template is provided and no
            # explicit state was set by the caller.
            if vals.get('template_id') and not vals.get('state'):
                vals['state'] = 'ready'
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    @api.constrains('filters_configuration')
    def _check_filters_configuration_json(self):
        for rec in self:
            if rec.filters_configuration:
                try:
                    json.loads(rec.filters_configuration)
                except (ValueError, TypeError) as exc:
                    raise ValidationError(_(
                        "Filters configuration for '%s' is not valid JSON: %s")
                        % (rec.display_name, exc))

    @api.constrains('columns_configuration')
    def _check_columns_configuration_json(self):
        for rec in self:
            if rec.columns_configuration:
                try:
                    parsed = json.loads(rec.columns_configuration)
                except (ValueError, TypeError) as exc:
                    raise ValidationError(_(
                        "Columns configuration for '%s' is not valid JSON: %s")
                        % (rec.display_name, exc))
                if not isinstance(parsed, list):
                    raise ValidationError(_(
                        "Columns configuration for '%s' must be a JSON list.")
                        % rec.display_name)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _parse_filters(self):
        """Return the parsed filters configuration as a dict."""
        self.ensure_one()
        if not self.filters_configuration:
            return {}
        try:
            return json.loads(self.filters_configuration) or {}
        except (ValueError, TypeError):
            return {}

    def _parse_columns(self):
        """Return the parsed columns configuration as a list of dicts."""
        self.ensure_one()
        if not self.columns_configuration:
            return []
        try:
            parsed = json.loads(self.columns_configuration)
            return parsed if isinstance(parsed, list) else []
        except (ValueError, TypeError):
            return []

    def _get_target_records(self):
        """Build a domain from ``filters_configuration`` and return the
        matching recordset on ``template_id.model_name``.

        Falls back to an empty recordset if the model is not registered
        or no model name is configured.
        """
        self.ensure_one()
        model_name = self.template_id.model_name
        if not model_name or model_name not in self.env:
            # Return an empty recordset on a model that always exists
            # so callers can safely call len() and inspect _fields.
            return self.env['ir.attachment'].browse()
        filters = self._parse_filters()
        domain = []
        for key, value in filters.items():
            # Ignore JSON metadata keys (e.g. ``_meta``)
            if key.startswith('_'):
                continue
            # Skip pseudo-filters that aren't real model fields
            if key not in self.env[model_name]._fields:
                continue
            domain.append((key, '=', value))
        records = self.env[model_name].search(domain)
        # Apply sort_by if provided
        if self.sort_by and self.sort_by in self.env[model_name]._fields:
            try:
                records = records.sorted(lambda r: getattr(r, self.sort_by, ''))
            except Exception:
                pass
        return records

    def _build_filename(self, extension):
        """Build a safe filename for the saved result."""
        self.ensure_one()
        base = (self.name_custom or self.name or 'report').strip()
        # Replace spaces with underscores for filesystem safety
        base = '_'.join(base.split())
        return '%s.%s' % (base, extension)

    @staticmethod
    def _wrap_binary(raw_bytes):
        """Wrap raw bytes into base64 string for Binary field storage."""
        if raw_bytes is False or raw_bytes is None:
            return False
        if isinstance(raw_bytes, str):
            raw_bytes = raw_bytes.encode('utf-8')
        return base64.b64encode(raw_bytes).decode('ascii')

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_run(self):
        """Run the report and persist the result.

        Delegates the actual rendering to:
            * the linked QWeb report action (if any) for PDF/HTML
            * a CSV/XLSX exporter otherwise
            * a direct ``search()`` for on-screen mode

        Records timing and result count for diagnostics.
        """
        for rec in self:
            start = time.time()
            rec.state = 'running'
            rec.message_post(body=_("Report execution started by %s.")
                             % self.env.user.name)
            try:
                content, filename, count = rec._execute_report()
                duration = time.time() - start
                rec.write({
                    'last_run_date': fields.Datetime.now(),
                    'last_run_duration_seconds': duration,
                    'result_count': count or 0,
                    'saved_result': content or False,
                    'saved_result_filename': filename or False,
                    'state': 'completed',
                })
                rec.message_post(body=_(
                    "Report completed in %.3fs — %s row(s)."
                    ) % (duration, count or 0))
            except Exception as exc:
                duration = time.time() - start
                rec.write({
                    'last_run_date': fields.Datetime.now(),
                    'last_run_duration_seconds': duration,
                    'state': 'error',
                })
                _logger.exception("Report builder %s failed: %s",
                                  rec.display_name, exc)
                rec.message_post(body=_(
                    "Report execution failed: %s") % exc)
        return True

    def _execute_report(self):
        """Render the report based on ``output_format``.

        Returns a tuple ``(content_base64_or_False, filename, count)``.
        For ``screen`` format the content is ``False`` and only ``count``
        is meaningful.
        """
        self.ensure_one()
        fmt = self.output_format
        records = self._get_target_records()
        count = len(records)

        # Screen mode — no file produced, just the count
        if fmt == 'screen':
            return False, False, count

        # PDF — render via HTML→PDF using the configured columns.
        # The template's ``report_action_id`` is invoked by the wizard
        # directly (since QWeb reports are bound to ``uni.report.wizard``);
        # the builder uses a generic HTML→PDF pipeline for flexibility.
        if fmt == 'pdf':
            html = self._render_html_table(records)
            pdf_bytes = self._html_to_pdf(html)
            if pdf_bytes:
                return self._wrap_binary(pdf_bytes), \
                    self._build_filename('pdf'), count
            return self._wrap_binary(html.encode('utf-8')), \
                self._build_filename('html'), count

        if fmt == 'html':
            html = self._render_html_table(records)
            return self._wrap_binary(html.encode('utf-8')), \
                self._build_filename('html'), count

        if fmt == 'csv':
            csv_bytes = self._render_csv(records)
            return self._wrap_binary(csv_bytes), \
                self._build_filename('csv'), count

        if fmt == 'xlsx':
            xlsx_bytes = self._render_xlsx(records)
            return self._wrap_binary(xlsx_bytes), \
                self._build_filename('xlsx'), count

        return False, False, count

    # ------------------------------------------------------------------
    # Renderers
    # ------------------------------------------------------------------
    def _render_html_table(self, records):
        """Render an HTML table of the records using configured columns.

        Builds a fully styled HTML document suitable for direct rendering
        (HTML output) or for conversion to PDF via ``_html_to_pdf``.
        """
        self.ensure_one()
        columns = self._parse_columns()
        if not columns and records:
            columns = [{'name': f, 'label': f.replace('_', ' ').title()}
                       for f in list(records._fields.keys())[:8]]
        header_cells = ''.join(
            '<th>%s</th>' % (col.get('label') or col.get('name') or '')
            for col in columns)
        body_rows = []
        for rec in records:
            cells = []
            for col in columns:
                field_name = col.get('name')
                value = ''
                if field_name and field_name in rec._fields:
                    value = rec[field_name]
                    if isinstance(value, models.BaseModel):
                        value = value.display_name or ''
                    value = str(value) if value not in (False, None) else ''
                cells.append('<td>%s</td>' % value)
            body_rows.append('<tr>%s</tr>' % ''.join(cells))
        title = (self.name_custom or self.name or _('Report'))
        generated = fields.Datetime.now().strftime('%Y-%m-%d %H:%M')
        return (
            '<html><head><meta charset="utf-8"/>'
            '<style>'
            'body{font-family: Arial, sans-serif; padding: 16px;}'
            'h2{color:#2c3e50;}'
            'table{border-collapse:collapse; width:100%;}'
            'th,td{border:1px solid #ccc; padding:6px 8px; text-align:left;}'
            'th{background:#f0f0f0;}'
            '</style></head><body>'
            '<h2>%s</h2>'
            '<p><small>Generated: %s — %s row(s)</small></p>'
            '<table><thead><tr>%s</tr></thead><tbody>%s</tbody></table>'
            '</body></html>'
        ) % (title, generated, len(records),
             header_cells, ''.join(body_rows))

    def _html_to_pdf(self, html):
        """Convert HTML to PDF using the standard ``ir.actions.report``
        HTML→PDF rendering pipeline.

        Returns the PDF bytes on success, or ``False`` if conversion
        failed (e.g. wkhtmltopdf not installed). The caller is expected
        to fall back to HTML output in that case.
        """
        try:
            # ``_run_wkhtmltopdf`` accepts a list of HTML bodies
            bodies = [html.decode('utf-8') if isinstance(html, bytes) else html]
            return self.env['ir.actions.report']._run_wkhtmltopdf(
                bodies, landscape=False, specific_paperformat_args=None,
                set_viewport_size=False)
        except Exception:
            _logger.exception("wkhtmltopdf rendering failed; "
                              "falling back to HTML output.")
            return False

    def _render_csv(self, records):
        """Render records to a CSV byte string using configured columns."""
        self.ensure_one()
        columns = self._parse_columns()
        if not columns and records:
            columns = [{'name': f, 'label': f}
                       for f in list(records._fields.keys())[:8]]
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([col.get('label') or col.get('name') or ''
                         for col in columns])
        for rec in records:
            row = []
            for col in columns:
                field_name = col.get('name')
                value = ''
                if field_name and field_name in rec._fields:
                    value = rec[field_name]
                    if isinstance(value, models.BaseModel):
                        value = value.display_name or ''
                    value = '' if value in (False, None) else value
                row.append(value)
            writer.writerow(row)
        return buf.getvalue().encode('utf-8')

    def _render_xlsx(self, records):
        """Render records to an XLSX byte string.

        Requires ``openpyxl`` (shipped with Odoo as a dependency).
        Falls back to CSV bytes if openpyxl is unavailable.
        """
        try:
            from openpyxl import Workbook
        except ImportError:  # pragma: no cover — defensive
            _logger.warning(
                "openpyxl not available, falling back to CSV for builder %s",
                self.display_name)
            return self._render_csv(records)

        self.ensure_one()
        columns = self._parse_columns()
        if not columns and records:
            columns = [{'name': f, 'label': f}
                       for f in list(records._fields.keys())[:8]]
        wb = Workbook()
        ws = wb.active
        ws.title = (self.name_custom or self.name or 'Report')[:31]
        ws.append([col.get('label') or col.get('name') or ''
                   for col in columns])
        for rec in records:
            row = []
            for col in columns:
                field_name = col.get('name')
                value = ''
                if field_name and field_name in rec._fields:
                    value = rec[field_name]
                    if isinstance(value, models.BaseModel):
                        value = value.display_name or ''
                    value = '' if value in (False, None) else value
                row.append(value)
            ws.append(row)
        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    # ------------------------------------------------------------------
    # UI actions
    # ------------------------------------------------------------------
    def action_preview(self):
        """Open the on-screen preview by running the report in screen mode
        and returning an action to view the result records.
        """
        self.ensure_one()
        # Force a screen run
        previous_format = self.output_format
        try:
            self.output_format = 'screen'
            self.action_run()
        finally:
            self.output_format = previous_format
        if self.template_id.model_name and \
                self.template_id.model_name in self.env:
            return {
                'name': _('Preview: %s') % (self.name_custom or self.name),
                'type': 'ir.actions.act_window',
                'res_model': self.template_id.model_name,
                'view_mode': 'list,form',
                'domain': [('id', 'in', self._get_target_records().ids)],
            }
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Preview'),
                'message': _('Preview generated — %s row(s).') % self.result_count,
                'sticky': False,
            },
        }

    def action_download(self):
        """Download the saved result file (if any)."""
        self.ensure_one()
        if not self.saved_result:
            raise UserError(_(
                "No saved result available for builder '%s'. "
                "Run the report first.") % self.display_name)
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=uni.report.builder&id=%s&field=saved_result'
                   '&filename_field=saved_result_filename&download=true' % self.id,
            'target': 'self',
        }

    def action_save_as_template(self):
        """Create a new ``uni.report.template`` from the current builder
        configuration. The new template is non-standard.
        """
        self.ensure_one()
        new_template = self.env['uni.report.template'].create({
            'name': self.name_custom or self.template_id.name or _('New Template'),
            'code': 'CUST-%s' % (self.code or self.id),
            'report_type': self.template_id.report_type,
            'model_name': self.template_id.model_name,
            'wizard_model': self.template_id.wizard_model,
            'report_action_id': self.template_id.report_action_id.id,
            'description': _('Created from builder %s') % self.display_name,
            'is_standard': False,
            'is_active': True,
        })
        self.message_post(body=_(
            "Configuration saved as new template '%s' (code: %s).")
            % (new_template.name, new_template.code))
        return {
            'name': _('Saved Template'),
            'type': 'ir.actions.act_window',
            'res_model': 'uni.report.template',
            'res_id': new_template.id,
            'view_mode': 'form',
        }

    def action_draft(self):
        """Reset the builder to draft state."""
        for rec in self:
            if rec.state == 'running':
                raise UserError(_(
                    "Cannot reset a running report (%s).") % rec.display_name)
            rec.state = 'draft'

    def action_set_ready(self):
        """Move the builder from draft to ready."""
        for rec in self:
            if not rec.template_id:
                raise UserError(_(
                    "Builder %s must reference a template before being marked "
                    "as ready.") % rec.display_name)
            rec.state = 'ready'
