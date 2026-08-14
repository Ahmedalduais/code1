# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestUniProjectSupervisor(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
        })
        cls.course = cls.env['uni.course'].create({
            'name': 'Supervisor Project',
            'code': 'SP001',
            'university_id': cls.university.id,
        })
        cls.project = cls.env['uni.project'].create({
            'name': 'Supervisor Test',
        })
        cls.person = cls.env['uni.person'].create({
            'name': 'Supervisor Person',
            'email': 'supervisor@test.com',
        })
        cls.faculty = cls.env['uni.faculty'].create({
            'person_id': cls.person.id,
            'university_id': cls.university.id,
            'faculty_code': 'SUP001',
        })
        cls.supervisor = cls.env['uni.project.supervisor'].create({
            'project_id': cls.project.id,
            'faculty_id': cls.faculty.id,
            'supervisor_role': 'primary',
        })

    def test_create_supervisor(self):
        self.assertTrue(self.supervisor)
        self.assertTrue(self.supervisor.name)

    def test_supervisor_role(self):
        for role in ('primary', 'co_supervisor', 'external', 'advisor'):
            self.supervisor.supervisor_role = role
            self.assertEqual(self.supervisor.supervisor_role, role)

    def test_supervisor_unique(self):
        with self.assertRaises(Exception):
            self.env['uni.project.supervisor'].create({
                'project_id': self.project.id,
                'faculty_id': self.faculty.id,
            })
