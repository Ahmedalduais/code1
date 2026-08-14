# -*- coding: utf-8 -*-
from datetime import date
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestUniInternshipCompletion(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
        })
        cls.entity = cls.env['uni.internship.training.entity'].create({
            'name': 'Comp Entity',
            'entity_code': 'CE001',
            'entity_type': 'private',
        })
        cls.course = cls.env['uni.course'].create({
            'name': 'Comp Course',
            'code': 'CC001',
            'university_id': cls.university.id,
        })
        cls.internship = cls.env['uni.internship'].create({
            'course_id': cls.course.id,
            'training_entity_id': cls.entity.id,
        })
        cls.person = cls.env['uni.person'].create({
            'name': 'Comp Student',
            'email': 'compstudent@test.com',
        })
        cls.student = cls.env['uni.student'].create({
            'person_id': cls.person.id,
            'university_id': cls.university.id,
        })
        cls.completion = cls.env['uni.internship.completion'].create({
            'internship_id': cls.internship.id,
            'student_id': cls.student.id,
            'hours_completed': 240.0,
            'hours_required': 240.0,
            'final_grade': 90.0,
            'max_grade': 100.0,
        })

    def test_create_completion(self):
        self.assertTrue(self.completion)
        self.assertTrue(self.completion.name)
        self.assertEqual(self.completion.status, 'pending')

    def test_completion_workflow(self):
        self.completion.action_approve()
        self.assertEqual(self.completion.status, 'approved')
        self.assertTrue(self.completion.approved_by)
        self.assertTrue(self.completion.approved_date)
        self.completion.action_complete()
        self.assertEqual(self.completion.status, 'completed')

    def test_completion_reject(self):
        self.completion.action_reject()
        self.assertEqual(self.completion.status, 'rejected')

    def test_completion_percentage(self):
        self.assertEqual(self.completion.completion_percentage, 100.0)
        self.assertEqual(self.completion.grade_percentage, 90.0)
