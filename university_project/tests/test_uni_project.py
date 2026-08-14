# -*- coding: utf-8 -*-
from datetime import date, timedelta
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestUniProject(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
        })
        cls.course = cls.env['uni.course'].create({
            'name': 'Project Course',
            'code': 'PC001',
            'university_id': cls.university.id,
        })
        cls.theme = cls.env['uni.project.theme'].create({
            'name': 'Web Dev',
            'code': 'WD',
        })
        cls.project = cls.env['uni.project'].create({
            'name': 'Web Application',
            'course_id': cls.course.id,
            'theme_id': cls.theme.id,
            'project_type': 'graduation',
            'start_date': date.today(),
            'expected_end_date': date.today() + timedelta(days=180),
            'max_team_size': 4,
        })

    def test_create_project(self):
        self.assertTrue(self.project)
        self.assertEqual(self.project.state, 'planning')

    def test_project_workflow(self):
        self.project.action_activate()
        self.assertEqual(self.project.state, 'active')
        self.project.action_hold()
        self.assertEqual(self.project.state, 'on_hold')
        self.project.action_activate()
        self.project.action_complete()
        self.assertEqual(self.project.state, 'completed')
        self.assertTrue(self.project.actual_end_date)

    def test_project_defend(self):
        self.project.action_activate()
        self.project.action_complete()
        self.project.action_defended()
        self.assertEqual(self.project.state, 'defended')

    def test_project_publish(self):
        self.project.action_defended()
        self.project.action_publish()
        self.assertEqual(self.project.state, 'published')

    def test_project_cancel(self):
        self.project.action_cancel()
        self.assertEqual(self.project.state, 'cancelled')

    def test_project_plan(self):
        self.project.action_activate()
        self.project.action_plan()
        self.assertEqual(self.project.state, 'planning')

    def test_project_type_selection(self):
        for ptype in ('graduation', 'capstone', 'research', 'industry', 'innovation'):
            self.project.project_type = ptype
            self.assertEqual(self.project.project_type, ptype)

    def test_project_budget(self):
        self.project.budget = 10000.0
        self.assertEqual(self.project.budget, 10000.0)
