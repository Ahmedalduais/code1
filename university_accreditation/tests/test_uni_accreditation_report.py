# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestUniAccreditationReport(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
        })
        cls.body = cls.env['uni.accreditation.body'].create({
            'name': 'Test Body',
            'code': 'TBR001',
        })
        cls.standard = cls.env['uni.accreditation.standard'].create({
            'name': 'Test Standard',
            'code': 'TSR001',
            'category': 'teaching',
        })
        cls.report = cls.env['uni.accreditation.report'].create({
            'name': 'Annual Report',
            'university_id': cls.university.id,
            'body_id': cls.body.id,
            'standard_id': cls.standard.id,
        })

    def test_create_report(self):
        self.assertTrue(self.report)
        self.assertEqual(self.report.state, 'draft')

    def test_report_workflow(self):
        self.report.action_submit()
        self.assertEqual(self.report.state, 'submitted')
        self.report.action_review()
        self.assertEqual(self.report.state, 'reviewed')

    def test_report_score(self):
        self.report.score = 85.0
        self.assertEqual(self.report.score, 85.0)
