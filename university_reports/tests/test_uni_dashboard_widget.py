# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestUniDashboardWidget(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.env.ref('base.user_admin')
        cls.widget = cls.env['uni.dashboard.widget'].create({
            'name': 'Student Count KPI',
            'code': 'STD-KPI-1',
            'user_id': cls.user.id,
            'widget_type': 'kpi',
            'data_source_model': 'uni.student',
            'data_source_method': 'search_count',
        })

    def test_create_widget(self):
        self.assertTrue(self.widget)
        self.assertTrue(self.widget.name)

    def test_widget_type_selection(self):
        for wtype in ('kpi', 'chart', 'table', 'list', 'calendar', 'gauge', 'counter'):
            self.widget.widget_type = wtype
            self.assertEqual(self.widget.widget_type, wtype)

    def test_widget_active(self):
        self.assertTrue(self.widget.is_active)

    def test_widget_user(self):
        self.assertEqual(self.widget.user_id, self.user)
