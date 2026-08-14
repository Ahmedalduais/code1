# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestUniProjectDefense(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env['uni.project'].create({
            'name': 'Defense Test Project',
        })
        cls.defense = cls.env['uni.project.defense'].create({
            'name': 'Final Defense',
            'project_id': cls.project.id,
            'defense_type': 'final',
            'date': datetime.now() + timedelta(days=14),
            'location': 'Hall A',
        })

    def test_create_defense(self):
        self.assertTrue(self.defense)
        self.assertTrue(self.defense.name)
        self.assertEqual(self.defense.state, 'scheduled')

    def test_defense_workflow(self):
        self.defense.action_start()
        self.assertEqual(self.defense.state, 'ongoing')
        self.defense.grade = 85.0
        self.defense.decision = 'pass'
        self.defense.action_complete()
        self.assertEqual(self.defense.state, 'completed')

    def test_defense_type_selection(self):
        for dtype in ('proposal', 'midterm', 'final'):
            self.defense.defense_type = dtype
            self.assertEqual(self.defense.defense_type, dtype)
