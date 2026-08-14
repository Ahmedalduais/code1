# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError


@tagged('post_install', '-at_install')
class TestUniReportTemplate(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.template = cls.env['uni.report.template'].create({
            'name': 'Student List Report',
            'code': 'STD-LIST',
            'report_type': 'student',
            'model_name': 'uni.student',
            'is_standard': True,
        })

    def test_create_template(self):
        self.assertTrue(self.template)
        self.assertTrue(self.template.name)

    def test_template_type_selection(self):
        for rtype in ('student', 'academic', 'financial', 'statistical',
                       'operational', 'custom'):
            self.template.report_type = rtype
            self.assertEqual(self.template.report_type, rtype)

    def test_template_active(self):
        self.assertTrue(self.template.is_active)
