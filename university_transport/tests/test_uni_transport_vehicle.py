# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestUniTransportVehicle(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
        })
        cls.vehicle = cls.env['uni.transport.vehicle'].create({
            'name': 'Test Bus',
            'plate_number': 'ABC-1234',
            'university_id': cls.university.id,
            'vehicle_type': 'bus',
            'capacity': 50,
        })

    def test_create_vehicle(self):
        self.assertTrue(self.vehicle)
        self.assertTrue(self.vehicle.name)

    def test_vehicle_state(self):
        self.assertEqual(self.vehicle.state, 'available')
        self.vehicle.action_assign()
        self.assertEqual(self.vehicle.state, 'in_use')

    def test_vehicle_maintenance(self):
        self.vehicle.action_maintenance()
        self.assertEqual(self.vehicle.state, 'maintenance')

    def test_vehicle_retire(self):
        self.vehicle.action_retire()
        self.assertEqual(self.vehicle.state, 'retired')
