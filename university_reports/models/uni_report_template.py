# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniReportTemplate(models.Model):
    """قوالب التقارير — تعريف مركزي لأنواع التقارير المتاحة في الجامعة.

    يحتوي كل قالب على:
        * اسم ورمز فريد
        * نوع التقرير (طلابي / أكاديمي / مالي / إحصائي / تشغيلي / مخصص)
        * اسم النموذج الفني المُراد التقرير عنه
        * اسم نموذج المعالج (wizard) إن وجد لجمع المعطيات
        * ربط اختياري بإجراء تقرير QWeb (ir.actions.report)

    القوالب القياسية (is_standard=True) تُحمّل عبر ملف البيانات
    ``data/report_templates_data.xml`` ولا يُفضّل تعديلها أو حذفها.
    """
    _name = 'uni.report.template'
    _description = 'University Report Template'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'report_type, sequence, name'

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Name', required=True, translate=True, tracking=True,
        help='Human-readable name of the report template.')
    code = fields.Char(
        string='Code', required=True, copy=False, index=True, tracking=True,
        help='Unique technical code identifying this template (e.g. STD-LIST).')
    sequence = fields.Integer(
        string='Sequence', default=10,
        help='Order in which templates are listed.')

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------
    report_type = fields.Selection([
        ('student', 'Student'),
        ('academic', 'Academic'),
        ('financial', 'Financial'),
        ('statistical', 'Statistical'),
        ('operational', 'Operational'),
        ('custom', 'Custom'),
    ], string='Report Type', required=True, default='custom',
        tracking=True, index=True, group_expand='_group_expand_report_types')

    # ------------------------------------------------------------------
    # Target / wizard / action binding
    # ------------------------------------------------------------------
    model_name = fields.Char(
        string='Target Model',
        help='Technical model name to report on (e.g. uni.student).')
    wizard_model = fields.Char(
        string='Wizard Model',
        help='Technical wizard model name used to collect parameters '
             '(e.g. uni.report.wizard).')
    report_action_id = fields.Many2one(
        'ir.actions.report', string='QWeb Report Action',
        ondelete='restrict',
        help='Optional QWeb report action linked to this template. '
             'When set, the template can generate PDF/XLSX output directly.')

    # ------------------------------------------------------------------
    # Description / flags
    # ------------------------------------------------------------------
    description = fields.Text(string='Description', translate=True)
    is_standard = fields.Boolean(
        string='Standard Template', default=False, copy=False, tracking=True,
        help='Standard templates are shipped with the module and should not '
             'be deleted.')
    is_active = fields.Boolean(
        string='Active', default=True, tracking=True,
        help='If unchecked, the template will not appear in selection lists.')

    active = fields.Boolean(default=True, tracking=True)

    # ------------------------------------------------------------------
    # Computed helpers
    # ------------------------------------------------------------------
    builder_count = fields.Integer(
        string='Builders Count',
        compute='_compute_builder_count',
        help='Number of report builders currently using this template.')

    @api.depends('code')
    def _compute_builder_count(self):
        builder_obj = self.env['uni.report.builder']
        for rec in self:
            rec.builder_count = builder_obj.search_count([
                ('template_id', '=', rec.id),
            ]) if rec.id else 0

    def _group_expand_report_types(self, states, domain, order):
        return [key for key, _ in self._fields['report_type'].selection]

    # ------------------------------------------------------------------
    # SQL constraints
    # ------------------------------------------------------------------
    _sql_constraints = [
        ('unique_code', 'unique(code)',
         'The template code must be unique.'),
    ]

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    @api.constrains('code')
    def _check_code_nonempty(self):
        for rec in self:
            if not rec.code or not rec.code.strip():
                raise ValidationError(_(
                    "Template code cannot be empty (%s).") % rec.display_name)
            # Avoid spaces / weird characters
            stripped = rec.code.strip()
            if stripped != rec.code:
                rec.code = stripped

    @api.constrains('is_standard', 'active')
    def _check_standard_not_archived(self):
        """Standard templates should remain active to avoid breaking
        seeded builders that reference them."""
        for rec in self:
            if rec.is_standard and not rec.active:
                raise ValidationError(_(
                    "Standard template '%s' cannot be archived. "
                    "Disable it by unchecking 'Active' flag (is_active) "
                    "instead.") % rec.display_name)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_generate_report(self):
        """Generate a report from this template.

        If a wizard model is defined, opens the wizard pre-configured
        with the current template. Otherwise, if a QWeb report action
        is linked, runs it directly. Otherwise, opens a new builder
        record pre-configured with the template.
        """
        self.ensure_one()
        if not self.is_active:
            raise ValidationError(_(
                "Template '%s' is not active.") % self.display_name)

        # 1) Wizard path — preferred for parameterised reports
        if self.wizard_model:
            try:
                wizard_model = self.env[self.wizard_model]
            except KeyError:
                raise ValidationError(_(
                    "Wizard model '%s' is not registered in the system.")
                    % self.wizard_model)
            wizard = wizard_model.create({
                'template_id': self.id,
            })
            return {
                'name': _('Generate Report'),
                'type': 'ir.actions.act_window',
                'res_model': self.wizard_model,
                'res_id': wizard.id,
                'view_mode': 'form',
                'target': 'new',
                'context': {'default_template_id': self.id},
            }

        # 2) Direct QWeb path
        if self.report_action_id:
            return self.report_action_id.report_action(self)

        # 3) Builder path — fall back to creating a new builder record
        builder = self.env['uni.report.builder'].create({
            'template_id': self.id,
            'name_custom': self.name,
        })
        return {
            'name': _('Report Builder'),
            'type': 'ir.actions.act_window',
            'res_model': 'uni.report.builder',
            'res_id': builder.id,
            'view_mode': 'form',
            'context': {'default_template_id': self.id},
        }

    def action_view_builders(self):
        """Open the list of builders using this template."""
        self.ensure_one()
        return {
            'name': _('Report Builders'),
            'type': 'ir.actions.act_window',
            'res_model': 'uni.report.builder',
            'view_mode': 'list,form',
            'domain': [('template_id', '=', self.id)],
        }
