# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from datetime import date, timedelta


@tagged('post_install', '-at_install')
class TestUniResearchConference(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.conference = cls.env['uni.research.conference'].create({
            'name': 'Test Conference',
            'start_date': date.today() + timedelta(days=30),
            'end_date': date.today() + timedelta(days=32),
        })

    def test_create_conference(self):
        self.assertTrue(self.conference)
        self.assertEqual(self.conference.state, 'draft')

    def test_conference_workflow(self):
        self.conference.action_confirm()
        self.assertEqual(self.conference.state, 'confirmed')
        self.conference.action_complete()
        self.assertEqual(self.conference.state, 'completed')

    def test_conference_dates(self):
        self.assertTrue(self.conference.start_date < self.conference.end_date)
