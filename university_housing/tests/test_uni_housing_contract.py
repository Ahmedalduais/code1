# -*- coding: utf-8 -*-
from datetime import date, timedelta
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestUniHousingContract(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
        })
        cls.person = cls.env['uni.person'].create({
            'name': 'Contract Student',
            'email': 'contract@test.com',
        })
        cls.student = cls.env['uni.student'].create({
            'person_id': cls.person.id,
            'university_id': cls.university.id,
        })
        cls.contract = cls.env['uni.housing.contract'].create({
            'name': 'Test Contract',
            'student_id': cls.student.id,
            'start_date': date.today(),
            'end_date': date.today() + timedelta(days=365),
            'monthly_amount': 500.0,
        })

    def test_create_contract(self):
        self.assertTrue(self.contract)
        self.assertEqual(self.contract.state, 'draft')

    def test_contract_workflow(self):
        self.contract.action_approve()
        self.assertEqual(self.contract.state, 'approved')
        self.contract.action_sign()
        self.assertEqual(self.contract.state, 'active')

    def test_contract_terminate(self):
        self.contract.action_approve()
        self.contract.action_sign()
        self.contract.action_terminate()
        self.assertEqual(self.contract.state, 'terminated')
