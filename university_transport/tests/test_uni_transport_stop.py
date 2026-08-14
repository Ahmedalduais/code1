# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestUniTransportStop(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
        })
        cls.vehicle = cls.env['uni.transport.vehicle'].create({
            'name': 'Stop Bus',
            'plate_number': 'STP-001',
            'university_id': cls.university.id,
            'vehicle_type': 'bus',
            'capacity': 40,
        })
        cls.route = cls.env['uni.transport.route'].create({
            'name': 'Stop Route',
            'university_id': cls.university.id,
            'start_point': 'A',
            'end_point': 'B',
            'vehicle_id': cls.vehicle.id,
        })
        cls.stop = cls.env['uni.transport.stop'].create({
            'name': 'Stop 1',
            'route_id': cls.route.id,
            'sequence': 1,
            'is_pickup_point': True,
        })

    def test_create_stop(self):
        self.assertTrue(self.stop)
        self.assertTrue(self.stop.name)

    def test_stop_pickup(self):
        self.assertTrue(self.stop.is_pickup_point)
