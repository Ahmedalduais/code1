# -*- coding: utf-8 -*-
import json
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import UserError, ValidationError


@tagged('post_install', '-at_install')
class TestUniReportBuilder(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.template = cls.env['uni.report.template'].create({
            'name': 'Builder Test Report',
            'code': 'BTR-001',
            'report_type': 'student',
            'model_name': 'uni.student',
        })
        cls.builder = cls.env['uni.report.builder'].create({
            'template_id': cls.template.id,
            'name_custom': 'My Student Report',
            'output_format': 'csv',
            'filters_configuration': '{}',
            'columns_configuration': '[]',
        })

    def test_create_builder(self):
        self.assertTrue(self.builder)
        self.assertTrue(self.builder.name)

    def test_builder_state(self):
        self.builder.action_draft()
        self.assertEqual(self.builder.state, 'draft')
        self.builder.action_set_ready()
        self.assertEqual(self.builder.state, 'ready')

    def test_builder_run(self):
        self.builder.action_run()
        self.assertEqual(self.builder.state, 'completed')
        self.assertTrue(self.builder.last_run_date)

    def test_builder_json_filters(self):
        self.builder.filters_configuration = '{"name": "test"}'
        parsed = self.builder._parse_filters()
        self.assertEqual(parsed['name'], 'test')

    def test_builder_invalid_json(self):
        with self.assertRaises(ValidationError):
            self.builder.filters_configuration = 'not valid json'

    def test_builder_columns_json(self):
        self.builder.columns_configuration = '[{"name": "name", "label": "Name"}]'
        parsed = self.builder._parse_columns()
        self.assertEqual(len(parsed), 1)
