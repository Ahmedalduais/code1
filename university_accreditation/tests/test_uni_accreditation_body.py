# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError


@tagged('post_install', '-at_install')
class TestUniAccreditationBody(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.body = cls.env['uni.accreditation.body'].create({
            'name': 'Test Accreditation Body',
            'code': 'TAB001',
        })

    def test_create_body(self):
        self.assertTrue(self.body)
        self.assertEqual(self.body.name, 'Test Accreditation Body')

    def test_body_active(self):
        self.assertTrue(self.body.is_active)

    def test_body_code_unique(self):
        with self.assertRaises(Exception):
            self.env['uni.accreditation.body'].create({
                'name': 'Duplicate Body',
                'code': 'TAB001',
            })

    def test_body_fields(self):
        self.body.write({
            'country_id': False,
            'website': 'https://test.com',
            'contact_email': 'contact@test.com',
        })
        self.assertEqual(self.body.website, 'https://test.com')
