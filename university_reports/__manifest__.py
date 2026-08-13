# -*- coding: utf-8 -*-
{
    'name': 'University Reports',
    'version': '19.0.1.0.0',
    'summary': 'University ERP — Advanced Reporting & Dashboards',
    'description': """
University Reports
==================
وحدة التقارير المتقدمة ولوحات المعلومات — تحتوي على:

- قوالب التقارير (uni.report.template)
  * قوالب قياسية لكل أنواع التقارير (طلابي / أكاديمي / مالي / إحصائي / تشغيلي)
  * ربط اختياري بإجراءات تقارير QWeb (ir.actions.report)
- منشئ التقارير (uni.report.builder)
  * اختيار قالب وفلاتر وأعمدة ونوع رسم وإخراج (PDF/XLSX/CSV/HTML/Screen)
  * حفظ آخر نتيجة وتشغيل مجدّد
- جدولة التقارير (uni.report.schedule)
  * جدولة يومية / أسبوعية / شهرية / ربع سنوية / سنوية / مخصصة
  * إرسال بريد تلقائي وحفظ الملف
- ودجات لوحة المعلومات (uni.dashboard.widget)
  * ودجات KPI / رسم / جدول / تقويم / مقياس / عداد
  * إعدادات موقع ولون وأيقونة وفترة تحديث
- معالج التقارير (uni.report.wizard)
  * جمع الفلاتر المشتركة (جامعة / كلية / قسم / برنامج / سنة / فصل / تواريخ)
  * توليد PDF / XLSX
- تقارير QWeb PDF جاهزة للإنتاج:
  * قائمة الطلاب
  * ملخص الكشوف الأكاديمية
  * الملخص المالي
  * إحصاءات التسجيل
  * توزيع المواقف الأكاديمية

This module is part of the University ERP and provides advanced
reporting, scheduling and dashboard infrastructure for all
university operations.

DEPENDENCY NOTE (per spec):
==========================
This module depends ONLY on ``university_core``. All references to
other university modules (uni.student, uni.faculty, uni.invoice.student,
uni.transcript, uni.student.enrollment, uni.gradebook.*) are stored
as free-text Char fields (model_name, wizard_model, data_source_model,
data_source_method). The wizard's Many2one fields target only
university_core models (uni.university, uni.college, uni.department,
uni.program, uni.academic.year, uni.academic.term).

The predefined QWeb report templates reference data from other
modules; they will only produce non-empty output if those modules are
installed. Each template description notes the module(s) it requires.
""",
    'author': 'University ERP Team',
    'website': 'https://example.com',
    'category': 'University/Reports',
    'license': 'LGPL-3',
    'depends': [
        'university_core',
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
        # Data — sequences & cron (loaded first)
        'data/ir_sequence_data.xml',
        'data/cron_data.xml',
        # Data — predefined templates & wizard actions (basic, no QWeb link yet)
        'data/report_templates_data.xml',
        # QWeb Reports (paperformats + ir.actions.report + templates + wizard actions)
        'reports/student_list_report.xml',
        'reports/student_list_report_template.xml',
        'reports/transcript_summary_report.xml',
        'reports/financial_summary_report.xml',
        'reports/enrollment_statistics_report.xml',
        'reports/academic_standing_report.xml',
        # Data — post-load links between templates and QWeb report actions
        'data/report_action_links.xml',
        # Views
        'views/uni_report_template_views.xml',
        'views/uni_report_builder_views.xml',
        'views/uni_report_schedule_views.xml',
        'views/uni_dashboard_widget_views.xml',
        'views/wizard_views.xml',
        'views/menu_views.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': False,  # Corrected from True per architecture
    'sequence': 28,
}
