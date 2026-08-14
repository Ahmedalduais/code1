# -*- coding: utf-8 -*-
from datetime import date
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestUniInternshipLog(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
        })
        cls.entity = cls.env['uni.internship.training.entity'].create({
            'name': 'Log Entity',
            'entity_code': 'LE001',
            'entity_type': 'private',
        })
        cls.course = cls.env['uni.course'].create({
            'name': 'Log Course',
            'code': 'LC001',
            'university_id': cls.university.id,
        })
        cls.internship = cls.env['uni.internship'].create({
            'course_id': cls.course.id,
            'training_entity_id': cls.entity.id,
            'start_date': date.today(),
        })
        cls.person = cls.env['uni.person'].create({
            'name': 'Log Student',
            'email': 'logstudent@test.com',
        })
        cls.student = cls.env['uni.student'].create({
            'person_id': cls.person.id,
            'university_id': cls.university.id,
        })
        cls.log = cls.env['uni.internship.log'].create({
            'internship_id': cls.internship.id,
            'student_id': cls.student.id,
            'hours': 8.0,
            'activity': 'Worked on project',
        })

    def test_create_log(self):
        self.assertTrue(self.log)
        self.assertTrue(self.log.name)
        self.assertEqual(self.log.hours, 8.0)

    def test_log_approved(self):
        self.assertFalse(self.log.is_approved)
        self.log.action_approve_supervisor()
        self.assertTrue(self.log.supervisor_approval)
        self.log.action_approve_entity()
        self.assertTrue(self.log.entity_supervisor_approval)
        self.assertTrue(self.log.is_approved)

    def test_log_unique(self):
        with self.assertRaises(Exception):
            self.env['uni.internship.log'].create({
                'internship_id': self.internship.id,
                'student_id': self.student.id,
                'hours': 4.0,
                'activity': 'Meeting',
                'name': self.log.name,
            })
