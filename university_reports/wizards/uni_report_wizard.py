# -*- coding: utf-8 -*-
import json
import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class UniReportWizard(models.TransientModel):
    """معالج التقارير — يجمع الفلاتر المشتركة للتقارير.

    يُستخدم من قوالب التقارير القياسية لفتح نموذج فلاتر صغير قبل إنتاج
    التقرير. عند ``action_generate_pdf`` يتم بناء سجل ``uni.report.builder``
    مع تخزين الفلاتر في ``filters_configuration`` كـ JSON ثم استدعاء
    ``action_run()`` عليه، وأخيراً إرجاع ملف PDF الناتج.

    يدعم أيضاً ``action_generate_xlsx()`` لإنتاج ملف Excel.
    """
    _name = 'uni.report.wizard'
    _description = 'University Report Wizard'

    # ------------------------------------------------------------------
    # Template link
    # ------------------------------------------------------------------
    template_id = fields.Many2one(
        'uni.report.template', string='Report Template',
        required=True, ondelete='restrict',
        help='The template that drives this wizard session.')

    # ------------------------------------------------------------------
    # Common filters
    # ------------------------------------------------------------------
    university_id = fields.Many2one(
        'uni.university', string='University',
        ondelete='restrict',
        help='Filter records by university.')
    college_id = fields.Many2one(
        'uni.college', string='College',
        ondelete='restrict',
        domain="[('university_id', '=', university_id)]",
        help='Filter records by college.')
    department_id = fields.Many2one(
        'uni.department', string='Department',
        ondelete='restrict',
        domain="[('college_id', '=', college_id)]",
        help='Filter records by department.')
    program_id = fields.Many2one(
        'uni.program', string='Program',
        ondelete='restrict',
        domain="[('department_id', '=', department_id)]",
        help='Filter records by program.')

    # ------------------------------------------------------------------
    # Academic period
    # ------------------------------------------------------------------
    academic_year_id = fields.Many2one(
        'uni.academic.year', string='Academic Year',
        ondelete='restrict',
        domain="[('university_id', '=', university_id)]",
        help='Filter records by academic year.')
    academic_term_id = fields.Many2one(
        'uni.academic.term', string='Academic Term',
        ondelete='restrict',
        domain="[('academic_year_id', '=', academic_year_id)]",
        help='Filter records by academic term.')

    # ------------------------------------------------------------------
    # Date range
    # ------------------------------------------------------------------
    date_from = fields.Date(
        string='Date From',
        help='Include records with date on or after this date.')
    date_to = fields.Date(
        string='Date To',
        help='Include records with date on or before this date.')

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------
    output_format = fields.Selection([
        ('pdf', 'PDF'),
        ('xlsx', 'XLSX'),
        ('csv', 'CSV'),
        ('html', 'HTML'),
        ('screen', 'On Screen'),
    ], string='Output Format', default='pdf', required=True)

    # ------------------------------------------------------------------
    # Optional columns config (free-form JSON for advanced users)
    # ------------------------------------------------------------------
    columns_configuration = fields.Text(
        string='Columns Configuration',
        help='Optional JSON list of columns to include in the report. '
             'Leave empty to use the default columns.')

    notes = fields.Text(string='Notes')

    # ------------------------------------------------------------------
    # Onchange — keep domains consistent
    # ------------------------------------------------------------------
    @api.onchange('university_id')
    def _onchange_university_id(self):
        if self.college_id and self.college_id.university_id != self.university_id:
            self.college_id = False
        if self.academic_year_id and \
                self.academic_year_id.university_id != self.university_id:
            self.academic_year_id = False

    @api.onchange('college_id')
    def _onchange_college_id(self):
        if self.department_id and self.department_id.college_id != self.college_id:
            self.department_id = False
        if self.program_id and self.program_id.college_id != self.college_id:
            self.program_id = False

    @api.onchange('department_id')
    def _onchange_department_id(self):
        if self.program_id and self.program_id.department_id != self.department_id:
            self.program_id = False

    @api.onchange('academic_year_id')
    def _onchange_academic_year_id(self):
        if self.academic_term_id and \
                self.academic_term_id.academic_year_id != self.academic_year_id:
            self.academic_term_id = False

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    @api.constrains('date_from', 'date_to')
    def _check_date_range(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_from > rec.date_to:
                raise ValidationError(_(
                    "Date From (%s) cannot be after Date To (%s).")
                    % (rec.date_from, rec.date_to))

    @api.constrains('columns_configuration')
    def _check_columns_configuration(self):
        for rec in self:
            if rec.columns_configuration:
                try:
                    parsed = json.loads(rec.columns_configuration)
                except (ValueError, TypeError) as exc:
                    raise ValidationError(_(
                        "Columns configuration is not valid JSON: %s") % exc)
                if not isinstance(parsed, list):
                    raise ValidationError(_(
                        "Columns configuration must be a JSON list."))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _build_filters(self):
        """Return a dict of non-empty filter values for the builder."""
        self.ensure_one()
        filters = {}
        for fname in ('university_id', 'college_id', 'department_id',
                      'program_id', 'academic_year_id', 'academic_term_id'):
            value = getattr(self, fname).id if getattr(self, fname) else False
            if value:
                filters[fname] = value
        if self.date_from:
            filters['date_from'] = fields.Date.to_string(self.date_from)
        if self.date_to:
            filters['date_to'] = fields.Date.to_string(self.date_to)
        return filters

    def _build_builder_values(self):
        """Return the vals used to create the underlying builder."""
        self.ensure_one()
        return {
            'template_id': self.template_id.id,
            'name_custom': self.template_id.name,
            'output_format': self.output_format,
            'filters_configuration': json.dumps(self._build_filters()),
            'columns_configuration': self.columns_configuration or '[]',
            'user_id': self.env.user.id,
        }

    def _create_and_run_builder(self):
        """Create the builder record, run it, and return it.

        Used for non-PDF output formats (XLSX/CSV/HTML/screen). For PDF
        output, prefer :meth:`_render_qweb_report` which delegates to the
        template's linked QWeb report action.
        """
        self.ensure_one()
        if not self.template_id:
            raise UserError(_("A report template is required."))
        builder = self.env['uni.report.builder'].create(
            self._build_builder_values())
        builder.action_run()
        if not builder.saved_result and self.output_format != 'screen':
            raise UserError(_(
                "Report generation produced no output. Please check the "
                "filters and try again. (Builder: %s)")
                % builder.display_name)
        return builder

    def _render_qweb_report(self):
        """Render the linked QWeb report action directly.

        The wizard is the bound model — QWeb templates read filter fields
        from ``object`` (the wizard) and fetch records internally.

        Returns a ``uni.report.builder`` record with the saved PDF result
        (for download) or ``None`` if no QWeb action is linked.
        """
        import base64
        self.ensure_one()
        action = self.template_id.report_action_id
        if not action:
            return None
        pdf_bytes, _ext = action._render_qweb_pdf(self.ids)
        # Build a deterministic filename
        base = (self.template_id.name or 'report').strip()
        base = '_'.join(base.split())
        filename = '%s.pdf' % base
        # Persist the result on a builder for history & download
        builder = self.env['uni.report.builder'].create(
            self._build_builder_values())
        builder.write({
            'saved_result': base64.b64encode(pdf_bytes).decode('ascii'),
            'saved_result_filename': filename,
            'last_run_date': fields.Datetime.now(),
            'result_count': 0,  # actual count is computed inside the QWeb
            'state': 'completed',
        })
        return builder

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_generate_pdf(self):
        """Generate a PDF report from the wizard's filters.

        Prefers the template's linked QWeb report action when available
        (renders a professionally formatted PDF). Falls back to the
        generic builder pipeline otherwise.
        """
        self.ensure_one()
        # Try the QWeb path first
        builder = self._render_qweb_report()
        if builder:
            return builder.action_download()
        # Fallback: use the generic builder pipeline
        previous = self.output_format
        self.output_format = 'pdf'
        try:
            builder = self._create_and_run_builder()
        finally:
            self.output_format = previous
        return builder.action_download()

    def action_generate_xlsx(self):
        """Generate an XLSX report from the wizard's filters."""
        self.ensure_one()
        previous = self.output_format
        self.output_format = 'xlsx'
        try:
            builder = self._create_and_run_builder()
        finally:
            self.output_format = previous
        return builder.action_download()

    def action_generate(self):
        """Generic generate action — honours ``output_format`` field."""
        self.ensure_one()
        if self.output_format == 'pdf':
            return self.action_generate_pdf()
        if self.output_format == 'screen':
            builder = self._create_and_run_builder()
            return builder.action_preview()
        builder = self._create_and_run_builder()
        return builder.action_download()
