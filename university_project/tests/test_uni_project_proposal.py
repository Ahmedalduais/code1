# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from datetime import datetime, timedelta


@tagged('post_install', '-at_install')
class TestUniProjectProposal(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
        })
        cls.theme = cls.env['uni.project.theme'].create({
            'name': 'AI',
            'code': 'AI',
        })
        cls.proposal = cls.env['uni.project.proposal'].create({
            'title': 'AI Chatbot',
            'university_id': cls.university.id,
            'theme_id': cls.theme.id,
            'abstract': 'Build an AI chatbot',
            'objectives': 'Develop NLP capabilities',
        })

    def test_create_proposal(self):
        self.assertTrue(self.proposal)
        self.assertTrue(self.proposal.name)
        self.assertEqual(self.proposal.state, 'draft')

    def test_proposal_workflow(self):
        self.proposal.action_submit()
        self.assertEqual(self.proposal.state, 'submitted')
        self.assertTrue(self.proposal.submission_date)
        self.proposal.action_approve()
        self.assertEqual(self.proposal.state, 'approved')

    def test_proposal_reject(self):
        self.proposal.action_submit()
        self.proposal.action_reject()
        self.assertEqual(self.proposal.state, 'rejected')
