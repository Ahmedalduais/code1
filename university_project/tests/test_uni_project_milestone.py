# -*- coding: utf-8 -*-
from datetime import date, timedelta
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestUniProjectMilestone(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env['uni.project'].create({
            'name': 'Milestone Test Project',
        })
        cls.milestone = cls.env['uni.project.milestone'].create({
            'name': 'Design Phase',
            'project_id': cls.project.id,
            'milestone_type': 'design',
            'planned_date': date.today() + timedelta(days=30),
        })

    def test_create_milestone(self):
        self.assertTrue(self.milestone)
        self.assertFalse(self.milestone.is_completed)

    def test_milestone_complete(self):
        self.milestone.action_complete()
        self.assertTrue(self.milestone.is_completed)
        self.assertTrue(self.milestone.completed_date)

    def test_milestone_type_selection(self):
        for mtype in ('proposal', 'requirements', 'design', 'prototype',
                       'implementation', 'testing', 'documentation',
                       'deployment', 'defense', 'other'):
            self.milestone.milestone_type = mtype
            self.assertEqual(self.milestone.milestone_type, mtype)
