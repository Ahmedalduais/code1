# -*- coding: utf-8 -*-
{
    'name': 'University Student',
    'version': '19.0.1.0.0',
    'summary': 'University ERP — Student Records Management',
    'description': """
University Student
==================
وحدة إدارة سجلات الطلاب — تحتوي على:
- نموذج الطالب (uni.student)
  * وراثة تفويض من uni.person
  * ربط بـ uni.program / uni.department / uni.college / uni.branch
  * تتبع المعدل التراكمي (cumulative_gpa) والساعات المكتسبة والموقف الأكاديمي
- التسجيل الأكاديمي (uni.student.enrollment + uni.student.enrollment.line)
  * تسجيل الطالب لفصل دراسي وربط المقررات بخطوط مسجل قابلة للتعديل
- حالات الطالب (uni.student.status)
- التحويلات (uni.student.transfer)
- الوثائق (uni.student.document)
- الحضور والغياب (uni.attendance + uni.attendance.line)

This module is part of the University ERP and provides complete
student lifecycle management including enrollment, transfers,
document tracking, attendance and academic standing.
    """,
    'author': 'University ERP Team',
    'website': 'https://example.com',
    'category': 'University/Student',
    'license': 'LGPL-3',
    'depends': ['university_core', 'university_curriculum'],
    'data': [
        # Security
        'security/ir.model.access.csv',
        # Data
        'data/ir_sequence_data.xml',
        'data/student_status_data.xml',
        # Views
        'views/uni_student_views.xml',
        'views/uni_student_enrollment_views.xml',
        'views/uni_student_status_views.xml',
        'views/uni_student_transfer_views.xml',
        'views/uni_student_document_views.xml',
        'views/uni_attendance_views.xml',
        'views/uni_student_advisor_views.xml',
        'views/menu_views.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': True,
    'sequence': 14,
}
