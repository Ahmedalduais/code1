# -*- coding: utf-8 -*-
{
    'name': 'University LMS',
    'version': '19.0.1.0.0',
    'summary': 'University ERP — Learning Management System',
    'description': """
University LMS
==============
وحدة نظام إدارة التعلم الإلكتروني — تحتوي على:
- المقررات الإلكترونية (uni.lms.course)
- المحتوى التعليمي (uni.lms.content)
- الواجبات والتسليمات (uni.lms.assignment / uni.lms.assignment.submission)
- الاختبارات الإلكترونية والأسئلة والمحاولات (uni.lms.quiz / .question / .attempt)
- المنتديات والمشاركات (uni.lms.forum / uni.lms.forum.post)
- تقدم الطلاب (uni.lms.progress)

This Tier-3 optional module adds a full Learning Management System on top
of the University ERP. It provides:
- Course content publishing (videos, documents, links, text)
- Assignments with file/text/URL submissions and late penalty rules
- Quizzes with multiple question types and graded/practice modes
- Discussion forums with pinned/locked threads
- Per-student progress tracking (completion %, scores, time spent)
- Optional public website pages for course catalog and student dashboard

NOTE: This module depends ONLY on university_curriculum + website (per spec).
Student/Instructor references are stored as free-text Char fields
(student_name, student_code, faculty_name, moderator_name, grade_letter).
If ``university_student`` is also installed, the LMS website controllers will
auto-fill these fields from the logged-in user's student record; otherwise
the user must enter them manually at enrollment time.
""",
    'author': 'University ERP Team',
    'website': 'https://example.com',
    'category': 'University/LMS',
    'license': 'LGPL-3',
    'depends': [
        'university_curriculum',
        'website',
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
        # Data
        'data/ir_sequence_data.xml',
        # Backend views
        'views/uni_lms_course_views.xml',
        'views/uni_lms_content_views.xml',
        'views/uni_lms_assignment_views.xml',
        'views/uni_lms_quiz_views.xml',
        'views/uni_lms_forum_views.xml',
        'views/uni_lms_progress_views.xml',
        # Website templates
        'views/templates/lms_layout.xml',
        'views/templates/lms_course_list.xml',
        'views/templates/lms_course_detail.xml',
        # Menu
        'views/menu_views.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
    'sequence': 27,
}
