# -*- coding: utf-8 -*-
from datetime import date, timedelta
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import UserError, ValidationError


@tagged('post_install', '-at_install')
class TestUniLibraryBorrow(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.book = cls.env['uni.library.book'].create({
            'name': 'Borrow Test Book',
            'total_copies': 2,
        })
        cls.borrow = cls.env['uni.library.borrow'].create({
            'book_id': cls.book.id,
            'borrower_type': 'student',
            'student_name': 'John Doe',
            'borrow_date': date.today() - timedelta(days=10),
            'due_date': date.today() + timedelta(days=4),
        })

    def test_create_borrow(self):
        self.assertTrue(self.borrow)
        self.assertTrue(self.borrow.name)
        self.assertEqual(self.borrow.state, 'borrowed')

    def test_borrow_return(self):
        self.borrow.action_return()
        self.assertEqual(self.borrow.state, 'returned')
        self.assertTrue(self.borrow.actual_return_date)

    def test_borrow_renew(self):
        old_due = self.borrow.due_date
        self.borrow.action_renew()
        self.assertEqual(self.borrow.renewed_count, 1)
        self.assertTrue(self.borrow.due_date > old_due)

    def test_borrow_cancel(self):
        self.borrow.action_cancel()
        self.assertEqual(self.borrow.state, 'cancelled')

    def test_borrow_lost(self):
        self.borrow.action_mark_lost()
        self.assertEqual(self.borrow.state, 'lost')

    def test_borrower_name_computed(self):
        self.assertEqual(self.borrow.borrower_name, 'John Doe')

    def test_due_date_constraint(self):
        with self.assertRaises(ValidationError):
            self.env['uni.library.borrow'].create({
                'book_id': self.book.id,
                'borrower_type': 'student',
                'student_name': 'Jane',
                'borrow_date': date.today(),
                'due_date': date.today() - timedelta(days=1),
            })

    def test_max_renewals(self):
        self.borrow.max_renewals = 1
        self.borrow.action_renew()
        with self.assertRaises(UserError):
            self.borrow.action_renew()
