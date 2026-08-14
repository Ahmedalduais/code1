# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestUniLibraryCategory(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.category = cls.env['uni.library.category'].create({
            'name': 'Computer Science',
            'code': 'CS',
        })

    def test_create_category(self):
        self.assertTrue(self.category)
        self.assertEqual(self.category.name, 'Computer Science')

    def test_category_active(self):
        self.assertTrue(self.category.active)
