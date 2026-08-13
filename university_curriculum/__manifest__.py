# -*- coding: utf-8 -*-
{
    'name': 'University Curriculum',
    'version': '19.0.1.0.0',
    'summary': 'University ERP — Curriculum Management',
    'description': """
University Curriculum
=====================
وحدة المناهج الدراسية — تحتوي على:
- المقررات الدراسية (uni.course)
- المتطلبات السابقة (uni.course.prerequisite)
- المقررات المعادلة (uni.course.equivalent)
- نواتج التعلم (uni.course.outcome)
- توصيف المقرر (uni.course.syllabus)
- أنواع التقييم (uni.evaluation.type)
- تقييم المقرر بأقسام وبنود (uni.course.evaluation)
- ربط المقرر بالبرنامج (uni.program.course)
- خطوط ربط البرنامج (uni.program.course.line)

This module is a default-installed Tier 2 module that provides curriculum
management infrastructure for courses, evaluations, and program-course links.
    """,
    'author': 'University ERP Team',
    'website': 'https://example.com',
    'category': 'University/Curriculum',
    'license': 'LGPL-3',
    'depends': ['university_core'],
    'data': [
        # Security
        'security/ir.model.access.csv',
        # Data
        'data/evaluation_types_data.xml',
        # Views
        'views/uni_course_views.xml',
        'views/uni_course_type_views.xml',
        'views/uni_course_delivery_views.xml',
        'views/uni_evaluation_type_views.xml',
        'views/uni_course_evaluation_views.xml',
        'views/uni_program_course_views.xml',
        'views/menu_views.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': True,
    'sequence': 12,
}
