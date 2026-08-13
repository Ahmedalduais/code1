# -*- coding: utf-8 -*-
{
    'name': 'University Alumni',
    'version': '19.0.1.0.0',
    'summary': 'University ERP — Alumni Management',
    'description': """
University Alumni
=================
وحدة الخريجين — تحتوي على:

- الخريج (uni.alumni.member)
  * سجل خريج لكل طالب متخرج، مرتبط بسجل الطالب الأصلي
  * بيانات التوظيف الحالية، روابط التواصل الاجتماعي
  * حالة العضوية (نشط/غير نشط/فخري/مدى الحياة)
  * إمكانية أن يكون موجهاً أو متطوعاً
  * ارتباط بالتبرعات والفعاليات والشبكات والمسار المهني

- الفعاليات (uni.alumni.event)
  * دورة حياة كاملة (draft → announced → registration_open → ongoing → completed/cancelled)
  * فعاليات حضورية أو أونلاين
  * تسجيل الحضور والأقصى للمشاركين والرسوم

- التبرعات (uni.alumni.donation)
  * تبرعات نقدية أو عينية أو أسهم
  * أغراض متعددة (منح دراسية، أبحاث، مبانٍ، معدات...)
  * تبرعات متكررة ومجهولة
  * إرسال إشعار الشكر

- الشبكات المهنية (uni.alumni.network)
  * شبكات حسب الصناعة أو المنطقة أو الاهتمام
  * منسق وأعضاء وتواريخ الاجتماعات

- التوظيف (uni.alumni.career)
  * المسار المهني لكل خريج
  * نوع التوظيف، النطاق الراتبي، المهارات
  * منع تكرار الوظيفة الحالية لكل خريج

This module is part of the University ERP and provides the complete
alumni management workflow.
    """,
    'author': 'University ERP Team',
    'website': 'https://example.com',
    'category': 'University/Alumni',
    'license': 'LGPL-3',
    'depends': ['university_student'],
    'data': [
        # Security
        'security/ir.model.access.csv',
        # Data
        'data/ir_sequence_data.xml',
        # Views
        'views/uni_alumni_member_views.xml',
        'views/uni_alumni_event_views.xml',
        'views/uni_alumni_donation_views.xml',
        'views/uni_alumni_network_views.xml',
        'views/uni_alumni_career_views.xml',
        'views/menu_views.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
    'sequence': 26,
}
