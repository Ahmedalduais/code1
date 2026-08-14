# -*- coding: utf-8 -*-
from datetime import date
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError


@tagged('post_install', '-at_install')
class TestUniAlumniDonation(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
        })
        cls.person = cls.env['uni.person'].create({
            'name': 'Donor Person',
            'email': 'donor@test.com',
        })
        cls.student = cls.env['uni.student'].create({
            'person_id': cls.person.id,
            'university_id': cls.university.id,
        })
        cls.member = cls.env['uni.alumni.member'].create({
            'student_id': cls.student.id,
        })
        cls.donation = cls.env['uni.alumni.donation'].create({
            'member_id': cls.member.id,
            'amount': 1000.0,
            'donation_date': date.today(),
            'donation_type': 'cash',
            'purpose': 'scholarship',
        })

    def test_create_donation(self):
        self.assertTrue(self.donation)
        self.assertTrue(self.donation.name)
        self.assertEqual(self.donation.amount, 1000.0)

    def test_donation_workflow(self):
        self.donation.action_confirm()
        self.assertEqual(self.donation.state, 'confirmed')
        self.donation.action_receive()
        self.assertEqual(self.donation.state, 'received')

    def test_donation_type_selection(self):
        for dtype in ('cash', 'check', 'bank_transfer', 'in_kind', 'other'):
            self.donation.donation_type = dtype
            self.assertEqual(self.donation.donation_type, dtype)

    def test_donation_thank(self):
        self.donation.action_send_thank_you()
        self.assertTrue(self.donation.thank_you_sent)
