# -*- coding: utf-8 -*-
from datetime import date, timedelta
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestUniInternship(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
        })
        cls.entity = cls.env['uni.internship.training.entity'].create({
            'name': 'Intern Entity',
            'entity_code': 'IE001',
            'entity_type': 'private',
        })
        cls.course = cls.env['uni.course'].create({
            'name': 'Internship Course',
            'code': 'IC001',
            'university_id': cls.university.id,
        })
        cls.internship = cls.env['uni.internship'].create({
            'course_id': cls.course.id,
            'internship_type': 'summer',
            'training_entity_id': cls.entity.id,
            'start_date': date.today(),
            'end_date': date.today() + timedelta(days=90),
            'hours_required': 240,
        })

    def test_create_internship(self):
        self.assertTrue(self.internship)
        self.assertEqual(self.internship.internship_state, 'planning')

    def test_internship_workflow(self):
        self.internship.action_start()
        self.assertEqual(self.internship.internship_state, 'ongoing')
        self.internship.action_complete()
        self.assertEqual(self.internship.internship_state, 'completed')
        self.assertTrue(self.internship.end_date)

    def test_internship_fail(self):
        self.internship.action_start()
        self.internship.action_fail()
        self.assertEqual(self.internship.internship_state, 'failed')

    def test_internship_cancel(self):
        self.internship.action_cancel()
        self.assertEqual(self.internship.internship_state, 'cancelled')

    def test_internship_planning(self):
        self.internship.action_start()
        self.internship.action_planning()
        self.assertEqual(self.internship.internship_state, 'planning')

    def test_internship_type_selection(self):
        for itype in ('summer', 'semester', 'year_long', 'capstone', 'graduation'):
            self.internship.internship_type = itype
            self.assertEqual(self.internship.internship_type, itype)
