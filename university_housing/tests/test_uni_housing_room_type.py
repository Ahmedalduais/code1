# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError


@tagged('post_install', '-at_install')
class TestUniHousingRoomType(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.room_type = cls.env['uni.housing.room.type'].create({
            'name': 'Single Room',
            'code': 'SGL',
            'capacity': 1,
            'monthly_rent': 500.0,
        })

    def test_create_room_type(self):
        self.assertTrue(self.room_type)
        self.assertEqual(self.room_type.capacity, 1)

    def test_room_type_active(self):
        self.assertTrue(self.room_type.active)

    def test_room_type_code_unique(self):
        with self.assertRaises(Exception):
            self.env['uni.housing.room.type'].create({
                'name': 'Duplicate',
                'code': 'SGL',
            })
