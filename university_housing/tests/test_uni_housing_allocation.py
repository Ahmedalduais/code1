# -*- coding: utf-8 -*-
from datetime import date
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import UserError, ValidationError


@tagged('post_install', '-at_install')
class TestUniHousingAllocation(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
        })
        cls.room_type = cls.env['uni.housing.room.type'].create({
            'name': 'Single',
            'code': 'ALCSGL',
            'capacity': 1,
            'monthly_rent': 500.0,
        })
        cls.building = cls.env['uni.housing.building'].create({
            'name': 'Alloc Building',
            'code': 'ALCBLD',
            'university_id': cls.university.id,
        })
        cls.room = cls.env['uni.housing.room'].create({
            'name': 'A101',
            'building_id': cls.building.id,
            'room_type_id': cls.room_type.id,
        })
        cls.person = cls.env['uni.person'].create({
            'name': 'Alloc Student',
            'email': 'alloc@test.com',
        })
        cls.student = cls.env['uni.student'].create({
            'person_id': cls.person.id,
            'university_id': cls.university.id,
        })
        cls.allocation = cls.env['uni.housing.allocation'].create({
            'student_id': cls.student.id,
            'room_id': cls.room.id,
            'allocation_date': date.today(),
            'monthly_rent': 500.0,
        })

    def test_create_allocation(self):
        self.assertTrue(self.allocation)
        self.assertTrue(self.allocation.name)
        self.assertEqual(self.allocation.state, 'draft')

    def test_allocation_check_in(self):
        self.allocation.action_check_in()
        self.assertEqual(self.allocation.state, 'active')
        self.assertTrue(self.allocation.check_in_date)

    def test_allocation_check_out(self):
        self.allocation.action_check_in()
        self.allocation.action_check_out()
        self.assertEqual(self.allocation.state, 'completed')
        self.assertTrue(self.allocation.actual_check_out_date)

    def test_allocation_cancel(self):
        self.allocation.action_cancel()
        self.assertEqual(self.allocation.state, 'cancelled')

    def test_allocation_cancel_from_active(self):
        self.allocation.action_check_in()
        self.allocation.action_cancel()
        self.assertEqual(self.allocation.state, 'cancelled')

    def test_allocation_draft_from_cancelled(self):
        self.allocation.action_cancel()
        self.allocation.action_draft()
        self.assertEqual(self.allocation.state, 'draft')

    def test_allocation_check_in_wrong_state(self):
        self.allocation.action_check_in()
        with self.assertRaises(UserError):
            self.allocation.action_check_in()

    def test_allocation_check_out_wrong_state(self):
        with self.assertRaises(UserError):
            self.allocation.action_check_out()
