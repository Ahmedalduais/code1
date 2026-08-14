# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestUniAlumniNetwork(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.network = cls.env['uni.alumni.network'].create({
            'name': 'CS Alumni Network',
            'network_type': 'industry',
            'industry': 'Technology',
        })

    def test_create_network(self):
        self.assertTrue(self.network)
        self.assertTrue(self.network.name)

    def test_network_workflow(self):
        self.network.action_activate()
        self.assertEqual(self.network.state, 'active')
        self.network.action_deactivate()
        self.assertEqual(self.network.state, 'inactive')
        self.network.action_close()
        self.assertEqual(self.network.state, 'closed')

    def test_network_type_selection(self):
        for ntype in ('industry', 'regional', 'academic', 'professional',
                       'special_interest'):
            self.network.network_type = ntype
            self.assertEqual(self.network.network_type, ntype)
