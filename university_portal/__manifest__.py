# -*- coding: utf-8 -*-
{
    'name': 'University Portal',
    'version': '19.0.1.0.0',
    'summary': 'University ERP — Student & Faculty Portals',
    'description': """
University Portal
=================
وحدة البوابات الإلكترونية لنظام ERP الجامعي — توفر:

- بوابة الطالب (uni.portal.student) — تسجيل دخول الطلاب وإدارة حساباتهم
- بوابة عضو هيئة التدريس (uni.portal.faculty) — تسجيل دخول أعضاء التدريس
- لوحة المعلومات (uni.portal.dashboard) — لوحات قابلة للتخصيص لكل مستخدم
- الإشعارات (uni.portal.notification) — إشعارات موجهة للطلاب/أعضاء التدريس

كما توفر الوحدة:
- واجهات ويب (QWeb) مدمجة مع وحدة website
- متحكمات HTTP للوصول إلى صفحات البوابة
- قوائم University الموجودة + قائمة موقع جديد
- مجموعات صلاحيات مخصصة للطلاب وأعضاء التدريس على البوابة

This module is part of the University ERP and provides web portal access
for students and faculty members, including personalised dashboards
and a notification system.
    """,
    'author': 'University ERP Team',
    'website': 'https://example.com',
    'category': 'University/Portal',
    'license': 'LGPL-3',
    'depends': [
        'website',
        'university_student',
        'university_faculty',
    ],
    'data': [
        # Security
        'security/university_portal_security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/ir_sequence_data.xml',
        # Backend views
        'views/uni_portal_student_views.xml',
        'views/uni_portal_faculty_views.xml',
        'views/uni_portal_dashboard_views.xml',
        'views/uni_portal_notification_views.xml',
        # Frontend templates
        'views/templates/portal_layout.xml',
        'views/templates/portal_student_dashboard.xml',
        'views/templates/portal_faculty_dashboard.xml',
        'views/templates/portal_notifications.xml',
        # Menus
        'views/menu_views.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
    'sequence': 20,
}
