# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestUniHousingRoom(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
        })
        cls.room_type = cls.env['uni.housing.room.type'].create({
            'name': 'Double Room',
            'code': 'DBL',
            'capacity': 2,
            'monthly_rent': 800.0,
        })
        cls.building = cls.env['uni.housing.building'].create({
            'name': 'Test Building',
            'code': 'BLDR001',
            'university_id': cls.university.id,
        })
        cls.room = cls.env['uni.housing.room'].create({
            'name': '101',
            'building_id': cls.building.id,
            'room_type_id': cls.room_type.id,
            'floor': 1,
        })

    def test_create_room(self):
        self.assertTrue(self.room)
        self.assertEqual(self.room.capacity, 2)

    def test_room_available(self):
        self.assertTrue(self.room.is_available)
        self.assertEqual(self.room.occupied_beds, 0)

    def test_room_code_unique(self):
        with self.assertRaises(Exception):
            self.env['uni.housing.room'].create({
                'name': '101',
                'building_id': self.building.id,
                'room_type_id': self.room_type.id,
            })
