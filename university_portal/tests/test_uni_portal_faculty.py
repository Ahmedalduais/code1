# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestUniPortalFaculty(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
        })
        cls.person = cls.env['uni.person'].create({
            'name': 'Test Faculty Person',
            'email': 'faculty@test.com',
        })
        cls.faculty = cls.env['uni.faculty'].create({
            'person_id': cls.person.id,
            'university_id': cls.university.id,
            'faculty_code': 'FAC001',
        })
        cls.portal_faculty = cls.env['uni.portal.faculty'].create({
            'faculty_id': cls.faculty.id,
            'portal_user_id': cls.env.ref('base.user_admin').id,
        })

    def test_create_portal_faculty(self):
        self.assertTrue(self.portal_faculty)
        self.assertEqual(self.portal_faculty.faculty_id, self.faculty)

    def test_portal_faculty_state(self):
        self.assertEqual(self.portal_faculty.state, 'draft')
        self.portal_faculty.action_activate()
        self.assertEqual(self.portal_faculty.state, 'active')

    def test_portal_faculty_deactivate(self):
        self.portal_faculty.action_activate()
        self.portal_faculty.action_deactivate()
        self.assertEqual(self.portal_faculty.state, 'inactive')
