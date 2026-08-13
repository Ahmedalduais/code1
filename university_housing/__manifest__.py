# -*- coding: utf-8 -*-
{
    'name': 'University Housing',
    'version': '19.0.1.0.0',
    'summary': 'University ERP — Housing Management',
    'description': """
University Housing
==================
وحدة إدارة السكن الجامعي — تحتوي على:

- أنواع الغرف (uni.housing.room.type)
  * تعريف أنواع الغرف (مزدوجة، مفردة، جناح...) مع السعة والإيجار الشهري
  * خصائص كل نوع: تكييف، مطبخ، حمام، إنترنت، أثاث
  * عدّاد الغرف المرتبطة بكل نوع
- المباني (uni.housing.building)
  * بيانات كاملة للمباني: النوع، العنوان، الطوابق، عدد الغرف
  * المرافق: موقف سيارات، مغسلة، صالة رياضية، أمن، واي فاي
  * حالة المبنى (متاح/صيانة/مغلق) مع مشرف وموقع
  * صورة المبنى + قائمة الغرف + إحصائيات الإشغال
- الغرف (uni.housing.room)
  * بيانات كل غرفة: المبنى، النوع، الطابق، السعة، الإيجار
  * حساب الأسرة المشغولة والمتاحة تلقائياً من التخصيصات
  * حالة الغرف (متاح/ممتلئ/صيانة/مغلق)
  * دعم Kanban مجمّع حسب الحالة
- التخصيص (uni.housing.allocation)
  * تخصيص غرفة لطالب مع تواريخ الدخول والخروج
  * سير عمل: مسودة → نشط → مكتمل → ملغى
  * منع التخصيص المكرر النشط للطالب نفسه
  * ربط اختياري بعقد السكن
- العقود (uni.housing.contract)
  * عقود سكن طلابية: فصلي/سنوي/شهري/مخصص
  * مبالغ وإيداع وتكرار الدفع
  * توقيع الطالب وتوقيع الموظف وتواريخ التوقيع
  * سير عمل: مسودة → نشط → منتهي/مفسوخ
- الصيانة (uni.housing.maintenance)
  * طلبات صيانة للمباني والغرف
  * أنواع: كهرباء، سباكة، نجارة، دهان، تكييف، تنظيف، إنشائي، أخرى
  * أولويات: منخفضة/عادية/عالية/عاجلة
  * سير عمل كامل: جديد → مُكلّف → مجدول → قيد التنفيذ → مكتمل/ملغى
  * تقييم الأداء (1-5) وملاحظات العمل

This module is part of the University ERP and provides complete
housing management including buildings, rooms, room types, allocations,
contracts, and maintenance requests.
    """,
    'author': 'University ERP Team',
    'website': 'https://example.com',
    'category': 'University/Housing',
    'license': 'LGPL-3',
    'depends': ['university_core', 'university_student'],
    'data': [
        # Security
        'security/ir.model.access.csv',
        # Data
        'data/ir_sequence_data.xml',
        # Views
        'views/uni_housing_room_type_views.xml',
        'views/uni_housing_building_views.xml',
        'views/uni_housing_room_views.xml',
        'views/uni_housing_allocation_views.xml',
        'views/uni_housing_contract_views.xml',
        'views/uni_housing_maintenance_views.xml',
        'views/menu_views.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
    'sequence': 24,
}
