# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestUniInternshipStudent(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
        })
        cls.person = cls.env['uni.person'].create({
            'name': 'Intern Student',
            'email': 'internstudent@test.com',
        })
        cls.student = cls.env['uni.student'].create({
            'person_id': cls.person.id,
            'university_id': cls.university.id,
        })
        cls.intern_student = cls.env['uni.internship.student'].create({
            'student_id': cls.student.id,
        })

    def test_create_intern_student(self):
        self.assertTrue(self.intern_student)
        self.assertEqual(self.intern_student.student_id, self.student)

    def test_intern_student_stats(self):
        self.assertEqual(self.intern_student.total_internships, 0)
        self.assertEqual(self.intern_student.completed_internships, 0)
        self.assertEqual(self.intern_student.total_hours_completed, 0.0)
        self.assertEqual(self.intern_student.average_grade, 0.0)
