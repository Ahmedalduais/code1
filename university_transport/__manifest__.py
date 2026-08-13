# -*- coding: utf-8 -*-
{
    'name': 'University Transport',
    'version': '19.0.1.0.0',
    'summary': 'University ERP — Transport Management',
    'description': """
University Transport
===================
وحدة إدارة النقل الجامعي — تحتوي على:

- المركبات (uni.transport.vehicle)
  * بيانات كاملة للمركبة: اللوحة، النوع، الماركة، الموديل، السنة، اللون، VIN
  * سعة المركبة ونوع الوقود واستهلاك الوقود والعداد الحالي
  * تاريخ الشراء وسعره وتاريخ انتهاء التأمين والترخيص
  * سائق مخصص (hr.employee) وصورة للمركبة
  * حالة المركبة (متاحة/قيد الاستخدام/صيانة/متقاعدة) مع workflow كامل
  * ربط مع الخطوط (Many2many)
- الخطوط (uni.transport.route)
  * نقطة بداية ونهاية مع مسافة ومدة تقديرية
  * أوقات المغادرة والوصول (float_time) وأيام التشغيل
  * مركبة وسائق مخصصان
  * حالة الخط (مسودة/نشط/معلق/مغلق)
- المحطات (uni.transport.stop)
  * محطات لكل خط مع تسلسل وإحداثيات جغرافية
  * أوقات الوصول والمغادرة لكل محطة
  * تصنيف المحطة (نقطة ركوب/نقطة إنزال/كلاهما)
- بطاقات النقل (uni.transport.pass)
  * بطاقة نقل للطالب على خط معين
  * أنواع البطاقات (فصلي/سنوي/شهري/ذهاب فقط/ذهاب وعودة)
  * تواريخ الصلاحية ومحطة الركوب والإنزال
  * باركود ومبلغ ومدفوع وصورة الطالب
  * تسجيل الاستخدام بعداد وآخر استخدام
  * حالة البطاقة (مسودة/نشطة/منتهية/معلقة/ملغاة)
- حضور النقل (uni.transport.attendance)
  * سجل حضور يومي لخط ومركبة وسائق
  * اتجاه الرحلة (صباحية/ظهرية/مسائية/أخرى)
  * خطوط الحضور لكل بطاقة مع حالة الحضور
  * حساب المجاميع تلقائياً (الإجمالي/الحاضر/الغائب)
  * ملء الخطوط تلقائياً من بطاقات الخط النشطة

This module is part of the University ERP and provides complete
transport management including vehicles, routes, stops, passes and
daily attendance tracking.
    """,
    'author': 'University ERP Team',
    'website': 'https://example.com',
    'category': 'University/Transport',
    'license': 'LGPL-3',
    'depends': ['university_core', 'university_student'],
    'data': [
        # Security
        'security/ir.model.access.csv',
        # Data
        'data/ir_sequence_data.xml',
        # Views
        'views/uni_transport_vehicle_views.xml',
        'views/uni_transport_route_views.xml',
        'views/uni_transport_stop_views.xml',
        'views/uni_transport_pass_views.xml',
        'views/uni_transport_attendance_views.xml',
        'views/menu_views.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
    'sequence': 25,
}
