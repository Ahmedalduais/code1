# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError


@tagged('post_install', '-at_install')
class TestUniLmsProgress(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
        })
        cls.course = cls.env['uni.course'].create({
            'name': 'Progress Course',
            'code': 'PC101',
            'university_id': cls.university.id,
        })
        cls.lms_course = cls.env['uni.lms.course'].create({
            'course_id': cls.course.id,
        })
        cls.progress = cls.env['uni.lms.progress'].create({
            'lms_course_id': cls.lms_course.id,
            'student_name': 'John Doe',
            'student_code': 'STU101',
        })

    def test_create_progress(self):
        self.assertTrue(self.progress)
        self.assertTrue(self.progress.name)
        self.assertEqual(self.progress.state, 'enrolled')

    def test_progress_workflow(self):
        self.progress.action_drop()
        self.assertEqual(self.progress.state, 'dropped')
        self.progress.action_reactivate()
        self.assertEqual(self.progress.state, 'in_progress')
        self.progress.action_complete()
        self.assertEqual(self.progress.state, 'completed')
        self.assertEqual(self.progress.completion_percentage, 100.0)

    def test_progress_update(self):
        self.progress.update_progress(content_completed=5, time_spent_hours=2.0)
        self.assertEqual(self.progress.content_completed, 5)
        self.assertEqual(self.progress.time_spent_hours, 2.0)
        self.assertEqual(self.progress.state, 'in_progress')

    def test_progress_completion_range(self):
        with self.assertRaises(ValidationError):
            self.progress.completion_percentage = 150.0

    def test_progress_unique_student(self):
        with self.assertRaises(Exception):
            self.env['uni.lms.progress'].create({
                'lms_course_id': self.lms_course.id,
                'student_name': 'Jane Doe',
                'student_code': 'STU101',
            })
