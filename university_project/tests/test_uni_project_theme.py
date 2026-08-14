# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestUniProjectTheme(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.theme = cls.env['uni.project.theme'].create({
            'name': 'Software Engineering',
            'code': 'SE',
        })

    def test_create_theme(self):
        self.assertTrue(self.theme)
        self.assertTrue(self.theme.name)

    def test_theme_code_unique(self):
        with self.assertRaises(Exception):
            self.env['uni.project.theme'].create({
                'name': 'Duplicate Theme',
                'code': 'SE',
            })

    def test_theme_hierarchy(self):
        child = self.env['uni.project.theme'].create({
            'name': 'Web Engineering',
            'code': 'WEB',
            'parent_id': self.theme.id,
        })
        self.assertEqual(child.parent_id, self.theme)
        self.assertIn(child, self.theme.child_ids)
