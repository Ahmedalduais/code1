# -*- coding: utf-8 -*-
{
    'name': 'University Gradebook',
    'version': '19.0.1.0.0',
    'summary': 'University ERP — Gradebook & Transcripts',
    'description': """
University Gradebook
====================
وحدة سجل الدرجات — تحتوي على:
- سجل الدرجات الرئيسي (uni.gradebook)
  * ربط بمقرر وفصل دراسي ونظام درجات
  * خطوط الطلاب (uni.gradebook.line)
  * إدخالات الدرجات الفردية (uni.gradebook.entry)
  * الدرجة النهائية لكل طالب (uni.gradebook.final)
- حساب المعدل (uni.gpa.calculation)
  * وراثة كلاسيكية من uni.grading.calculator
  * حساب المعدل الفصلي والتراكمي
- الكشف الأكاديمي (uni.transcript)
  * إنشاء كشف رسمي للطالب
  * تقرير QWeb PDF بكامل البيانات الأكاديمية

This module is part of the University ERP and provides complete
gradebook management, GPA calculation and official transcripts.
    """,
    'author': 'University ERP Team',
    'website': 'https://example.com',
    'category': 'University/Gradebook',
    'license': 'LGPL-3',
    'depends': ['university_student', 'university_curriculum', 'university_grading'],
    'data': [
        # Security
        'security/ir.model.access.csv',
        # Data
        'data/ir_sequence_data.xml',
        # Views
        'views/uni_gradebook_views.xml',
        'views/uni_gradebook_line_views.xml',
        'views/uni_gradebook_entry_views.xml',
        'views/uni_gradebook_final_views.xml',
        'views/uni_gpa_calculation_views.xml',
        'views/uni_transcript_views.xml',
        'views/uni_gradebook_approval_views.xml',
        'views/menu_views.xml',
        # Reports
        'reports/transcript_report.xml',
        'reports/transcript_report_template.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
    'sequence': 18,
}
