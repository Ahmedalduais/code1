# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestUniLmsForum(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
        })
        cls.course = cls.env['uni.course'].create({
            'name': 'Forum Course',
            'code': 'FC101',
            'university_id': cls.university.id,
        })
        cls.lms_course = cls.env['uni.lms.course'].create({
            'course_id': cls.course.id,
        })
        cls.forum = cls.env['uni.lms.forum'].create({
            'lms_course_id': cls.lms_course.id,
            'title': 'Course Discussion Forum',
            'forum_type': 'discussion',
        })

    def test_create_forum(self):
        self.assertTrue(self.forum)
        self.assertTrue(self.forum.title)

    def test_forum_workflow(self):
        self.forum.action_activate()
        self.assertEqual(self.forum.state, 'active')
        self.forum.action_archive()
        self.assertEqual(self.forum.state, 'archived')

    def test_forum_type(self):
        for ftype in ('discussion', 'q_and_a', 'announcements', 'general'):
            self.forum.forum_type = ftype
            self.assertEqual(self.forum.forum_type, ftype)
