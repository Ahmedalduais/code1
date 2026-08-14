# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestUniResearchCollaboration(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.collaboration = cls.env['uni.research.collaboration'].create({
            'name': 'Test Collaboration',
            'collaboration_type': 'joint_research',
        })

    def test_create_collaboration(self):
        self.assertTrue(self.collaboration)
        self.assertEqual(self.collaboration.state, 'draft')

    def test_collaboration_workflow(self):
        self.collaboration.action_approve()
        self.assertEqual(self.collaboration.state, 'active')

    def test_collaboration_type(self):
        for ctype in ('joint_research', 'staff_exchange', 'student_exchange',
                       'joint_supervision', 'other'):
            self.collaboration.collaboration_type = ctype
            self.assertEqual(self.collaboration.collaboration_type, ctype)
