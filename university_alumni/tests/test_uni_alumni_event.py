# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestUniAlumniEvent(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.event = cls.env['uni.alumni.event'].create({
            'title': 'Annual Reunion',
            'event_type': 'reunion',
            'start_date': datetime.now() + timedelta(days=30),
            'end_date': datetime.now() + timedelta(days=30, hours=3),
            'location': 'Main Campus Hall',
        })

    def test_create_event(self):
        self.assertTrue(self.event)
        self.assertTrue(self.event.name)
        self.assertEqual(self.event.state, 'draft')

    def test_event_workflow(self):
        self.event.action_announce()
        self.assertEqual(self.event.state, 'announced')
        self.event.action_open_registration()
        self.assertEqual(self.event.state, 'registration_open')

    def test_event_type_selection(self):
        for etype in ('reunion', 'networking', 'career_fair', 'fundraising',
                       'social', 'conference', 'workshop', 'other'):
            self.event.event_type = etype
            self.assertEqual(self.event.event_type, etype)
