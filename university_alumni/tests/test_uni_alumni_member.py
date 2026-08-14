# -*- coding: utf-8 -*-
from datetime import date
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError


@tagged('post_install', '-at_install')
class TestUniAlumniMember(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
        })
        cls.person = cls.env['uni.person'].create({
            'name': 'Alumni Person',
            'email': 'alumni@test.com',
        })
        cls.student = cls.env['uni.student'].create({
            'person_id': cls.person.id,
            'university_id': cls.university.id,
        })
        cls.alumni = cls.env['uni.alumni.member'].create({
            'student_id': cls.student.id,
            'graduation_date': date(2023, 6, 15),
            'degree_received': 'B.Sc. Computer Science',
            'membership_status': 'active',
        })

    def test_create_alumni(self):
        self.assertTrue(self.alumni)
        self.assertTrue(self.alumni.name)

    def test_alumni_graduation_year(self):
        self.assertEqual(self.alumni.graduation_year, 2023)

    def test_alumni_unique_student(self):
        with self.assertRaises(Exception):
            self.env['uni.alumni.member'].create({
                'student_id': self.student.id,
            })

    def test_alumni_membership_workflow(self):
        self.alumni.action_deactivate()
        self.assertEqual(self.alumni.membership_status, 'inactive')
        self.alumni.action_make_honorary()
        self.assertEqual(self.alumni.membership_status, 'honorary')
        self.alumni.action_make_lifetime()
        self.assertEqual(self.alumni.membership_status, 'lifetime')
        self.alumni.action_activate()
        self.assertEqual(self.alumni.membership_status, 'active')

    def test_alumni_employment(self):
        self.alumni.write({
            'current_employment_status': 'employed',
            'current_job_title': 'Software Engineer',
            'current_employer': 'Tech Corp',
        })
        self.assertEqual(self.alumni.current_job_title, 'Software Engineer')
