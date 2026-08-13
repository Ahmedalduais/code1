# -*- coding: utf-8 -*-
{
    'name': 'University Library',
    'version': '19.0.1.0.0',
    'summary': 'University ERP — Library Management',
    'description': """
University Library
==================
وحدة إدارة المكتبة الجامعية — تحتوي على:

- المؤلفون (uni.library.author)
  * بيانات المؤلفين مع تواريخ الميلاد والوفاة والجنسية والسيرة الذاتية
  * ربط تلقائي بالكتب التي شارك في تأليفها
- التصنيفات (uni.library.category)
  * هرمية تصنيفات مع نظام تصنيف (ديوي / كونجرس / مخصص)
  * أكواد تصنيف لكل فئة
- الكتب (uni.library.book)
  * بيانات كاملة للكتب: ISBN, الناشر، السنة، الطبعة، اللغة، التجليد
  * صورة الغلاف وملف الكتاب الإلكتروني والرابط الرقمي
  * حالة الكتاب (متاح/مستعار بالكامل/مفقود/تالف/محذوف)
  * حساب النسخ المتاحة والمستعارة تلقائياً
- الاستعارات (uni.library.borrow)
  * استعارات للطلاب وأعضاء هيئة التدريس والموظفين والأطراف الخارجية
  * تتبع تاريخ الاستعارة والإرجاع المتوقع والفعلي
  * حساب الغرامات تلقائياً للتأخير مع دعم التجديد
- المستودع الرقمي (uni.library.digital)
  * أطروحات ورسائل ومقالات وأوراق بحثية ومحاضرات
  * مستويات وصول (عام/جامعة فقط/قسم فقط/مقيّد)
  * عدّادات التنزيل والعرض
- الغرامات (uni.library.fine)
  * غرامات التأخير والتلف والفقد
  * سير اعتماد (معلّق → مدفوع → متنازل عنه → ملغى)
  * طرق دفع متعددة

This module is part of the University ERP and provides complete
library management including books, authors, categories, borrowing,
digital repository, and fines.
    """,
    'author': 'University ERP Team',
    'website': 'https://example.com',
    'category': 'University/Library',
    'license': 'LGPL-3',
    'depends': ['university_core'],
    'data': [
        # Security
        'security/ir.model.access.csv',
        # Data
        'data/ir_sequence_data.xml',
        'data/library_data.xml',
        # Views
        'views/uni_library_author_views.xml',
        'views/uni_library_category_views.xml',
        'views/uni_library_book_views.xml',
        'views/uni_library_borrow_views.xml',
        'views/uni_library_digital_views.xml',
        'views/uni_library_fine_views.xml',
        'views/menu_views.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
    'sequence': 23,
}
