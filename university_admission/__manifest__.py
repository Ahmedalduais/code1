# -*- coding: utf-8 -*-
{
    'name': 'University Admission',
    'version': '19.0.1.0.0',
    'summary': 'University ERP — Admission & Registration',
    'description': """
University Admission
====================
وحدة القبول والتسجيل الجامعي — تحتوي على:

- طلب القبول (uni.admission.application)
  * دورة حياة كاملة (draft → submitted → under_review → interview_scheduled
    → accepted / rejected / waitlisted → enrolled)
  * بيانات المتقدم الشخصية والأكاديمية
  * مرفقات (نسخة الدرجات، خطابات التوصية، الصورة الشخصية)
  * ربط بالبرنامج والكلية والقسم والفصل الدراسي
  * إنشاء سجل طالب تلقائياً عند القبول النهائي (action_enroll)

- متطلبات القبول (uni.admission.requirement + uni.admission.requirement.line)
  * قائمة من المتطلبات القابلة لإعادة الاستخدام
  * خطوط متطلبات لكل طلب تتبع حالة الاستيفاء والمرفقات

- معايير القبول (uni.admission.criteria)
  * معايير الحد الأدنى للمعدل / GPA / درجة الاختبار
  * عمر الحد الأدنى والأقصى + رسوم التقديم
  * تقييم تلقائي للطلبات

- المقابلات (uni.admission.interview)
  * جدولة مقابلات مع أعضاء هيئة التدريس
  * حالة (scheduled/completed/cancelled/no_show)
  * تقييم وتوصية (strong_accept → strong_reject)

- القرارات (uni.admission.decision)
  * قبول / قبول مشروط / رفض / قائمة انتظار
  * منح دراسية وشروط وموعد نهائي للتسجيل

This module is part of the University ERP and provides the complete
admission & registration workflow for prospective students.
    """,
    'author': 'University ERP Team',
    'website': 'https://example.com',
    'category': 'University/Admission',
    'license': 'LGPL-3',
    'depends': ['university_core', 'university_student'],
    'data': [
        # Security
        'security/ir.model.access.csv',
        # Data
        'data/ir_sequence_data.xml',
        'data/admission_data.xml',
        # Views
        'views/uni_admission_application_views.xml',
        'views/uni_admission_requirement_views.xml',
        'views/uni_admission_criteria_views.xml',
        'views/uni_admission_interview_views.xml',
        'views/uni_admission_decision_views.xml',
        'views/menu_views.xml',
        # Reports
        'reports/admission_application_report.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
    'sequence': 16,
}
