# -*- coding: utf-8 -*-
{
    'name': 'University Accreditation',
    'version': '19.0.1.0.0',
    'summary': 'University ERP — Academic Accreditation',
    'description': """
University Accreditation
========================
وحدة الاعتماد الأكاديمي — تحتوي على:
- جهات الاعتماد (uni.accreditation.body)
  * هيئات الاعتماد الوطنية والإقليمية والدولية والمهنية
- المعايير (uni.accreditation.standard)
  * شجرة هرمية للمعايير مع الأوزان والدرجات الدنيا
- اعتماد البرامج (uni.accreditation.program)
  * اعتماد لكل برنامج دراسي مع خطوط تقييم المعايير
  * خطوط التقييم (uni.accreditation.program.standard)
- تقارير الاعتماد (uni.accreditation.report)
  * تقارير دورية: الدراسة الذاتية / المرحلية / النهائية / الخاصة / السنوية
- الدراسة الذاتية (uni.self.study)
  * وثيقة شاملة لكل برنامج: الرسالة، الرؤية، الأهداف،
    نواتج التعلم، المنهج، الموارد، التحليل الرباعي (SWOT)، خطة التحسين

This module is part of the University ERP and provides comprehensive
academic accreditation management for programs, including self-studies,
reports and standards assessment.
    """,
    'author': 'University ERP Team',
    'website': 'https://example.com',
    'category': 'University/Accreditation',
    'license': 'LGPL-3',
    'depends': [
        'university_core',
        'university_curriculum',
        'university_faculty',
        'university_gradebook',
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
        # Data
        'data/ir_sequence_data.xml',
        # Views
        'views/uni_accreditation_body_views.xml',
        'views/uni_accreditation_standard_views.xml',
        'views/uni_accreditation_program_views.xml',
        'views/uni_accreditation_report_views.xml',
        'views/uni_self_study_views.xml',
        'views/menu_views.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
    'sequence': 21,
}
