# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestUniLmsQuiz(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
        })
        cls.course = cls.env['uni.course'].create({
            'name': 'Quiz Course',
            'code': 'QC101',
            'university_id': cls.university.id,
        })
        cls.lms_course = cls.env['uni.lms.course'].create({
            'course_id': cls.course.id,
        })
        cls.quiz = cls.env['uni.lms.quiz'].create({
            'lms_course_id': cls.lms_course.id,
            'title': 'Midterm Quiz',
            'quiz_type': 'graded',
            'max_score': 100.0,
            'attempts_allowed': 3,
        })

    def test_create_quiz(self):
        self.assertTrue(self.quiz)
        self.assertTrue(self.quiz.name)

    def test_quiz_workflow(self):
        self.quiz.action_publish()
        self.assertEqual(self.quiz.state, 'published')
        self.quiz.action_close()
        self.assertEqual(self.quiz.state, 'closed')

    def test_quiz_type(self):
        for qtype in ('practice', 'graded', 'pre_test', 'post_test', 'survey'):
            self.quiz.quiz_type = qtype
            self.assertEqual(self.quiz.quiz_type, qtype)
