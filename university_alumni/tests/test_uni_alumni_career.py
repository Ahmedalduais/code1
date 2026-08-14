# -*- coding: utf-8 -*-
from datetime import date
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestUniAlumniCareer(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
        })
        cls.person = cls.env['uni.person'].create({
            'name': 'Career Person',
            'email': 'career@test.com',
        })
        cls.student = cls.env['uni.student'].create({
            'person_id': cls.person.id,
            'university_id': cls.university.id,
        })
        cls.member = cls.env['uni.alumni.member'].create({
            'student_id': cls.student.id,
        })
        cls.career = cls.env['uni.alumni.career'].create({
            'member_id': cls.member.id,
            'job_title': 'Software Engineer',
            'employer': 'Tech Corp',
            'employment_type': 'full_time',
            'start_date': date(2023, 7, 1),
        })

    def test_create_career(self):
        self.assertTrue(self.career)
        self.assertTrue(self.career.name)
        self.assertEqual(self.career.job_title, 'Software Engineer')

    def test_career_employment_type(self):
        for etype in ('full_time', 'part_time', 'contract', 'internship',
                       'freelance', 'self_employed', 'other'):
            self.career.employment_type = etype
            self.assertEqual(self.career.employment_type, etype)

    def test_career_current(self):
        self.assertTrue(self.career.is_current)
