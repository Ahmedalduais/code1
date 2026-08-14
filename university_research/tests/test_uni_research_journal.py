# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError


@tagged('post_install', '-at_install')
class TestUniResearchJournal(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
        })
        cls.journal = cls.env['uni.research.journal'].create({
            'name': 'Test Journal',
            'code': 'TJ001',
            'university_id': cls.university.id,
            'issn': '1234-5678',
        })

    def test_create_journal(self):
        self.assertTrue(self.journal)
        self.assertTrue(self.journal.name)

    def test_journal_active(self):
        self.assertTrue(self.journal.is_active)

    def test_journal_impact_factor(self):
        self.journal.impact_factor = 3.5
        self.assertEqual(self.journal.impact_factor, 3.5)

    def test_journal_status(self):
        self.journal.action_deactivate()
        self.assertFalse(self.journal.is_active)
