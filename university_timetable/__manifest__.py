# -*- coding: utf-8 -*-
{
    'name': 'University Timetable',
    'version': '19.0.1.0.0',
    'summary': 'University ERP — Timetable Management',
    'description': """
University Timetable
====================
وحدة إدارة الجداول الدراسية — تحتوي على:
- أنواع القاعات (uni.classroom.type) ومواصفاتها التقنية
- القاعات الدراسية (uni.classroom) مع حالة الصيانة/الإتاحة
- حجز القاعات (uni.classroom.booking) مع منع التعارض الزمني
- الفترات الزمنية (uni.timetable.slot) لكل يوم من أيام الأسبوع
- الجدول الدراسي (uni.timetable) لكل فصل دراسي مع دورة حياة
- خطوط الجدول (uni.timetable.line) التي تربط المقرر بعضو هيئة التدريس والقاعة والفترة

This module is part of the University ERP and provides complete timetable
management including classroom catalogue, classroom booking with conflict
prevention, time slots, and per-term timetables with conflict detection
at the faculty / classroom / slot level.
    """,
    'author': 'University ERP Team',
    'website': 'https://example.com',
    'category': 'University/Timetable',
    'license': 'LGPL-3',
    'depends': ['university_curriculum', 'university_faculty'],
    'data': [
        # Security
        'security/ir.model.access.csv',
        # Data
        'data/ir_sequence_data.xml',
        'data/timetable_slots_data.xml',
        # Views
        'views/uni_classroom_type_views.xml',
        'views/uni_classroom_views.xml',
        'views/uni_classroom_booking_views.xml',
        'views/uni_timetable_slot_views.xml',
        'views/uni_timetable_views.xml',
        'views/uni_timetable_line_views.xml',
        'views/menu_views.xml',
        # Reports
        'reports/timetable_report.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': True,
    'sequence': 15,
}
