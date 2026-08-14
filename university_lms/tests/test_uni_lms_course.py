# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestUniLmsCourse(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
        })
        cls.course = cls.env['uni.course'].create({
            'name': 'Introduction to CS',
            'code': 'CS101',
            'university_id': cls.university.id,
        })
        cls.lms_course = cls.env['uni.lms.course'].create({
            'course_id': cls.course.id,
            'faculty_name': 'Dr. Smith',
            'description': 'Online CS course',
        })

    def test_create_lms_course(self):
        self.assertTrue(self.lms_course)
        self.assertTrue(self.lms_course.name)

    def test_lms_course_enrollment(self):
        self.assertTrue(self.lms_course.enrollment_open)

    def test_lms_course_workflow(self):
        self.lms_course.action_publish()
        self.assertEqual(self.lms_course.state, 'published')
        self.lms_course.action_close()
        self.assertEqual(self.lms_course.state, 'closed')
