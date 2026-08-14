# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestUniLibraryBook(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = cls.env['uni.library.author'].create({
            'name': 'Author',
        })
        cls.category = cls.env['uni.library.category'].create({
            'name': 'Category',
        })
        cls.book = cls.env['uni.library.book'].create({
            'name': 'Test Book',
            'isbn': '978-3-16-148410-0',
            'author_ids': [(6, 0, [cls.author.id])],
            'category_id': cls.category.id,
            'total_copies': 3,
        })

    def test_create_book(self):
        self.assertTrue(self.book)
        self.assertEqual(self.book.total_copies, 3)

    def test_book_available_copies(self):
        self.assertEqual(self.book.available_copies, 3)

    def test_book_isbn_unique(self):
        with self.assertRaises(Exception):
            self.env['uni.library.book'].create({
                'name': 'Duplicate',
                'isbn': '978-3-16-148410-0',
            })

    def test_book_binding_type(self):
        for btype in ('hardcover', 'paperback', 'ebook', 'audio', 'other'):
            self.book.binding_type = btype
            self.assertEqual(self.book.binding_type, btype)

    def test_book_state(self):
        self.assertEqual(self.book.state, 'available')
