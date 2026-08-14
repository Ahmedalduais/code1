# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError


@tagged('post_install', '-at_install')
class TestUniPortalStudent(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
        })
        cls.person = cls.env['uni.person'].create({
            'name': 'Test Student Person',
            'email': 'student@test.com',
        })
        cls.student = cls.env['uni.student'].create({
            'person_id': cls.person.id,
            'university_id': cls.university.id,
            'student_code': 'STU001',
        })
        cls.portal_student = cls.env['uni.portal.student'].create({
            'student_id': cls.student.id,
            'portal_user_id': cls.env.ref('base.user_admin').id,
        })

    def test_create_portal_student(self):
        self.assertTrue(self.portal_student)
        self.assertEqual(self.portal_student.student_id, self.student)

    def test_portal_student_reference(self):
        self.portal_student.name = 'New'
        self.portal_student._compute_name()
        self.assertTrue(self.portal_student.name)

    def test_portal_student_state(self):
        self.assertEqual(self.portal_student.state, 'draft')
        self.portal_student.action_activate()
        self.assertEqual(self.portal_student.state, 'active')
        self.portal_student.action_deactivate()
        self.assertEqual(self.portal_student.state, 'inactive')

    def test_portal_student_unique_student(self):
        with self.assertRaises(Exception):
            self.env['uni.portal.student'].create({
                'student_id': self.student.id,
            })
