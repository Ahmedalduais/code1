# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from datetime import date, timedelta


@tagged('post_install', '-at_install')
class TestUniResearchGrant(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.grant = cls.env['uni.research.grant'].create({
            'name': 'Test Grant',
            'amount': 50000.0,
            'start_date': date.today(),
            'end_date': date.today() + timedelta(days=365),
        })

    def test_create_grant(self):
        self.assertTrue(self.grant)
        self.assertEqual(self.grant.amount, 50000.0)

    def test_grant_workflow(self):
        self.grant.action_approve()
        self.assertEqual(self.grant.state, 'approved')
        self.grant.action_activate()
        self.assertEqual(self.grant.state, 'active')

    def test_grant_complete(self):
        self.grant.action_approve()
        self.grant.action_activate()
        self.grant.action_complete()
        self.assertEqual(self.grant.state, 'completed')
