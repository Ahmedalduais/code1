# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestUniHousingBuilding(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
        })
        cls.building = cls.env['uni.housing.building'].create({
            'name': 'Test Building',
            'code': 'BLD001',
            'university_id': cls.university.id,
            'total_floors': 5,
            'total_rooms': 50,
        })

    def test_create_building(self):
        self.assertTrue(self.building)
        self.assertEqual(self.building.total_floors, 5)

    def test_building_active(self):
        self.assertTrue(self.building.active)

    def test_building_workflow(self):
        self.building.action_maintenance()
        self.assertEqual(self.building.state, 'maintenance')
        self.building.action_open()
        self.assertEqual(self.building.state, 'open')
