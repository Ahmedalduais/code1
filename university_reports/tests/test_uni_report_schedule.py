# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestUniReportSchedule(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.template = cls.env['uni.report.template'].create({
            'name': 'Schedule Test Report',
            'code': 'STR-001',
            'report_type': 'student',
            'model_name': 'uni.student',
        })
        cls.builder = cls.env['uni.report.builder'].create({
            'template_id': cls.template.id,
            'output_format': 'screen',
        })
        cls.schedule = cls.env['uni.report.schedule'].create({
            'report_builder_id': cls.builder.id,
            'frequency': 'daily',
            'next_run_date': datetime.now() + timedelta(days=1),
        })

    def test_create_schedule(self):
        self.assertTrue(self.schedule)
        self.assertTrue(self.schedule.name)
        self.assertEqual(self.schedule.state, 'draft')

    def test_schedule_workflow(self):
        self.schedule.action_activate()
        self.assertEqual(self.schedule.state, 'active')
        self.schedule.action_pause()
        self.assertEqual(self.schedule.state, 'paused')

    def test_schedule_frequency(self):
        for freq in ('daily', 'weekly', 'monthly', 'quarterly', 'annual'):
            self.schedule.frequency = freq
            self.assertEqual(self.schedule.frequency, freq)
