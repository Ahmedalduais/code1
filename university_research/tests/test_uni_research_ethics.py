# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestUniResearchEthics(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ethics = cls.env['uni.research.ethics'].create({
            'name': 'Ethics Review',
            'project_name': 'Test Project',
            'risk_level': 'medium',
        })

    def test_create_ethics(self):
        self.assertTrue(self.ethics)
        self.assertEqual(self.ethics.state, 'draft')

    def test_ethics_workflow(self):
        self.ethics.action_submit()
        self.assertEqual(self.ethics.state, 'submitted')
        self.ethics.action_approve()
        self.assertEqual(self.ethics.state, 'approved')

    def test_ethics_risk_level(self):
        for level in ('low', 'medium', 'high'):
            self.ethics.risk_level = level
            self.assertEqual(self.ethics.risk_level, level)
