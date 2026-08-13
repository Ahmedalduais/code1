# -*- coding: utf-8 -*-
{
    'name': 'University Core',
    'version': '19.0.1.0.0',
    'summary': 'University ERP — Core Foundation Module',
    'description': """
University Core
===============
النواة الأساسية لنظام الجامعة — تحتوي على:
- الكيانات التنظيمية (جامعة، فرع، كلية، قسم، برنامج)
- السنة الأكاديمية والفصول الدراسية
- نموذج الأشخاص الأساسي والميكزن المشترك
- الإعدادات المرنة (مدمجة من uni_config)

This module is mandatory and provides the foundation for all other
University ERP modules.
    """,
    'author': 'University ERP Team',
    'website': 'https://example.com',
    'category': 'University/Core',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'contacts'],
    'data': [
        # Security
        'security/university_security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/ir_sequence_data.xml',
        'data/university_data.xml',
        # Views
        'views/uni_university_views.xml',
        'views/uni_branch_views.xml',
        'views/uni_college_views.xml',
        'views/uni_department_views.xml',
        'views/uni_program_views.xml',
        'views/uni_academic_year_views.xml',
        'views/uni_academic_term_views.xml',
        'views/uni_academic_term_type_views.xml',
        'views/uni_person_views.xml',
        'views/uni_academic_standing_views.xml',
        'views/uni_honors_level_views.xml',
        'views/res_config_settings_views.xml',
        'views/menu_views.xml',
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
    'sequence': 10,
}
