# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError
from odoo import fields


@tagged('post_install', '-at_install')
class TestFacultyRank(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
            'code': 'TU',
        })
        cls.rank = cls.env['uni.faculty.rank'].create({
            'name': 'Assistant Professor',
            'code': 'ASPROF',
            'sequence': 20,
            'min_years_experience': 3,
            'salary_grade': 'SG-3',
        })

    def test_create_rank(self):
        self.assertEqual(self.rank.name, 'Assistant Professor')
        self.assertEqual(self.rank.code, 'ASPROF')
        self.assertEqual(self.rank.sequence, 20)
        self.assertEqual(self.rank.min_years_experience, 3)
        self.assertTrue(self.rank.active)

    def test_rank_code_uniqueness(self):
        with self.assertRaises(Exception):
            self.env['uni.faculty.rank'].create({
                'name': 'Duplicate Rank',
                'code': 'ASPROF',
            })

    def test_faculty_count_computation(self):
        self.assertEqual(self.rank.faculty_count, 0)
        person = self.env['uni.person'].create({
            'name': 'Dr. Smith',
            'university_id': self.university.id,
            'person_type': 'faculty',
        })
        self.env['uni.faculty'].create({
            'person_id': person.id,
            'faculty_rank_id': self.rank.id,
        })
        self.assertEqual(self.rank.faculty_count, 1)

    def test_action_toggle_active(self):
        self.assertTrue(self.rank.active)
        self.rank.action_toggle_active()
        self.assertFalse(self.rank.active)
        self.rank.action_toggle_active()
        self.assertTrue(self.rank.active)


@tagged('post_install', '-at_install')
class TestFaculty(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
            'code': 'TU',
        })
        cls.college = cls.env['uni.college'].create({
            'name': 'Engineering College',
            'code': 'ENG',
            'university_id': cls.university.id,
        })
        cls.department = cls.env['uni.department'].create({
            'name': 'Computer Science',
            'code': 'CS',
            'university_id': cls.university.id,
            'college_id': cls.college.id,
        })
        cls.rank = cls.env['uni.faculty.rank'].create({
            'name': 'Professor',
            'code': 'PROF',
            'min_years_experience': 10,
        })
        cls.person = cls.env['uni.person'].create({
            'name': 'Dr. John Doe',
            'university_id': cls.university.id,
            'person_type': 'faculty',
        })
        cls.faculty = cls.env['uni.faculty'].create({
            'person_id': cls.person.id,
            'faculty_code': 'FAC001',
            'faculty_rank_id': cls.rank.id,
            'department_id': cls.department.id,
            'college_id': cls.college.id,
            'specialization': 'Machine Learning',
            'hire_date': '2020-01-15',
            'employment_type': 'full_time',
        })

    def test_create_faculty(self):
        self.assertEqual(self.faculty.name, 'Dr. John Doe')
        self.assertEqual(self.faculty.faculty_code, 'FAC001')
        self.assertEqual(self.faculty.state, 'active')
        self.assertEqual(self.faculty.employment_type, 'full_time')
        self.assertEqual(self.faculty.specialization, 'Machine Learning')

    def test_faculty_code_uniqueness(self):
        person2 = self.env['uni.person'].create({
            'name': 'Dr. Jane Doe',
            'university_id': self.university.id,
            'person_type': 'faculty',
        })
        with self.assertRaises(Exception):
            self.env['uni.faculty'].create({
                'person_id': person2.id,
                'faculty_code': 'FAC001',
            })

    def test_state_workflow_active_to_on_leave(self):
        self.assertEqual(self.faculty.state, 'active')
        self.faculty.action_on_leave()
        self.assertEqual(self.faculty.state, 'on_leave')

    def test_state_workflow_on_leave_to_active(self):
        self.faculty.action_on_leave()
        self.assertEqual(self.faculty.state, 'on_leave')
        self.faculty.action_activate()
        self.assertEqual(self.faculty.state, 'active')

    def test_state_workflow_active_to_terminated(self):
        self.faculty.action_terminate()
        self.assertEqual(self.faculty.state, 'terminated')
        self.assertTrue(self.faculty.termination_date)

    def test_cannot_activate_terminated(self):
        self.faculty.action_terminate()
        with self.assertRaises(ValidationError):
            self.faculty.action_activate()

    def test_cannot_place_terminated_on_leave(self):
        self.faculty.action_terminate()
        with self.assertRaises(ValidationError):
            self.faculty.action_on_leave()

    def test_termination_clears_date_on_activate(self):
        self.faculty.action_terminate()
        self.assertTrue(self.faculty.termination_date)

    def test_date_validation_termination_before_hire(self):
        with self.assertRaises(ValidationError):
            self.faculty.write({
                'hire_date': '2020-01-15',
                'termination_date': '2019-01-15',
            })

    def test_termination_state_requires_date(self):
        with self.assertRaises(ValidationError):
            self.faculty.write({
                'state': 'terminated',
                'termination_date': False,
            })

    def test_total_load_computation(self):
        self.assertEqual(self.faculty.total_load_hours, 0.0)
        term_type = self.env['uni.academic.term.type'].create({
            'name': 'Semester',
            'code': 'SEM',
            'terms_per_year': 2,
        })
        year = self.env['uni.academic.year'].create({
            'name': '2024-2025',
            'code': '2024',
            'university_id': self.university.id,
            'date_start': '2024-09-01',
            'date_end': '2025-06-30',
        })
        term = self.env['uni.academic.term'].create({
            'name': 'Fall 2024',
            'code': 'F24',
            'university_id': self.university.id,
            'academic_year_id': year.id,
            'term_type_id': term_type.id,
            'date_start': '2024-09-01',
            'date_end': '2024-12-31',
        })
        self.env['uni.faculty.load'].create({
            'faculty_id': self.faculty.id,
            'academic_term_id': term.id,
            'teaching_hours': 12.0,
            'research_hours': 6.0,
            'admin_hours': 2.0,
        })
        self.assertEqual(self.faculty.total_load_hours, 20.0)

    def test_active_assignment_count(self):
        self.assertEqual(self.faculty.active_assignment_count, 0)

    def test_publication_count(self):
        self.assertEqual(self.faculty.publication_count, 0)

    def test_inferred_university_from_college(self):
        person = self.env['uni.person'].create({
            'name': 'Dr. Inferred',
            'university_id': self.university.id,
            'person_type': 'faculty',
        })
        f = self.env['uni.faculty'].create({
            'person_id': person.id,
            'college_id': self.college.id,
        })
        self.assertEqual(f.university_id, self.university)


@tagged('post_install', '-at_install')
class TestFacultyAssignment(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
            'code': 'TU',
        })
        cls.college = cls.env['uni.college'].create({
            'name': 'Engineering College',
            'code': 'ENG',
            'university_id': cls.university.id,
        })
        cls.department = cls.env['uni.department'].create({
            'name': 'Computer Science',
            'code': 'CS',
            'university_id': cls.university.id,
            'college_id': cls.college.id,
        })
        cls.program = cls.env['uni.program'].create({
            'name': 'BS Computer Science',
            'code': 'BSCS',
            'university_id': cls.university.id,
            'college_id': cls.college.id,
            'department_id': cls.department.id,
            'level_id': cls.env['uni.program.level'].create({
                'name': 'Bachelor',
                'code': 'BSC',
            }).id,
        })
        term_type = cls.env['uni.academic.term.type'].create({
            'name': 'Semester',
            'code': 'SEM',
            'terms_per_year': 2,
        })
        cls.year = cls.env['uni.academic.year'].create({
            'name': '2024-2025',
            'code': '2024',
            'university_id': cls.university.id,
            'date_start': '2024-09-01',
            'date_end': '2025-06-30',
        })
        cls.term = cls.env['uni.academic.term'].create({
            'name': 'Fall 2024',
            'code': 'F24',
            'university_id': cls.university.id,
            'academic_year_id': cls.year.id,
            'term_type_id': term_type.id,
            'date_start': '2024-09-01',
            'date_end': '2024-12-31',
        })
        cls.person = cls.env['uni.person'].create({
            'name': 'Dr. Assigner',
            'university_id': cls.university.id,
            'person_type': 'faculty',
        })
        cls.faculty = cls.env['uni.faculty'].create({
            'person_id': cls.person.id,
            'faculty_code': 'FAC-ASN001',
            'department_id': cls.department.id,
            'college_id': cls.college.id,
        })
        cls.assignment = cls.env['uni.faculty.assignment'].create({
            'faculty_id': cls.faculty.id,
            'course_name': 'Introduction to Programming',
            'course_code': 'CS101',
            'program_id': cls.program.id,
            'academic_term_id': cls.term.id,
            'assignment_type': 'primary',
            'start_date': '2024-09-01',
            'end_date': '2024-12-31',
        })

    def test_create_assignment(self):
        self.assertTrue(self.assignment.name)
        self.assertEqual(self.assignment.faculty_id, self.faculty)
        self.assertEqual(self.assignment.course_name, 'Introduction to Programming')
        self.assertEqual(self.assignment.state, 'draft')
        self.assertEqual(self.assignment.assignment_type, 'primary')

    def test_date_validation(self):
        with self.assertRaises(ValidationError):
            self.env['uni.faculty.assignment'].create({
                'faculty_id': self.faculty.id,
                'course_name': 'Bad Dates',
                'academic_term_id': self.term.id,
                'start_date': '2024-12-31',
                'end_date': '2024-09-01',
            })

    def test_student_count_non_negative(self):
        with self.assertRaises(ValidationError):
            self.assignment.write({'student_count': -1})

    def test_state_workflow_draft_to_active(self):
        self.assignment.action_activate()
        self.assertEqual(self.assignment.state, 'active')

    def test_state_workflow_active_to_completed(self):
        self.assignment.action_activate()
        self.assignment.action_complete()
        self.assertEqual(self.assignment.state, 'completed')

    def test_state_workflow_active_to_cancelled(self):
        self.assignment.action_activate()
        self.assignment.action_cancel()
        self.assertEqual(self.assignment.state, 'cancelled')

    def test_state_workflow_draft_to_cancelled(self):
        self.assignment.action_cancel()
        self.assertEqual(self.assignment.state, 'cancelled')

    def test_onchange_term_fills_dates(self):
        a = self.env['uni.faculty.assignment'].new({
            'faculty_id': self.faculty.id,
            'academic_term_id': self.term.id,
        })
        a._onchange_academic_term_id()
        self.assertEqual(a.start_date, self.term.date_start)
        self.assertEqual(a.end_date, self.term.date_end)


@tagged('post_install', '-at_install')
class TestFacultyLoad(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
            'code': 'TU',
        })
        cls.college = cls.env['uni.college'].create({
            'name': 'Engineering College',
            'code': 'ENG',
            'university_id': cls.university.id,
        })
        term_type = cls.env['uni.academic.term.type'].create({
            'name': 'Semester',
            'code': 'SEM',
            'terms_per_year': 2,
        })
        cls.year = cls.env['uni.academic.year'].create({
            'name': '2024-2025',
            'code': '2024',
            'university_id': cls.university.id,
            'date_start': '2024-09-01',
            'date_end': '2025-06-30',
        })
        cls.term = cls.env['uni.academic.term'].create({
            'name': 'Fall 2024',
            'code': 'F24',
            'university_id': cls.university.id,
            'academic_year_id': cls.year.id,
            'term_type_id': term_type.id,
            'date_start': '2024-09-01',
            'date_end': '2024-12-31',
        })
        cls.person = cls.env['uni.person'].create({
            'name': 'Dr. Load',
            'university_id': cls.university.id,
            'person_type': 'faculty',
        })
        cls.faculty = cls.env['uni.faculty'].create({
            'person_id': cls.person.id,
            'faculty_code': 'FAC-LOAD001',
            'college_id': cls.college.id,
        })
        cls.load = cls.env['uni.faculty.load'].create({
            'faculty_id': cls.faculty.id,
            'academic_term_id': cls.term.id,
            'teaching_hours': 12.0,
            'research_hours': 6.0,
            'admin_hours': 2.0,
        })

    def test_create_load(self):
        self.assertTrue(self.load.name)
        self.assertEqual(self.load.faculty_id, self.faculty)
        self.assertEqual(self.load.teaching_hours, 12.0)
        self.assertEqual(self.load.research_hours, 6.0)
        self.assertEqual(self.load.admin_hours, 2.0)

    def test_total_hours_computation(self):
        self.assertEqual(self.load.total_hours, 20.0)

    def test_total_hours_zero(self):
        load = self.env['uni.faculty.load'].create({
            'faculty_id': self.faculty.id,
            'academic_term_id': self.env['uni.academic.term'].create({
                'name': 'Spring 2025',
                'code': 'S25',
                'university_id': self.university.id,
                'academic_year_id': self.year.id,
                'term_type_id': self.env.ref('university_core.uni_academic_term_type_semester', raise_if_not_found=False) and self.term.term_type_id.id or self.env['uni.academic.term.type'].create({'name': 'SEM2', 'code': 'SEM2'}).id,
                'date_start': '2025-01-01',
                'date_end': '2025-05-31',
            }).id,
            'teaching_hours': 0.0,
            'research_hours': 0.0,
            'admin_hours': 0.0,
        })
        self.assertEqual(load.total_hours, 0.0)

    def test_non_negative_validation(self):
        with self.assertRaises(ValidationError):
            self.load.write({'teaching_hours': -5.0})
        with self.assertRaises(ValidationError):
            self.load.write({'research_hours': -5.0})
        with self.assertRaises(ValidationError):
            self.load.write({'admin_hours': -5.0})

    def test_unique_faculty_per_term(self):
        with self.assertRaises(Exception):
            self.env['uni.faculty.load'].create({
                'faculty_id': self.faculty.id,
                'academic_term_id': self.term.id,
                'teaching_hours': 10.0,
            })

    def test_load_ref_uniqueness(self):
        with self.assertRaises(Exception):
            self.env['uni.faculty.load'].create({
                'name': self.load.name,
                'faculty_id': self.faculty.id,
                'academic_term_id': self.env['uni.academic.term'].create({
                    'name': 'Spring 2025',
                    'code': 'S25',
                    'university_id': self.university.id,
                    'academic_year_id': self.year.id,
                    'term_type_id': self.term.term_type_id.id,
                    'date_start': '2025-01-01',
                    'date_end': '2025-05-31',
                }).id,
            })


@tagged('post_install', '-at_install')
class TestFacultyContract(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
            'code': 'TU',
        })
        cls.college = cls.env['uni.college'].create({
            'name': 'Engineering College',
            'code': 'ENG',
            'university_id': cls.university.id,
        })
        cls.person = cls.env['uni.person'].create({
            'name': 'Dr. Contract',
            'university_id': cls.university.id,
            'person_type': 'faculty',
        })
        cls.faculty = cls.env['uni.faculty'].create({
            'person_id': cls.person.id,
            'faculty_code': 'FAC-CTR001',
            'college_id': cls.college.id,
        })
        cls.contract = cls.env['uni.faculty.contract'].create({
            'faculty_id': cls.faculty.id,
            'contract_type': 'full_time',
            'university_id': cls.university.id,
            'start_date': '2024-09-01',
            'end_date': '2025-08-31',
            'salary': 75000.0,
        })

    def test_create_contract(self):
        self.assertTrue(self.contract.name)
        self.assertEqual(self.contract.state, 'draft')
        self.assertEqual(self.contract.contract_type, 'full_time')
        self.assertEqual(self.contract.salary, 75000.0)

    def test_state_workflow_draft_to_submitted(self):
        self.contract.action_submit()
        self.assertEqual(self.contract.state, 'submitted')

    def test_state_workflow_submitted_to_approved(self):
        self.contract.action_submit()
        self.contract.action_approve()
        self.assertEqual(self.contract.state, 'approved')
        self.assertEqual(self.contract.approved_by.id, self.env.uid)
        self.assertTrue(self.contract.approved_date)

    def test_state_workflow_approved_to_active(self):
        self.contract.action_submit()
        self.contract.action_approve()
        self.contract.action_activate()
        self.assertEqual(self.contract.state, 'active')

    def test_state_workflow_to_terminated(self):
        self.contract.action_submit()
        self.contract.action_approve()
        self.contract.action_activate()
        self.contract.action_terminate()
        self.assertEqual(self.contract.state, 'terminated')
        self.assertTrue(self.contract.termination_date)

    def test_state_workflow_to_expired(self):
        self.contract.action_submit()
        self.contract.action_approve()
        self.contract.action_activate()
        self.contract.action_expire()
        self.assertEqual(self.contract.state, 'expired')

    def test_state_workflow_to_renewed(self):
        self.contract.action_submit()
        self.contract.action_approve()
        self.contract.action_activate()
        result = self.contract.action_renew()
        self.assertEqual(self.contract.state, 'renewed')
        self.assertIsNotNone(result)

    def test_renew_creates_new_contract(self):
        self.contract.action_submit()
        self.contract.action_approve()
        self.contract.action_activate()
        self.contract.action_renew()
        new_contracts = self.env['uni.faculty.contract'].search([
            ('faculty_id', '=', self.faculty.id),
            ('id', '!=', self.contract.id),
        ])
        self.assertEqual(len(new_contracts), 1)
        self.assertEqual(new_contracts.state, 'draft')

    def test_state_workflow_to_cancelled(self):
        self.contract.action_cancel()
        self.assertEqual(self.contract.state, 'cancelled')

    def test_date_validation_via_sql(self):
        with self.assertRaises(Exception):
            self.env['uni.faculty.contract'].create({
                'faculty_id': self.faculty.id,
                'contract_type': 'full_time',
                'university_id': self.university.id,
                'start_date': '2025-08-31',
                'end_date': '2024-09-01',
                'salary': 50000.0,
            })

    def test_salary_non_negative(self):
        with self.assertRaises(Exception):
            self.env['uni.faculty.contract'].create({
                'faculty_id': self.faculty.id,
                'contract_type': 'full_time',
                'university_id': self.university.id,
                'start_date': '2024-09-01',
                'salary': -1000.0,
            })

    def test_contract_ref_uniqueness(self):
        with self.assertRaises(Exception):
            self.env['uni.faculty.contract'].create({
                'name': self.contract.name,
                'faculty_id': self.faculty.id,
                'contract_type': 'part_time',
                'university_id': self.university.id,
                'start_date': '2024-09-01',
                'salary': 30000.0,
            })


@tagged('post_install', '-at_install')
class TestFacultyPublication(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
            'code': 'TU',
        })
        cls.person = cls.env['uni.person'].create({
            'name': 'Dr. Publisher',
            'university_id': cls.university.id,
            'person_type': 'faculty',
        })
        cls.faculty = cls.env['uni.faculty'].create({
            'person_id': cls.person.id,
            'faculty_code': 'FAC-PUB001',
        })
        cls.publication = cls.env['uni.faculty.publication'].create({
            'faculty_id': cls.faculty.id,
            'title': 'Deep Learning in Healthcare',
            'publication_type': 'journal',
            'publisher': 'IEEE',
            'publication_date': '2024-06-15',
            'doi': '10.1109/TEST.2024.12345',
            'citation_count': 10,
            'is_peer_reviewed': True,
        })

    def test_create_publication(self):
        self.assertTrue(self.publication.name)
        self.assertEqual(self.publication.title, 'Deep Learning in Healthcare')
        self.assertEqual(self.publication.publication_type, 'journal')
        self.assertEqual(self.publication.citation_count, 10)

    def test_citation_count_non_negative(self):
        with self.assertRaises(ValidationError):
            self.publication.write({'citation_count': -1})

    def test_doi_format_validation(self):
        with self.assertRaises(ValidationError):
            self.env['uni.faculty.publication'].create({
                'faculty_id': self.faculty.id,
                'title': 'Bad DOI',
                'publication_type': 'journal',
                'doi': 'invalid-doi',
            })

    def test_doi_valid_format(self):
        pub = self.env['uni.faculty.publication'].create({
            'faculty_id': self.faculty.id,
            'title': 'Valid DOI',
            'publication_type': 'journal',
            'doi': '10.1000/xyz123',
        })
        self.assertEqual(pub.doi, '10.1000/xyz123')

    def test_doi_not_checked_for_books(self):
        pub = self.env['uni.faculty.publication'].create({
            'faculty_id': self.faculty.id,
            'title': 'Book with DOI',
            'publication_type': 'book',
            'doi': 'not-a-real-doi',
        })
        self.assertEqual(pub.doi, 'not-a-real-doi')

    def test_publication_ref_uniqueness(self):
        with self.assertRaises(Exception):
            self.env['uni.faculty.publication'].create({
                'name': self.publication.name,
                'faculty_id': self.faculty.id,
                'title': 'Duplicate Ref',
            })


@tagged('post_install', '-at_install')
class TestCommittee(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
            'code': 'TU',
        })
        cls.college = cls.env['uni.college'].create({
            'name': 'Engineering College',
            'code': 'ENG',
            'university_id': cls.university.id,
        })
        cls.department = cls.env['uni.department'].create({
            'name': 'Computer Science',
            'code': 'CS',
            'university_id': cls.university.id,
            'college_id': cls.college.id,
        })
        cls.chair_person = cls.env['uni.person'].create({
            'name': 'Dr. Chair',
            'university_id': cls.university.id,
            'person_type': 'faculty',
        })
        cls.chair_faculty = cls.env['uni.faculty'].create({
            'person_id': cls.chair_person.id,
            'faculty_code': 'FAC-CH001',
            'college_id': cls.college.id,
        })
        cls.committee = cls.env['uni.committee'].create({
            'name': 'Academic Standards Committee',
            'code': 'ASC',
            'committee_type': 'academic',
            'university_id': cls.university.id,
            'college_id': cls.college.id,
            'chair_id': cls.chair_faculty.id,
            'start_date': '2024-09-01',
        })

    def test_create_committee(self):
        self.assertEqual(self.committee.name, 'Academic Standards Committee')
        self.assertEqual(self.committee.state, 'draft')
        self.assertEqual(self.committee.chair_id, self.chair_faculty)

    def test_committee_code_uniqueness(self):
        with self.assertRaises(Exception):
            self.env['uni.committee'].create({
                'name': 'Duplicate Committee',
                'code': 'ASC',
                'university_id': self.university.id,
            })

    def test_state_workflow_draft_to_active(self):
        self.committee.action_activate()
        self.assertEqual(self.committee.state, 'active')

    def test_activation_requires_chair(self):
        committee = self.env['uni.committee'].create({
            'name': 'No Chair Committee',
            'code': 'NCC',
            'university_id': self.university.id,
        })
        with self.assertRaises(ValidationError):
            committee.action_activate()

    def test_state_workflow_active_to_closed(self):
        self.committee.action_activate()
        self.committee.action_close()
        self.assertEqual(self.committee.state, 'closed')
        self.assertTrue(self.committee.end_date)

    def test_state_workflow_to_draft(self):
        self.committee.action_activate()
        self.committee.action_draft()
        self.assertEqual(self.committee.state, 'draft')

    def test_date_validation(self):
        with self.assertRaises(ValidationError):
            self.env['uni.committee'].create({
                'name': 'Bad Dates',
                'code': 'BD',
                'university_id': self.university.id,
                'start_date': '2024-12-31',
                'end_date': '2024-09-01',
            })

    def test_hierarchy_validation_department_mismatch(self):
        other_university = self.env['uni.university'].create({
            'name': 'Other University',
            'code': 'OU',
        })
        other_dept = self.env['uni.department'].create({
            'name': 'Other Dept',
            'code': 'OD',
            'university_id': other_university.id,
            'college_id': self.college.id,
        })
        with self.assertRaises(ValidationError):
            self.env['uni.committee'].create({
                'name': 'Mismatch Committee',
                'code': 'MC',
                'university_id': self.university.id,
                'department_id': other_dept.id,
            })

    def test_member_count_computation(self):
        self.assertEqual(self.committee.member_count, 0)
        member_person = self.env['uni.person'].create({
            'name': 'Dr. Member',
            'university_id': self.university.id,
            'person_type': 'faculty',
        })
        member_faculty = self.env['uni.faculty'].create({
            'person_id': member_person.id,
            'faculty_code': 'FAC-MEM001',
        })
        self.env['uni.committee.member'].create({
            'committee_id': self.committee.id,
            'faculty_id': member_faculty.id,
            'role': 'member',
            'is_active': True,
        })
        self.committee.invalidate_recordset(['member_count'])
        self.assertEqual(self.committee.member_count, 1)


@tagged('post_install', '-at_install')
class TestCommitteeMember(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
            'code': 'TU',
        })
        cls.committee = cls.env['uni.committee'].create({
            'name': 'Test Committee',
            'code': 'TC',
            'university_id': cls.university.id,
        })
        cls.chair_person = cls.env['uni.person'].create({
            'name': 'Dr. Chair',
            'university_id': cls.university.id,
            'person_type': 'faculty',
        })
        cls.chair_faculty = cls.env['uni.faculty'].create({
            'person_id': cls.chair_person.id,
            'faculty_code': 'FAC-CM001',
        })
        cls.member_person = cls.env['uni.person'].create({
            'name': 'Dr. Member',
            'university_id': cls.university.id,
            'person_type': 'faculty',
        })
        cls.member_faculty = cls.env['uni.faculty'].create({
            'person_id': cls.member_person.id,
            'faculty_code': 'FAC-CM002',
        })
        cls.member = cls.env['uni.committee.member'].create({
            'committee_id': cls.committee.id,
            'faculty_id': cls.chair_faculty.id,
            'role': 'chair',
            'is_active': True,
        })

    def test_create_member(self):
        self.assertTrue(self.member.name)
        self.assertEqual(self.member.committee_id, self.committee)
        self.assertEqual(self.member.faculty_id, self.chair_faculty)
        self.assertEqual(self.member.role, 'chair')
        self.assertTrue(self.member.is_active)

    def test_unique_committee_faculty(self):
        with self.assertRaises(Exception):
            self.env['uni.committee.member'].create({
                'committee_id': self.committee.id,
                'faculty_id': self.chair_faculty.id,
                'role': 'member',
            })

    def test_single_chair_constraint(self):
        with self.assertRaises(ValidationError):
            self.env['uni.committee.member'].create({
                'committee_id': self.committee.id,
                'faculty_id': self.member_faculty.id,
                'role': 'chair',
                'is_active': True,
            })

    def test_multiple_non_chair_roles_allowed(self):
        self.env['uni.committee.member'].create({
            'committee_id': self.committee.id,
            'faculty_id': self.member_faculty.id,
            'role': 'vice_chair',
            'is_active': True,
        })
        self.assertEqual(len(self.committee.member_ids), 2)

    def test_date_validation(self):
        with self.assertRaises(ValidationError):
            self.env['uni.committee.member'].create({
                'committee_id': self.committee.id,
                'faculty_id': self.member_faculty.id,
                'role': 'member',
                'join_date': '2024-12-31',
                'leave_date': '2024-09-01',
            })

    def test_onchange_leave_date_deactivates(self):
        member = self.env['uni.committee.member'].new({
            'committee_id': self.committee.id,
            'faculty_id': self.member_faculty.id,
        })
        member.leave_date = '2024-12-31'
        member._onchange_leave_date()
        self.assertFalse(member.is_active)
