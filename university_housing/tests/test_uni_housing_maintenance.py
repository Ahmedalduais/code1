# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestUniHousingMaintenance(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
        })
        cls.room_type = cls.env['uni.housing.room.type'].create({
            'name': 'Maint Room Type',
            'code': 'MTYP',
            'capacity': 1,
        })
        cls.building = cls.env['uni.housing.building'].create({
            'name': 'Maint Building',
            'code': 'MBLD',
            'university_id': cls.university.id,
        })
        cls.room = cls.env['uni.housing.room'].create({
            'name': 'M101',
            'building_id': cls.building.id,
            'room_type_id': cls.room_type.id,
        })
        cls.maintenance = cls.env['uni.housing.maintenance'].create({
            'name': 'Fix AC',
            'room_id': cls.room.id,
            'issue_type': 'electrical',
            'priority': 'high',
            'description': 'AC not working',
        })

    def test_create_maintenance(self):
        self.assertTrue(self.maintenance)
        self.assertEqual(self.maintenance.state, 'reported')

    def test_maintenance_workflow(self):
        self.maintenance.action_assign()
        self.assertEqual(self.maintenance.state, 'in_progress')
        self.maintenance.action_complete()
        self.assertEqual(self.maintenance.state, 'completed')

    def test_maintenance_cancel(self):
        self.maintenance.action_cancel()
        self.assertEqual(self.maintenance.state, 'cancelled')
