# -*- coding: utf-8 -*-
from datetime import date
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestUniResearchPublication(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.publication = cls.env['uni.research.publication'].create({
            'title': 'Test Publication',
            'publication_type': 'journal',
            'publication_date': date.today(),
        })

    def test_create_publication(self):
        self.assertTrue(self.publication)
        self.assertTrue(self.publication.title)

    def test_publication_type(self):
        for ptype in ('journal', 'conference', 'book', 'chapter', 'other'):
            self.publication.publication_type = ptype
            self.assertEqual(self.publication.publication_type, ptype)

    def test_publication_status(self):
        self.publication.action_publish()
        self.assertEqual(self.publication.state, 'published')
