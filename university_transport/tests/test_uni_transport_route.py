# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestUniTransportRoute(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
        })
        cls.vehicle = cls.env['uni.transport.vehicle'].create({
            'name': 'Route Bus',
            'plate_number': 'RT-001',
            'university_id': cls.university.id,
            'vehicle_type': 'bus',
            'capacity': 40,
        })
        cls.route = cls.env['uni.transport.route'].create({
            'name': 'North Campus Line',
            'university_id': cls.university.id,
            'start_point': 'Main Gate',
            'end_point': 'North Campus',
            'vehicle_id': cls.vehicle.id,
            'distance_km': 15.0,
        })

    def test_create_route(self):
        self.assertTrue(self.route)
        self.assertEqual(self.route.state, 'draft')

    def test_route_activate(self):
        self.route.action_activate()
        self.assertEqual(self.route.state, 'active')

    def test_route_suspend(self):
        self.route.action_activate()
        self.route.action_suspend()
        self.assertEqual(self.route.state, 'suspended')

    def test_route_close(self):
        self.route.action_activate()
        self.route.action_close()
        self.assertEqual(self.route.state, 'closed')
