# -*- coding: utf-8 -*-
from datetime import date, timedelta
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestUniInternshipOpportunity(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
        })
        cls.entity = cls.env['uni.internship.training.entity'].create({
            'name': 'Opportunity Entity',
            'entity_code': 'OE001',
            'entity_type': 'private',
        })
        cls.opportunity = cls.env['uni.internship.opportunity'].create({
            'title': 'Software Developer Intern',
            'entity_id': cls.entity.id,
            'university_id': cls.university.id,
            'description': 'Develop web applications',
            'start_date': date.today() + timedelta(days=30),
            'end_date': date.today() + timedelta(days=120),
            'max_students': 5,
        })

    def test_create_opportunity(self):
        self.assertTrue(self.opportunity)
        self.assertTrue(self.opportunity.name)
        self.assertEqual(self.opportunity.state, 'draft')

    def test_opportunity_workflow(self):
        self.opportunity.action_publish()
        self.assertEqual(self.opportunity.state, 'published')
        self.opportunity.action_close()
        self.assertEqual(self.opportunity.state, 'closed')

    def test_opportunity_paid(self):
        self.opportunity.is_paid = True
        self.opportunity.monthly_stipend = 1500.0
        self.assertTrue(self.opportunity.is_paid)
