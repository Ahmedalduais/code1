# -*- coding: utf-8 -*-
from datetime import date
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestUniInternshipCertificate(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
        })
        cls.entity = cls.env['uni.internship.training.entity'].create({
            'name': 'Cert Entity',
            'entity_code': 'CER001',
            'entity_type': 'private',
        })
        cls.course = cls.env['uni.course'].create({
            'name': 'Cert Course',
            'code': 'CERT001',
            'university_id': cls.university.id,
        })
        cls.internship = cls.env['uni.internship'].create({
            'course_id': cls.course.id,
            'training_entity_id': cls.entity.id,
        })
        cls.person = cls.env['uni.person'].create({
            'name': 'Cert Student',
            'email': 'certstudent@test.com',
        })
        cls.student = cls.env['uni.student'].create({
            'person_id': cls.person.id,
            'university_id': cls.university.id,
        })
        cls.certificate = cls.env['uni.internship.certificate'].create({
            'student_id': cls.student.id,
            'internship_id': cls.internship.id,
            'training_entity_id': cls.entity.id,
            'grade': 'excellent',
            'grade_percentage': 95.0,
            'hours_completed': 240.0,
        })

    def test_create_certificate(self):
        self.assertTrue(self.certificate)
        self.assertTrue(self.certificate.name)
        self.assertTrue(self.certificate.certificate_number)
        self.assertTrue(self.certificate.verification_code)
        self.assertEqual(self.certificate.state, 'draft')

    def test_certificate_workflow(self):
        self.certificate.action_issue()
        self.assertEqual(self.certificate.state, 'issued')
        self.certificate.action_verify()
        self.assertEqual(self.certificate.state, 'verified')
        self.assertTrue(self.certificate.is_verified)

    def test_certificate_revoke(self):
        self.certificate.action_issue()
        self.certificate.action_revoke()
        self.assertEqual(self.certificate.state, 'revoked')

    def test_certificate_grade_selection(self):
        for grade in ('excellent', 'very_good', 'good', 'pass', 'fail'):
            self.certificate.grade = grade
            self.assertEqual(self.certificate.grade, grade)
