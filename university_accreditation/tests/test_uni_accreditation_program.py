# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError


@tagged('post_install', '-at_install')
class TestUniAccreditationProgram(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
        })
        cls.body = cls.env['uni.accreditation.body'].create({
            'name': 'Test Body',
            'code': 'TB001',
        })
        cls.standard = cls.env['uni.accreditation.standard'].create({
            'name': 'Test Standard',
            'code': 'TS001',
            'category': 'teaching',
        })
        cls.program = cls.env['uni.accreditation.program'].create({
            'name': 'CS Accreditation',
            'university_id': cls.university.id,
            'body_id': cls.body.id,
            'program_name': 'Computer Science',
        })

    def test_create_program(self):
        self.assertTrue(self.program)
        self.assertEqual(self.program.state, 'pending')

    def test_program_workflow(self):
        self.program.action_start()
        self.assertEqual(self.program.state, 'in_progress')
        self.program.action_grant()
        self.assertEqual(self.program.state, 'granted')
        self.program.action_probation()
        self.assertEqual(self.program.state, 'probation')
        self.program.action_revoke()
        self.assertEqual(self.program.state, 'revoked')

    def test_program_status(self):
        self.program.action_start()
        self.program.action_grant()
        self.assertTrue(self.program.accreditation_date)
        self.assertTrue(self.program.expiry_date)

    def test_program_unique(self):
        with self.assertRaises(Exception):
            self.env['uni.accreditation.program'].create({
                'name': 'Duplicate',
                'university_id': self.university.id,
                'body_id': self.body.id,
                'program_name': 'Computer Science',
            })
