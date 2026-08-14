# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError


@tagged('post_install', '-at_install')
class TestUniSelfStudy(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
        })
        cls.self_study = cls.env['uni.self.study'].create({
            'name': 'Self Study Report',
            'university_id': cls.university.id,
        })

    def test_create_self_study(self):
        self.assertTrue(self.self_study)
        self.assertEqual(self.self_study.state, 'draft')

    def test_self_study_workflow(self):
        self.self_study.action_start()
        self.assertEqual(self.self_study.state, 'in_progress')
        self.self_study.action_submit()
        self.assertEqual(self.self_study.state, 'submitted')

    def test_self_study_accept(self):
        self.self_study.action_start()
        self.self_study.action_submit()
        self.self_study.action_accept()
        self.assertEqual(self.self_study.state, 'accepted')

    def test_self_study_reject(self):
        self.self_study.action_start()
        self.self_study.action_submit()
        self.self_study.action_reject()
        self.assertEqual(self.self_study.state, 'rejected')
