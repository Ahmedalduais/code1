# -*- coding: utf-8 -*-
from datetime import date, timedelta

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestUniversity(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test University Partner',
            'is_company': True,
        })
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
            'code': 'TU01',
            'partner_id': cls.partner.id,
        })

    def test_create_university_with_partner(self):
        partner = self.env['res.partner'].create({
            'name': 'Partner With Uni',
            'is_company': True,
        })
        uni = self.env['uni.university'].create({
            'name': 'Partner Uni',
            'code': 'PU01',
            'partner_id': partner.id,
        })
        self.assertEqual(uni.partner_id, partner)
        self.assertTrue(uni.active)

    def test_create_university_without_partner(self):
        uni = self.env['uni.university'].create({
            'name': 'Auto Partner Uni',
            'code': 'AP01',
        })
        self.assertTrue(uni.partner_id)
        self.assertEqual(uni.partner_id.name, 'Auto Partner Uni')
        self.assertTrue(uni.partner_id.is_company)

    def test_code_uniqueness(self):
        with self.assertRaises(Exception):
            self.env['uni.university'].create({
                'name': 'Duplicate Code Uni',
                'code': 'TU01',
            })

    def test_action_view_branches(self):
        action = self.university.action_view_branches()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'uni.branch')
        self.assertIn(('university_id', '=', self.university.id), action['domain'])

    def test_action_view_colleges(self):
        action = self.university.action_view_colleges()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'uni.college')
        self.assertIn(('university_id', '=', self.university.id), action['domain'])

    def test_archive_unarchive(self):
        self.university.action_archive()
        self.assertFalse(self.university.active)
        self.university.action_unarchive()
        self.assertTrue(self.university.active)

    def test_branch_count_computation(self):
        self.assertEqual(self.university.branch_count, 0)
        self.env['uni.branch'].create({
            'name': 'Branch 1',
            'code': 'BR01',
            'university_id': self.university.id,
        })
        self.env['uni.branch'].create({
            'name': 'Branch 2',
            'code': 'BR02',
            'university_id': self.university.id,
        })
        self.assertEqual(self.university.branch_count, 2)

    def test_college_count_computation(self):
        self.assertEqual(self.university.college_count, 0)
        self.env['uni.college'].create({
            'name': 'College 1',
            'code': 'CL01',
            'university_id': self.university.id,
        })
        self.assertEqual(self.university.college_count, 1)


@tagged('post_install', '-at_install')
class TestBranch(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Branch Test University',
            'code': 'BTU',
        })
        cls.university2 = cls.env['uni.university'].create({
            'name': 'Second University',
            'code': 'SU02',
        })

    def test_create_branch(self):
        branch = self.env['uni.branch'].create({
            'name': 'Main Branch',
            'code': 'MB01',
            'university_id': self.university.id,
        })
        self.assertEqual(branch.university_id, self.university)
        self.assertTrue(branch.active)

    def test_code_uniqueness_per_university(self):
        self.env['uni.branch'].create({
            'name': 'Branch A',
            'code': 'BA01',
            'university_id': self.university.id,
        })
        self.env['uni.branch'].create({
            'name': 'Branch A Other Uni',
            'code': 'BA01',
            'university_id': self.university2.id,
        })
        with self.assertRaises(Exception):
            self.env['uni.branch'].create({
                'name': 'Branch A Duplicate',
                'code': 'BA01',
                'university_id': self.university.id,
            })

    def test_action_view_colleges(self):
        branch = self.env['uni.branch'].create({
            'name': 'View Colleges Branch',
            'code': 'VCB',
            'university_id': self.university.id,
        })
        action = branch.action_view_colleges()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'uni.college')
        self.assertEqual(action['context']['default_branch_id'], branch.id)
        self.assertEqual(action['context']['default_university_id'], self.university.id)

    def test_college_count_computation(self):
        branch = self.env['uni.branch'].create({
            'name': 'Count Branch',
            'code': 'CB01',
            'university_id': self.university.id,
        })
        self.assertEqual(branch.college_count, 0)
        self.env['uni.college'].create({
            'name': 'College 1',
            'code': 'CC01',
            'university_id': self.university.id,
            'branch_id': branch.id,
        })
        self.assertEqual(branch.college_count, 1)


@tagged('post_install', '-at_install')
class TestCollege(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'College Test University',
            'code': 'CTU',
        })
        cls.branch = cls.env['uni.branch'].create({
            'name': 'Main Branch',
            'code': 'MC01',
            'university_id': cls.university.id,
        })

    def test_create_college(self):
        college = self.env['uni.college'].create({
            'name': 'Engineering College',
            'code': 'EC01',
            'university_id': self.university.id,
            'branch_id': self.branch.id,
        })
        self.assertEqual(college.university_id, self.university)
        self.assertEqual(college.branch_id, self.branch)

    def test_code_uniqueness_per_university(self):
        self.env['uni.college'].create({
            'name': 'Science College',
            'code': 'SC01',
            'university_id': self.university.id,
        })
        with self.assertRaises(Exception):
            self.env['uni.college'].create({
                'name': 'Science College Dup',
                'code': 'SC01',
                'university_id': self.university.id,
            })

    def test_onchange_branch_id(self):
        college = self.env['uni.college'].new({
            'name': 'New College',
            'code': 'NC01',
            'university_id': False,
            'branch_id': self.branch.id,
        })
        college._onchange_branch_id()
        self.assertEqual(college.university_id, self.university)

    def test_onchange_branch_id_with_existing_university(self):
        college = self.env['uni.college'].new({
            'name': 'New College',
            'code': 'NC02',
            'university_id': self.university.id,
            'branch_id': self.branch.id,
        })
        college._onchange_branch_id()
        self.assertEqual(college.university_id, self.university)

    def test_action_view_departments(self):
        college = self.env['uni.college'].create({
            'name': 'Dept View College',
            'code': 'DVC',
            'university_id': self.university.id,
        })
        action = college.action_view_departments()
        self.assertEqual(action['res_model'], 'uni.department')

    def test_action_view_programs(self):
        college = self.env['uni.college'].create({
            'name': 'Prog View College',
            'code': 'PVC',
            'university_id': self.university.id,
        })
        action = college.action_view_programs()
        self.assertEqual(action['res_model'], 'uni.program')


@tagged('post_install', '-at_install')
class TestDepartment(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Dept Test University',
            'code': 'DTU',
        })
        cls.college = cls.env['uni.college'].create({
            'name': 'Engineering College',
            'code': 'DEC',
            'university_id': cls.university.id,
        })
        cls.college2 = cls.env['uni.college'].create({
            'name': 'Science College',
            'code': 'DSC',
            'university_id': cls.university.id,
        })

    def test_create_department(self):
        dept = self.env['uni.department'].create({
            'name': 'CS Department',
            'code': 'DCS',
            'university_id': self.university.id,
            'college_id': self.college.id,
        })
        self.assertEqual(dept.university_id, self.university)
        self.assertEqual(dept.college_id, self.college)

    def test_code_uniqueness_per_college(self):
        self.env['uni.department'].create({
            'name': 'Math Dept',
            'code': 'DMT',
            'university_id': self.university.id,
            'college_id': self.college.id,
        })
        with self.assertRaises(Exception):
            self.env['uni.department'].create({
                'name': 'Math Dept Dup',
                'code': 'DMT',
                'university_id': self.university.id,
                'college_id': self.college.id,
            })

    def test_code_allowed_across_colleges(self):
        self.env['uni.department'].create({
            'name': 'Physics Dept',
            'code': 'DPH',
            'university_id': self.university.id,
            'college_id': self.college.id,
        })
        dept2 = self.env['uni.department'].create({
            'name': 'Physics Dept Other College',
            'code': 'DPH',
            'university_id': self.university.id,
            'college_id': self.college2.id,
        })
        self.assertTrue(dept2)

    def test_onchange_college_id(self):
        dept = self.env['uni.department'].new({
            'name': 'New Dept',
            'code': 'NDP',
            'college_id': self.college.id,
            'university_id': False,
        })
        dept._onchange_college_id()
        self.assertEqual(dept.university_id, self.university)

    def test_action_view_programs(self):
        dept = self.env['uni.department'].create({
            'name': 'Program Dept',
            'code': 'PGD',
            'university_id': self.university.id,
            'college_id': self.college.id,
        })
        action = dept.action_view_programs()
        self.assertEqual(action['res_model'], 'uni.program')
        self.assertEqual(action['context']['default_department_id'], dept.id)


@tagged('post_install', '-at_install')
class TestProgram(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Prog Test University',
            'code': 'PTU',
        })
        cls.college = cls.env['uni.college'].create({
            'name': 'Engineering College',
            'code': 'PEC',
            'university_id': cls.university.id,
        })
        cls.level = cls.env['uni.program.level'].create({
            'name': 'Bachelor',
            'code': 'BSC',
            'sequence': 1,
        })

    def _create_program(self, code='CS01'):
        return self.env['uni.program'].create({
            'name': 'Computer Science',
            'code': code,
            'university_id': self.university.id,
            'college_id': self.college.id,
            'level_id': self.level.id,
        })

    def test_create_program(self):
        prog = self._create_program()
        self.assertEqual(prog.state, 'draft')
        self.assertEqual(prog.university_id, self.university)

    def test_code_uniqueness_per_college(self):
        self._create_program('CS01')
        with self.assertRaises(Exception):
            self._create_program('CS01')

    def test_state_workflow_draft_to_active(self):
        prog = self._create_program()
        self.assertEqual(prog.state, 'draft')
        prog.action_activate()
        self.assertEqual(prog.state, 'active')

    def test_state_workflow_active_to_suspended(self):
        prog = self._create_program()
        prog.action_activate()
        self.assertEqual(prog.state, 'active')
        prog.action_suspend()
        self.assertEqual(prog.state, 'suspended')

    def test_state_workflow_suspended_to_closed(self):
        prog = self._create_program()
        prog.action_activate()
        prog.action_suspend()
        prog.action_close()
        self.assertEqual(prog.state, 'closed')

    def test_state_workflow_closed_to_draft(self):
        prog = self._create_program()
        prog.action_activate()
        prog.action_suspend()
        prog.action_close()
        prog.action_draft()
        self.assertEqual(prog.state, 'draft')

    def test_onchange_college_id(self):
        prog = self.env['uni.program'].new({
            'name': 'New Program',
            'code': 'NP01',
            'college_id': self.college.id,
            'university_id': False,
            'level_id': self.level.id,
        })
        prog._onchange_college_id()
        self.assertEqual(prog.university_id, self.university)

    def test_program_level_count(self):
        self._create_program('PL1')
        self._create_program('PL2')
        self.env['uni.program'].create({
            'name': 'Electrical Engineering',
            'code': 'PL3',
            'university_id': self.university.id,
            'college_id': self.college.id,
            'level_id': self.level.id,
        })
        self.assertEqual(self.college.program_count, 3)


@tagged('post_install', '-at_install')
class TestAcademicYear(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Year Test University',
            'code': 'YTU',
        })
        cls.year = cls.env['uni.academic.year'].create({
            'name': '2025-2026',
            'code': 'AY2526',
            'university_id': cls.university.id,
            'date_start': date(2025, 9, 1),
            'date_end': date(2026, 6, 30),
        })

    def test_create_academic_year(self):
        self.assertEqual(self.year.state, 'draft')
        self.assertTrue(self.year.active)

    def test_code_uniqueness_per_university(self):
        with self.assertRaises(Exception):
            self.env['uni.academic.year'].create({
                'name': '2025-2026 Duplicate',
                'code': 'AY2526',
                'university_id': self.university.id,
                'date_start': date(2025, 9, 1),
                'date_end': date(2026, 6, 30),
            })

    def test_date_validation_end_before_start(self):
        with self.assertRaises(ValidationError):
            self.env['uni.academic.year'].create({
                'name': 'Bad Dates',
                'code': 'BD01',
                'university_id': self.university.id,
                'date_start': date(2026, 6, 30),
                'date_end': date(2025, 9, 1),
            })

    def test_is_current_uniqueness(self):
        year2 = self.env['uni.academic.year'].create({
            'name': '2026-2027',
            'code': 'AY2627',
            'university_id': self.university.id,
            'date_start': date(2026, 9, 1),
            'date_end': date(2027, 6, 30),
        })
        self.year.is_current = True
        self.year._check_is_current()
        self.assertFalse(year2.is_current)

    def test_is_current_only_one_per_university(self):
        year2 = self.env['uni.academic.year'].create({
            'name': '2026-2027',
            'code': 'AY2627',
            'university_id': self.university.id,
            'date_start': date(2026, 9, 1),
            'date_end': date(2027, 6, 30),
        })
        self.year.is_current = True
        self.year._check_is_current()
        year2.is_current = True
        year2._check_is_current()
        self.assertFalse(self.year.is_current)
        self.assertTrue(year2.is_current)

    def test_state_workflow_draft_to_active(self):
        self.year.action_activate()
        self.assertEqual(self.year.state, 'active')

    def test_state_workflow_active_to_closed(self):
        self.year.action_activate()
        self.year.action_close()
        self.assertEqual(self.year.state, 'closed')

    def test_action_set_current(self):
        self.year.action_set_current()
        self.assertTrue(self.year.is_current)
        self.assertEqual(self.year.state, 'active')

    def test_action_view_terms(self):
        action = self.year.action_view_terms()
        self.assertEqual(action['res_model'], 'uni.academic.term')
        self.assertEqual(action['context']['default_academic_year_id'], self.year.id)


@tagged('post_install', '-at_install')
class TestAcademicTerm(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Term Test University',
            'code': 'TTU',
        })
        cls.year = cls.env['uni.academic.year'].create({
            'name': '2025-2026',
            'code': 'TY2526',
            'university_id': cls.university.id,
            'date_start': date(2025, 9, 1),
            'date_end': date(2026, 6, 30),
        })
        cls.term_type = cls.env['uni.academic.term.type'].create({
            'name': 'Semester',
            'code': 'SEM',
        })

    def _create_term(self, code='T01', start=date(2025, 9, 1), end=date(2025, 12, 31)):
        return self.env['uni.academic.term'].create({
            'name': 'Fall Term',
            'code': code,
            'university_id': self.university.id,
            'academic_year_id': self.year.id,
            'term_type_id': self.term_type.id,
            'date_start': start,
            'date_end': end,
        })

    def test_create_term(self):
        term = self._create_term()
        self.assertEqual(term.academic_year_id, self.year)
        self.assertEqual(term.state, 'draft')

    def test_code_uniqueness_per_year(self):
        self._create_term()
        with self.assertRaises(Exception):
            self._create_term()

    def test_date_validation_end_before_start(self):
        with self.assertRaises(ValidationError):
            self.env['uni.academic.term'].create({
                'name': 'Bad Term',
                'code': 'BT01',
                'university_id': self.university.id,
                'academic_year_id': self.year.id,
                'term_type_id': self.term_type.id,
                'date_start': date(2025, 12, 31),
                'date_end': date(2025, 9, 1),
            })

    def test_dates_within_academic_year(self):
        with self.assertRaises(ValidationError):
            self.env['uni.academic.term'].create({
                'name': 'Early Term',
                'code': 'ET01',
                'university_id': self.university.id,
                'academic_year_id': self.year.id,
                'term_type_id': self.term_type.id,
                'date_start': date(2025, 6, 1),
                'date_end': date(2025, 8, 31),
            })

    def test_dates_end_after_academic_year(self):
        with self.assertRaises(ValidationError):
            self.env['uni.academic.term'].create({
                'name': 'Late Term',
                'code': 'LT01',
                'university_id': self.university.id,
                'academic_year_id': self.year.id,
                'term_type_id': self.term_type.id,
                'date_start': date(2026, 1, 1),
                'date_end': date(2026, 9, 30),
            })

    def test_is_current_uniqueness(self):
        term2 = self.env['uni.academic.term'].create({
            'name': 'Spring Term',
            'code': 'ST01',
            'university_id': self.university.id,
            'academic_year_id': self.year.id,
            'term_type_id': self.term_type.id,
            'date_start': date(2026, 1, 1),
            'date_end': date(2026, 5, 31),
        })
        term = self._create_term()
        term.is_current = True
        term._check_is_current()
        self.assertFalse(term2.is_current)

    def test_state_workflow(self):
        term = self._create_term()
        self.assertEqual(term.state, 'draft')
        term.action_open_registration()
        self.assertEqual(term.state, 'registration')
        term.action_activate()
        self.assertEqual(term.state, 'active')
        term.action_close()
        self.assertEqual(term.state, 'closed')

    def test_action_set_current(self):
        term = self._create_term()
        term.action_set_current()
        self.assertTrue(term.is_current)
        self.assertEqual(term.state, 'active')

    def test_action_draft(self):
        term = self._create_term()
        term.action_activate()
        term.action_draft()
        self.assertEqual(term.state, 'draft')


@tagged('post_install', '-at_install')
class TestPerson(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Person Test University',
            'code': 'PTU',
        })

    def test_create_person(self):
        person = self.env['uni.person'].create({
            'name': 'John Doe',
            'university_id': self.university.id,
            'person_type': 'student',
        })
        self.assertTrue(person.partner_id)
        self.assertEqual(person.partner_id.name, 'John Doe')

    def test_create_person_with_email(self):
        person = self.env['uni.person'].create({
            'name': 'Jane Doe',
            'university_id': self.university.id,
            'email': 'jane@example.com',
        })
        self.assertEqual(person.partner_id.email, 'jane@example.com')

    def test_age_computation(self):
        today = date.today()
        birth_date = today.replace(year=today.year - 20)
        person = self.env['uni.person'].create({
            'name': 'Age Test',
            'university_id': self.university.id,
            'birth_date': birth_date,
        })
        self.assertEqual(person.age, 20)

    def test_age_computation_birthday_not_passed(self):
        today = date.today()
        birth_date = today.replace(year=today.year - 20)
        if birth_date.month < 12:
            birth_date = birth_date.replace(month=birth_date.month + 1)
        person = self.env['uni.person'].create({
            'name': 'Age Future',
            'university_id': self.university.id,
            'birth_date': birth_date,
        })
        expected = today.year - birth_date.year - (
            (today.month, today.day) < (birth_date.month, birth_date.day)
        )
        self.assertEqual(person.age, expected)

    def test_age_computation_no_birth_date(self):
        person = self.env['uni.person'].create({
            'name': 'No Birth Date',
            'university_id': self.university.id,
        })
        self.assertEqual(person.age, 0)

    def test_person_type_selection(self):
        for ptype in ['student', 'faculty', 'staff', 'other']:
            person = self.env['uni.person'].create({
                'name': f'Person {ptype}',
                'university_id': self.university.id,
                'person_type': ptype,
            })
            self.assertEqual(person.person_type, ptype)

    def test_create_person_with_partner(self):
        partner = self.env['res.partner'].create({
            'name': 'Existing Partner',
        })
        person = self.env['uni.person'].create({
            'name': 'With Partner',
            'university_id': self.university.id,
            'partner_id': partner.id,
        })
        self.assertEqual(person.partner_id, partner)

    def test_write_person_syncs_partner(self):
        person = self.env['uni.person'].create({
            'name': 'Sync Test',
            'university_id': self.university.id,
            'email': 'old@example.com',
        })
        person.write({'email': 'new@example.com'})
        self.assertEqual(person.partner_id.email, 'new@example.com')
