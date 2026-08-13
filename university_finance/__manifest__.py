# -*- coding: utf-8 -*-
{
    'name': 'University Finance',
    'version': '19.0.1.0.0',
    'summary': 'University ERP — Financial Management',
    'description': """
University Finance
==================
وحدة الإدارة المالية للجامعة — تحتوي على:

- أنواع الرسوم (uni.fee.type)
  * تصنيفات الرسوم: tuition, lab, library, activity, registration,
    graduation, housing, transport, late_penalty, other
  * رسوم متكررة ومبالغ افتراضية
- هيكل الرسوم (uni.fee.structure + uni.fee.structure.line + uni.fee.installment)
  * هيكل مرتبط بالجامعة/الكلية/القسم/البرنامج ومستوى البرنامج والفصل الدراسي
  * بنود هيكل قابلة للتعديل لكل نوع رسوم
  * أقساط مع تواريخ استحقاق وغرامات تأخير
- المنح الدراسية (uni.scholarship + uni.scholarship.type)
  * منح كاملة/جزئية/استحقاق/احتياج/رياضة/تابعين موظفين
  * سير اعتماد (draft → pending → approved → active → terminated)
- الفواتير الطلابية (uni.invoice.student + uni.invoice.student.line)
  * فاتورة مرتبطة بالطالب والفصل وهيكل الرسوم
  * ربط اختياري بالمنح وخطط السداد
  * إنشاء فاتورة Odoo (account.move) مرتبطة بالفاتورة الطلابية
- خطط السداد (uni.payment.plan + uni.payment.plan.line)
  * خطط أسبوعية/نصف شهرية/شهرية/ربع سنوية
  * توليد الأقساط تلقائياً مع متابعة حالة السداد

This module is part of the University ERP and provides complete
financial management including fee structures, scholarships,
student invoicing, and payment plans.
    """,
    'author': 'University ERP Team',
    'website': 'https://example.com',
    'category': 'University/Finance',
    'license': 'LGPL-3',
    'depends': ['university_core', 'university_student', 'account'],
    'data': [
        # Security
        'security/ir.model.access.csv',
        # Data
        'data/ir_sequence_data.xml',
        'data/finance_data.xml',
        # Views
        'views/uni_fee_type_views.xml',
        'views/uni_fee_structure_views.xml',
        'views/uni_scholarship_views.xml',
        'views/uni_invoice_student_views.xml',
        'views/uni_payment_plan_views.xml',
        'views/menu_views.xml',
        # Reports
        'reports/student_invoice_report.xml',
        'reports/student_invoice_report_template.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
    'sequence': 19,
}
