# -*- coding: utf-8 -*-
{
    'name': 'University Faculty',
    'version': '19.0.1.0.0',
    'summary': 'University ERP — Faculty Management',
    'description': """
University Faculty
==================
وحدة إدارة أعضاء هيئة التدريس — تحتوي على:
- نموذج عضو هيئة التدريس (uni.faculty)
  * وراثة تفويض من uni.person
  * ربط Many2one بـ hr.employee (التصميم المُصحح)
- الرتب الأكاديمية (uni.faculty.rank)
- التكليفات التدريسية (uni.faculty.assignment)
- العبء التدريسي (uni.faculty.load)
- المنشورات العلمية (uni.faculty.publication)
- اللجان (uni.committee) وأعضاء اللجان (uni.committee.member)

This module is part of the University ERP and provides faculty lifecycle
management including ranks, teaching assignments, load tracking,
publications and committee membership.
    """,
    'author': 'University ERP Team',
    'website': 'https://example.com',
    'category': 'University/Faculty',
    'license': 'LGPL-3',
    'depends': ['university_core', 'hr'],
    'data': [
        # Security
        'security/ir.model.access.csv',
        # Data
        'data/ir_sequence_data.xml',
        'data/faculty_ranks_data.xml',
        # Views
        'views/uni_faculty_rank_views.xml',
        'views/uni_faculty_views.xml',
        'views/uni_faculty_assignment_views.xml',
        'views/uni_faculty_load_views.xml',
        'views/uni_faculty_publication_views.xml',
        'views/uni_committee_views.xml',
        'views/uni_faculty_contract_views.xml',
        'views/menu_views.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': True,
    'sequence': 13,
}
