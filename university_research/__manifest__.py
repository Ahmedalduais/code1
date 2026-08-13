# -*- coding: utf-8 -*-
{
    'name': 'University Research',
    'version': '19.0.1.0.0',
    'summary': 'University ERP — Scientific Research Management',
    'description': """
University Research
===================
وحدة إدارة البحث العلمي — تحتوي على:
- المشاريع البحثية (uni.research.project)
- المنشورات العلمية (uni.research.publication)
- المجلات العلمية (uni.research.journal)
- المؤتمرات (uni.research.conference)
- المنح البحثية (uni.research.grant)
- لجنة الأخلاقيات (uni.research.ethics)
- التعاون البحثي (uni.research.collaboration)
  * تتبّع تعاون الباحثين الداخليين والشركاء الخارجيين على مشروع بحثي
  * سير العمل: draft → proposed → active → completed/terminated/cancelled

This module is part of the University ERP and provides full research
lifecycle management: from project proposal, ethics review, funding
through grants, to publication tracking with journal/conference metadata,
citation counts, indexing databases and impact factor monitoring, plus
internal/external research collaboration tracking.
    """,
    'author': 'University ERP Team',
    'website': 'https://example.com',
    'category': 'University/Research',
    'license': 'LGPL-3',
    'depends': ['university_faculty'],
    'data': [
        # Security
        'security/ir.model.access.csv',
        # Data
        'data/ir_sequence_data.xml',
        # Views
        'views/uni_research_journal_views.xml',
        'views/uni_research_conference_views.xml',
        'views/uni_research_project_views.xml',
        'views/uni_research_publication_views.xml',
        'views/uni_research_grant_views.xml',
        'views/uni_research_ethics_views.xml',
        'views/uni_research_collaboration_views.xml',
        'views/menu_views.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
    'sequence': 22,
}
