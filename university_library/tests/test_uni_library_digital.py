# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestUniLibraryDigital(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.digital = cls.env['uni.library.digital'].create({
            'name': 'Digital Resource',
            'resource_type': 'ebook',
            'url': 'https://example.com/book',
        })

    def test_create_digital(self):
        self.assertTrue(self.digital)
        self.assertTrue(self.digital.name)

    def test_digital_type(self):
        for rtype in ('ebook', 'audiobook', 'video', 'article', 'database', 'other'):
            self.digital.resource_type = rtype
            self.assertEqual(self.digital.resource_type, rtype)

    def test_digital_active(self):
        self.assertTrue(self.digital.active)
