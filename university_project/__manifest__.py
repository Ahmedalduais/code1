# -*- coding: utf-8 -*-
{
    'name': 'University Project',
    'version': '19.0.1.0.0',
    'summary': 'University ERP — Graduation Projects Management',
    'description': """
University Project
==================
وحدة مشاريع التخرج — تدعم:
- مشاريع فردية وجماعية (فرق متعددة الطلاب)
- هيكل الفرق: uni.project.team + uni.project.team.member
- تتبع مساهمة كل طالب (contribution_percentage)
- التقييم المختلط (جماعي + فردي + مختلط)
- سير عمل كامل: مقترح ← موافقة ← تنفيذ ← مناقشة ← تقييم ← نشر
- 16 نموذج متكامل

This module manages graduation projects with full team support,
allowing multiple students to collaborate on a single project with
individual and team-based evaluation options.
    """,
    'author': 'University ERP Team',
    'website': 'https://example.com',
    'category': 'University/Project',
    'license': 'LGPL-3',
    'depends': [
        'university_curriculum',
        'university_faculty',
        'university_student',
        'university_research',
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
        # Data
        'data/ir_sequence_data.xml',
        'data/project_data.xml',
        # Views — ordered: parent models before child models
        'views/uni_project_theme_views.xml',
        'views/uni_project_proposal_views.xml',
        'views/uni_project_approval_views.xml',
        'views/uni_project_views.xml',
        'views/uni_project_team_views.xml',
        'views/uni_project_team_member_views.xml',
        'views/uni_project_supervisor_views.xml',
        'views/uni_project_timeline_views.xml',
        'views/uni_project_milestone_views.xml',
        'views/uni_project_deliverable_views.xml',
        'views/uni_project_meeting_views.xml',
        'views/uni_project_progress_views.xml',
        'views/uni_project_defense_views.xml',
        'views/uni_project_committee_views.xml',
        'views/uni_project_evaluation_views.xml',
        'views/uni_project_publication_views.xml',
        # Menu (last)
        'views/menu_views.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
    'sequence': 29,
}
