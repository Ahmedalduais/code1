# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestUniInternshipTrainingEntity(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.entity = cls.env['uni.internship.training.entity'].create({
            'name': 'Tech Corp',
            'entity_code': 'TC001',
            'entity_type': 'private',
            'industry_sector': 'IT',
        })

    def test_create_entity(self):
        self.assertTrue(self.entity)
        self.assertEqual(self.entity.entity_type, 'private')

    def test_entity_type_selection(self):
        for etype in ('private', 'government', 'non_profit', 'educational',
                       'research', 'other'):
            self.entity.entity_type = etype
            self.assertEqual(self.entity.entity_type, etype)

    def test_entity_approval(self):
        self.entity.action_approve()
        self.assertTrue(self.entity.is_approved)
        self.assertTrue(self.entity.approval_date)
