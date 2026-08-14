# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestUniLmsContent(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
        })
        cls.course = cls.env['uni.course'].create({
            'name': 'Content Course',
            'code': 'CC101',
            'university_id': cls.university.id,
        })
        cls.lms_course = cls.env['uni.lms.course'].create({
            'course_id': cls.course.id,
        })
        cls.content = cls.env['uni.lms.content'].create({
            'lms_course_id': cls.lms_course.id,
            'content_type': 'video',
            'title': 'Introduction Video',
            'duration': 0.5,
        })

    def test_create_content(self):
        self.assertTrue(self.content)
        self.assertEqual(self.content.content_type, 'video')

    def test_content_workflow(self):
        self.content.action_publish()
        self.assertEqual(self.content.state, 'published')
        self.content.action_archive()
        self.assertEqual(self.content.state, 'archived')

    def test_content_type_selection(self):
        for ctype in ('video', 'document', 'presentation', 'link',
                       'text', 'image', 'audio', 'other'):
            self.content.content_type = ctype
            self.assertEqual(self.content.content_type, ctype)
