# -*- coding: utf-8 -*-
from datetime import date
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestUniInternshipAttendance(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
        })
        cls.entity = cls.env['uni.internship.training.entity'].create({
            'name': 'Att Entity',
            'entity_code': 'ATE001',
            'entity_type': 'private',
        })
        cls.course = cls.env['uni.course'].create({
            'name': 'Att Course',
            'code': 'ATC001',
            'university_id': cls.university.id,
        })
        cls.internship = cls.env['uni.internship'].create({
            'course_id': cls.course.id,
            'training_entity_id': cls.entity.id,
            'start_date': date.today(),
        })
        cls.person = cls.env['uni.person'].create({
            'name': 'Att Student',
            'email': 'attstudent@test.com',
        })
        cls.student = cls.env['uni.student'].create({
            'person_id': cls.person.id,
            'university_id': cls.university.id,
        })
        cls.attendance = cls.env['uni.internship.attendance'].create({
            'internship_id': cls.internship.id,
            'student_id': cls.student.id,
            'check_in': 8.0,
            'check_out': 16.0,
            'status': 'present',
        })

    def test_create_attendance(self):
        self.assertTrue(self.attendance)
        self.assertTrue(self.attendance.name)

    def test_attendance_hours(self):
        self.assertEqual(self.attendance.hours, 8.0)

    def test_attendance_status(self):
        for status in ('present', 'absent', 'late', 'early_leave', 'excused', 'holiday'):
            self.attendance.status = status
            self.assertEqual(self.attendance.status, status)

    def test_attendance_unique(self):
        with self.assertRaises(Exception):
            self.env['uni.internship.attendance'].create({
                'internship_id': self.internship.id,
                'student_id': self.student.id,
                'check_in': 9.0,
                'check_out': 17.0,
                'status': 'present',
                'date': self.attendance.date,
            })
