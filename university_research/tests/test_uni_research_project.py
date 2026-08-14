# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from datetime import date, timedelta


@tagged('post_install', '-at_install')
class TestUniResearchProject(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env['uni.research.project'].create({
            'name': 'Test Research Project',
            'start_date': date.today(),
            'end_date': date.today() + timedelta(days=365),
        })

    def test_create_project(self):
        self.assertTrue(self.project)
        self.assertEqual(self.project.state, 'proposal')

    def test_project_workflow(self):
        self.project.action_submit()
        self.assertEqual(self.project.state, 'submitted')
        self.project.action_approve()
        self.assertEqual(self.project.state, 'approved')
        self.project.action_start()
        self.assertEqual(self.project.state, 'active')

    def test_project_complete(self):
        self.project.action_submit()
        self.project.action_approve()
        self.project.action_start()
        self.project.action_complete()
        self.assertEqual(self.project.state, 'completed')
