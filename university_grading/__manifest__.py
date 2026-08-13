# -*- coding: utf-8 -*-
{
    'name': 'University Grading',
    'version': '19.0.1.0.0',
    'summary': 'University ERP — Grading Framework',
    'description': """
University Grading
==================
إطار الدرجات — يحتوي على:
- أنظمة الدرجات (نقاطي، نسبي، حرفي)
- خطوط سلم الدرجات
- محرك حساب الدرجات المجرد (AbstractModel)
- حاسبة GPA (وراثة كلاسيكية من المحرك)
- التقديرات الحرفية
- جدول التحويل بين الأنظمة

This module is mandatory and provides grading infrastructure
for gradebook, transcripts, and GPA calculations.
    """,
    'author': 'University ERP Team',
    'website': 'https://example.com',
    'category': 'University/Grading',
    'license': 'LGPL-3',
    'depends': ['university_core'],
    'data': [
        'security/ir.model.access.csv',
        'security/grading_security.xml',
        'data/grading_data.xml',
        'views/uni_grading_system_views.xml',
        'views/uni_grading_scale_line_views.xml',
        'views/uni_grade_letter_views.xml',
        'views/uni_grade_conversion_views.xml',
        'views/uni_grading_calculator_views.xml',
        'views/menu_views.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': True,
    'sequence': 11,
}
