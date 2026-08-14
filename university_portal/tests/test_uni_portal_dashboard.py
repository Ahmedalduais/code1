# -*- coding: utf-8 -*-
import json
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError


@tagged('post_install', '-at_install')
class TestUniPortalDashboard(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.env.ref('base.user_admin')
        cls.dashboard = cls.env['uni.portal.dashboard'].create({
            'name': 'Test Dashboard',
            'user_id': cls.user.id,
            'dashboard_type': 'student',
            'is_default': True,
        })

    def test_create_dashboard(self):
        self.assertTrue(self.dashboard)
        self.assertTrue(self.dashboard.configuration)
        config = json.loads(self.dashboard.configuration)
        self.assertIn('widgets', config)

    def test_dashboard_type_selection(self):
        for dtype in ('student', 'faculty', 'admin'):
            self.dashboard.dashboard_type = dtype
            self.assertEqual(self.dashboard.dashboard_type, dtype)

    def test_single_default_constraint(self):
        with self.assertRaises(ValidationError):
            self.env['uni.portal.dashboard'].create({
                'name': 'Duplicate Default',
                'user_id': self.user.id,
                'dashboard_type': 'student',
                'is_default': True,
            })

    def test_action_mark_accessed(self):
        self.dashboard.action_mark_accessed()
        self.assertEqual(self.dashboard.access_count, 1)
        self.assertTrue(self.dashboard.last_accessed)

    def test_action_reset_dashboard(self):
        self.dashboard.action_reset_dashboard()
        config = json.loads(self.dashboard.configuration)
        self.assertIn('widgets', config)

    def test_get_dashboard_data(self):
        data = self.dashboard.get_dashboard_data()
        self.assertIn('id', data)
        self.assertIn('name', data)
        self.assertIn('configuration', data)
        self.assertIn('stats', data)

    def test_get_or_create_for_user(self):
        dash = self.env['uni.portal.dashboard'].get_or_create_for_user(
            self.user, 'student')
        self.assertTrue(dash)
        self.assertEqual(dash.user_id, self.user)
