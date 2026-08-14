# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestUniLibraryAuthor(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = cls.env['uni.library.author'].create({
            'name': 'Test Author',
            'nationality': 'Test Country',
        })

    def test_create_author(self):
        self.assertTrue(self.author)
        self.assertEqual(self.author.name, 'Test Author')

    def test_author_active(self):
        self.assertTrue(self.author.active)
