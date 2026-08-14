# -*- coding: utf-8 -*-
from datetime import date
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestUniTransportAttendance(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
        })
        cls.vehicle = cls.env['uni.transport.vehicle'].create({
            'name': 'Att Bus',
            'plate_number': 'ATT-001',
            'university_id': cls.university.id,
            'vehicle_type': 'bus',
            'capacity': 40,
        })
        cls.route = cls.env['uni.transport.route'].create({
            'name': 'Att Route',
            'university_id': cls.university.id,
            'start_point': 'A',
            'end_point': 'B',
            'vehicle_id': cls.vehicle.id,
        })
        cls.attendance = cls.env['uni.transport.attendance'].create({
            'date': date.today(),
            'route_id': cls.route.id,
            'direction': 'morning_pickup',
        })

    def test_create_attendance(self):
        self.assertTrue(self.attendance)
        self.assertTrue(self.attendance.name)

    def test_attendance_direction(self):
        for d in ('morning_pickup', 'afternoon_drop', 'night_drop', 'other'):
            self.attendance.direction = d
            self.assertEqual(self.attendance.direction, d)

    def test_attendance_route(self):
        self.assertEqual(self.attendance.route_id, self.route)
