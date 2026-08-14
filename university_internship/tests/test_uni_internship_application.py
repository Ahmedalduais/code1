# -*- coding: utf-8 -*-
from datetime import date, timedelta
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestUniInternshipApplication(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
        })
        cls.entity = cls.env['uni.internship.training.entity'].create({
            'name': 'App Entity',
            'entity_code': 'AE001',
            'entity_type': 'private',
        })
        cls.opportunity = cls.env['uni.internship.opportunity'].create({
            'title': 'Dev Intern',
            'entity_id': cls.entity.id,
            'university_id': cls.university.id,
            'description': 'Dev work',
            'start_date': date.today() + timedelta(days=30),
            'end_date': date.today() + timedelta(days=120),
        })
        cls.person = cls.env['uni.person'].create({
            'name': 'Applicant Person',
            'email': 'applicant@test.com',
        })
        cls.student = cls.env['uni.student'].create({
            'person_id': cls.person.id,
            'university_id': cls.university.id,
        })
        cls.application = cls.env['uni.internship.application'].create({
            'student_id': cls.student.id,
            'opportunity_id': cls.opportunity.id,
        })

    def test_create_application(self):
        self.assertTrue(self.application)
        self.assertTrue(self.application.name)
        self.assertEqual(self.application.status, 'draft')

    def test_application_workflow(self):
        self.application.action_submit()
        self.assertEqual(self.application.status, 'submitted')
        self.application.action_accept()
        self.assertEqual(self.application.status, 'accepted')

    def test_application_reject(self):
        self.application.action_submit()
        self.application.action_reject()
        self.assertEqual(self.application.status, 'rejected')
