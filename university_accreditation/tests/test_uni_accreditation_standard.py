# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestUniAccreditationStandard(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.standard = cls.env['uni.accreditation.standard'].create({
            'name': 'Teaching Quality Standard',
            'code': 'STD001',
            'category': 'teaching',
            'max_score': 100.0,
        })

    def test_create_standard(self):
        self.assertTrue(self.standard)
        self.assertEqual(self.standard.max_score, 100.0)

    def test_standard_active(self):
        self.assertTrue(self.standard.is_active)

    def test_standard_category(self):
        for cat in ('teaching', 'research', 'facilities', 'governance',
                     'student_support', 'community', 'other'):
            self.standard.category = cat
            self.assertEqual(self.standard.category, cat)
