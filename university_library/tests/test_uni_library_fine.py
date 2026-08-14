# -*- coding: utf-8 -*-
from datetime import date
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestUniLibraryFine(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fine = cls.env['uni.library.fine'].create({
            'borrower_name': 'Test Borrower',
            'amount': 25.0,
            'issue_date': date.today(),
            'reason': 'Late return',
        })

    def test_create_fine(self):
        self.assertTrue(self.fine)
        self.assertEqual(self.fine.amount, 25.0)

    def test_fine_paid(self):
        self.assertFalse(self.fine.is_paid)
        self.fine.action_pay()
        self.assertTrue(self.fine.is_paid)

    def test_fine_cancel(self):
        self.fine.action_cancel()
        self.assertEqual(self.fine.state, 'cancelled')
