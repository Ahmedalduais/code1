# -*- coding: utf-8 -*-
{
    'name': 'University Internship',
    'version': '19.0.1.0.0',
    'summary': 'University ERP — Field Training / Internship Management',
    'description': """
University Internship
=====================
وحدة التدريب الميداني — تدعم:
- جهات التدريب الخارجية (شركات/مؤسسات) مع اعتمادها
- فرص التدريب المتاحة مع المهارات المطلوبة
- طلبات التدريب والمقابلات
- الفرق (عدة طلاب في نفس التدريب)
- سجلات التدريب اليومية والحضور
- التقارير الأسبوعية والشهرية والنهائية
- التقييم (فردي/جماعي/مختلط) بمعايير قابلة للتكوين
- إتمام التدريب وإصدار الشهادات
- 21 نموذج متكامل

This module manages field training/internship with full team support,
external training entities, attendance tracking, periodic reports,
and comprehensive evaluation system.
    """,
    'author': 'University ERP Team',
    'website': 'https://example.com',
    'category': 'University/Internship',
    'license': 'LGPL-3',
    'depends': [
        'university_core',
        'university_student',
        'university_faculty',
        'university_curriculum',
        'hr',
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
        # Data
        'data/ir_sequence_data.xml',
        'data/internship_data.xml',
        # Views — ordered: parent models before child models
        'views/uni_internship_training_entity_views.xml',
        'views/uni_internship_entity_supervisor_views.xml',
        'views/uni_internship_opportunity_views.xml',
        'views/uni_internship_opportunity_skill_views.xml',
        'views/uni_internship_application_views.xml',
        'views/uni_internship_application_interview_views.xml',
        'views/uni_internship_team_views.xml',
        'views/uni_internship_team_member_views.xml',
        'views/uni_internship_views.xml',
        'views/uni_internship_student_views.xml',
        'views/uni_internship_supervisor_views.xml',
        'views/uni_internship_supervision_plan_views.xml',
        'views/uni_internship_log_views.xml',
        'views/uni_internship_attendance_views.xml',
        'views/uni_internship_weekly_report_views.xml',
        'views/uni_internship_report_views.xml',
        'views/uni_internship_evaluation_views.xml',
        'views/uni_internship_evaluation_criteria_views.xml',
        'views/uni_internship_completion_views.xml',
        'views/uni_internship_certificate_views.xml',
        'views/uni_internship_placement_views.xml',
        # Menu (last)
        'views/menu_views.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
    'sequence': 30,
}
