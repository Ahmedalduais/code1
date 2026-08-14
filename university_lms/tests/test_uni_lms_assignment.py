# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo.fields import Datetime
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestUniLmsAssignment(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
        })
        cls.course = cls.env['uni.course'].create({
            'name': 'Assignment Course',
            'code': 'AC101',
            'university_id': cls.university.id,
        })
        cls.lms_course = cls.env['uni.lms.course'].create({
            'course_id': cls.course.id,
        })
        cls.assignment = cls.env['uni.lms.assignment'].create({
            'lms_course_id': cls.lms_course.id,
            'title': 'Homework 1',
            'description': '<p>Complete exercises</p>',
            'max_score': 100.0,
            'due_date': Datetime.now() + timedelta(days=7),
        })

    def test_create_assignment(self):
        self.assertTrue(self.assignment)
        self.assertTrue(self.assignment.name)

    def test_assignment_workflow(self):
        self.assignment.action_publish()
        self.assertEqual(self.assignment.state, 'published')
        self.assignment.action_close()
        self.assertEqual(self.assignment.state, 'closed')

    def test_assignment_type(self):
        for atype in ('individual', 'group'):
            self.assignment.assignment_type = atype
            self.assertEqual(self.assignment.assignment_type, atype)
