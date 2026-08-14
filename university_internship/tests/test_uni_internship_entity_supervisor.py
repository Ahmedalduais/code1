# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestUniInternshipEntitySupervisor(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.entity = cls.env['uni.internship.training.entity'].create({
            'name': 'Supervisor Entity',
            'entity_code': 'SE001',
            'entity_type': 'private',
        })
        cls.supervisor = cls.env['uni.internship.entity.supervisor'].create({
            'name': 'John Supervisor',
            'entity_id': cls.entity.id,
            'position': 'Senior Engineer',
            'department': 'R&D',
        })

    def test_create_supervisor(self):
        self.assertTrue(self.supervisor)
        self.assertTrue(self.supervisor.name)

    def test_supervisor_active(self):
        self.assertTrue(self.supervisor.is_active)

    def test_supervisor_unique(self):
        with self.assertRaises(Exception):
            self.env['uni.internship.entity.supervisor'].create({
                'name': 'John Supervisor',
                'entity_id': self.entity.id,
            })
