# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError


@tagged('post_install', '-at_install')
class TestUniProjectTeam(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
        })
        cls.course = cls.env['uni.course'].create({
            'name': 'Graduation Project',
            'code': 'GP001',
            'university_id': cls.university.id,
        })
        cls.project = cls.env['uni.project'].create({
            'course_id': cls.course.id if hasattr(cls.env['uni.project'], 'course_id') else False,
            'name': 'Test Project',
            'max_team_size': 3,
        })
        cls.person1 = cls.env['uni.person'].create({
            'name': 'Team Leader',
            'email': 'leader@test.com',
        })
        cls.student1 = cls.env['uni.student'].create({
            'person_id': cls.person1.id,
            'university_id': cls.university.id,
        })
        cls.person2 = cls.env['uni.person'].create({
            'name': 'Team Member',
            'email': 'member@test.com',
        })
        cls.student2 = cls.env['uni.student'].create({
            'person_id': cls.person2.id,
            'university_id': cls.university.id,
        })

    def test_create_team(self):
        team = self.env['uni.project.team'].create({
            'name': 'Alpha Team',
            'project_id': self.project.id,
            'team_leader_id': self.student1.id,
        })
        self.assertTrue(team)
        self.assertEqual(team.status, 'active')

    def test_team_dissolve(self):
        team = self.env['uni.project.team'].create({
            'name': 'Beta Team',
            'project_id': self.project.id,
            'team_leader_id': self.student1.id,
        })
        team.action_dissolve()
        self.assertEqual(team.status, 'dissolved')
        self.assertTrue(team.dissolution_date)

    def test_team_reactivate(self):
        team = self.env['uni.project.team'].create({
            'name': 'Gamma Team',
            'project_id': self.project.id,
            'team_leader_id': self.student1.id,
        })
        team.action_dissolve()
        team.action_reactivate()
        self.assertEqual(team.status, 'active')

    def test_team_unique_name(self):
        self.env['uni.project.team'].create({
            'name': 'Unique Team',
            'project_id': self.project.id,
            'team_leader_id': self.student1.id,
        })
        with self.assertRaises(Exception):
            self.env['uni.project.team'].create({
                'name': 'Unique Team',
                'project_id': self.project.id,
                'team_leader_id': self.student2.id,
            })
