# -*- coding: utf-8 -*-
from datetime import date, timedelta
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import UserError, ValidationError


@tagged('post_install', '-at_install')
class TestUniTransportPass(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
        })
        cls.person = cls.env['uni.person'].create({
            'name': 'Transport Student',
            'email': 'transport@test.com',
        })
        cls.student = cls.env['uni.student'].create({
            'person_id': cls.person.id,
            'university_id': cls.university.id,
        })
        cls.vehicle = cls.env['uni.transport.vehicle'].create({
            'name': 'Pass Bus',
            'plate_number': 'PS-001',
            'university_id': cls.university.id,
            'vehicle_type': 'bus',
            'capacity': 40,
        })
        cls.route = cls.env['uni.transport.route'].create({
            'name': 'Pass Route',
            'university_id': cls.university.id,
            'start_point': 'A',
            'end_point': 'B',
            'vehicle_id': cls.vehicle.id,
        })
        cls.pass_rec = cls.env['uni.transport.pass'].create({
            'student_id': cls.student.id,
            'route_id': cls.route.id,
            'pass_type': 'semester',
            'start_date': date.today(),
            'end_date': date.today() + timedelta(days=180),
            'amount': 200.0,
        })

    def test_create_pass(self):
        self.assertTrue(self.pass_rec)
        self.assertTrue(self.pass_rec.name)
        self.assertEqual(self.pass_rec.state, 'draft')

    def test_pass_activate(self):
        self.pass_rec.action_activate()
        self.assertEqual(self.pass_rec.state, 'active')

    def test_pass_suspend(self):
        self.pass_rec.action_activate()
        self.pass_rec.action_suspend()
        self.assertEqual(self.pass_rec.state, 'suspended')

    def test_pass_expire(self):
        self.pass_rec.action_expire()
        self.assertEqual(self.pass_rec.state, 'expired')

    def test_pass_cancel(self):
        self.pass_rec.action_cancel()
        self.assertEqual(self.pass_rec.state, 'cancelled')

    def test_pass_dates_constraint(self):
        with self.assertRaises(ValidationError):
            self.env['uni.transport.pass'].create({
                'student_id': self.student.id,
                'route_id': self.route.id,
                'pass_type': 'semester',
                'start_date': date.today(),
                'end_date': date.today() - timedelta(days=1),
            })

    def test_pass_amount_positive(self):
        with self.assertRaises(Exception):
            self.env['uni.transport.pass'].create({
                'student_id': self.student.id,
                'route_id': self.route.id,
                'pass_type': 'semester',
                'start_date': date.today(),
                'end_date': date.today() + timedelta(days=180),
                'amount': -100.0,
            })
