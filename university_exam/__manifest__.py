# -*- coding: utf-8 -*-
{
    'name': 'University Exam',
    'version': '19.0.1.0.0',
    'summary': 'University ERP — Exam Management',
    'description': """
University Exam
===============
وحدة إدارة الامتحانات — تحتوي على:
- نوع الامتحان (uni.exam.type)
  * خصائص افتراضية: الطبيعة، المدة، الدرجة العظمى، الوزن، نسبة النجاح
- الامتحان (uni.exam)
  * ربط بمقرر وفصل دراسي ونوع امتحان
  * قاعات ومراقبين ومخالفات وجداول
  * سير العمل: draft → scheduled → ongoing → completed / cancelled
- جدول الامتحانات (uni.exam.schedule)
  * نشر جداول الامتحانات لكل فصل دراسي
- قاعات الامتحان (uni.exam.room)
  * قاعات مخصصة للامتحانات مع التجهيزات والحالة
- المراقبون (uni.exam.invigilator)
  * مراقبو الامتحانات مع الأدوار (رئيس/مساعد/مراقب)
- المخالفات (uni.exam.violation)
  * مخالفات الطلاب أثناء الامتحانات مع الإجراءات المتخذة
- تسهيلات الامتحان (uni.exam.accommodation)
  * تسهيلات للطلاب ذوي الاحتياجات الخاصة (وقت إضافي، تقنيات مساعدة، إلخ)
  * سير العمل: draft → submitted → under_review → approved/denied → applied

This module is part of the University ERP and provides complete
exam management: scheduling, room assignment, invigilator allocation,
and violation tracking.
    """,
    'author': 'University ERP Team',
    'website': 'https://example.com',
    'category': 'University/Exam',
    'license': 'LGPL-3',
    'depends': [
        'university_curriculum',
        'university_grading',
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
        # Data
        'data/ir_sequence_data.xml',
        'data/exam_types_data.xml',
        # Views
        'views/uni_exam_type_views.xml',
        'views/uni_exam_views.xml',
        'views/uni_exam_schedule_views.xml',
        'views/uni_exam_room_views.xml',
        'views/uni_exam_invigilator_views.xml',
        'views/uni_exam_violation_views.xml',
        'views/uni_exam_accommodation_views.xml',
        'views/menu_views.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
    'sequence': 17,
}
