# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError
from odoo import fields


@tagged('post_install', '-at_install')
class TestStudentStatus(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
            'code': 'TU',
        })
        cls.status = cls.env['uni.student.status'].create({
            'name': 'Active',
            'code': 'ACTIVE',
            'is_active_status': True,
            'sequence': 10,
        })

    def test_create_status(self):
        self.assertEqual(self.status.name, 'Active')
        self.assertEqual(self.status.code, 'ACTIVE')
        self.assertTrue(self.status.is_active_status)
        self.assertTrue(self.status.active)

    def test_status_code_uniqueness(self):
        with self.assertRaises(Exception):
            self.env['uni.student.status'].create({
                'name': 'Duplicate Status',
                'code': 'ACTIVE',
            })

    def test_student_count_computation(self):
        self.assertEqual(self.status.student_count, 0)

    def test_action_toggle_active(self):
        self.assertTrue(self.status.active)
        self.status.action_toggle_active()
        self.assertFalse(self.status.active)


@tagged('post_install', '-at_install')
class TestStudent(TransactionCase):

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
        cls.level = cls.env['uni.program.level'].create({
            'name': 'Bachelor',
            'code': 'BSC',
        })
        cls.program = cls.env['uni.program'].create({
            'name': 'BS Computer Science',
            'code': 'BSCS',
            'university_id': cls.university.id,
            'college_id': cls.college.id,
            'department_id': cls.department.id,
            'level_id': cls.level.id,
            'credit_hours': 120,
        })
        cls.status = cls.env['uni.student.status'].create({
            'name': 'Active',
            'code': 'ACTIVE',
            'is_active_status': True,
        })
        cls.person = cls.env['uni.person'].create({
            'name': 'Ahmed Student',
            'university_id': cls.university.id,
            'person_type': 'student',
        })
        cls.student = cls.env['uni.student'].create({
            'person_id': cls.person.id,
            'student_code': 'STU001',
            'program_id': cls.program.id,
            'department_id': cls.department.id,
            'college_id': cls.college.id,
            'status_id': cls.status.id,
            'admission_date': '2024-09-01',
            'expected_graduation_date': '2028-06-30',
            'state': 'prospective',
        })

    def test_create_student(self):
        self.assertEqual(self.student.name, 'Ahmed Student')
        self.assertEqual(self.student.student_code, 'STU001')
        self.assertEqual(self.student.state, 'prospective')
        self.assertEqual(self.student.current_level, 1)

    def test_student_code_uniqueness(self):
        person2 = self.env['uni.person'].create({
            'name': 'Another Student',
            'university_id': self.university.id,
            'person_type': 'student',
        })
        with self.assertRaises(Exception):
            self.env['uni.student'].create({
                'person_id': person2.id,
                'student_code': 'STU001',
            })

    def test_barcode_uniqueness(self):
        self.student.barcode = 'BAR001'
        person2 = self.env['uni.person'].create({
            'name': 'Barcode Student',
            'university_id': self.university.id,
            'person_type': 'student',
        })
        with self.assertRaises(Exception):
            self.env['uni.student'].create({
                'person_id': person2.id,
                'student_code': 'STU-BAR',
                'barcode': 'BAR001',
            })

    def test_state_workflow_prospective_to_active(self):
        self.student.action_activate()
        self.assertEqual(self.student.state, 'active')

    def test_state_workflow_active_to_graduated(self):
        self.student.action_activate()
        self.student.action_graduate()
        self.assertEqual(self.student.state, 'graduated')
        self.assertTrue(self.student.actual_graduation_date)

    def test_state_workflow_active_to_suspended(self):
        self.student.action_activate()
        self.student.action_suspend()
        self.assertEqual(self.student.state, 'suspended')

    def test_state_workflow_active_to_withdrawn(self):
        self.student.action_activate()
        self.student.action_withdraw()
        self.assertEqual(self.student.state, 'withdrawn')

    def test_cannot_activate_graduated(self):
        self.student.action_activate()
        self.student.action_graduate()
        with self.assertRaises(ValidationError):
            self.student.action_activate()

    def test_cannot_suspend_graduated(self):
        self.student.action_activate()
        self.student.action_graduate()
        with self.assertRaises(ValidationError):
            self.student.action_suspend()

    def test_cannot_withdraw_graduated(self):
        self.student.action_activate()
        self.student.action_graduate()
        with self.assertRaises(ValidationError):
            self.student.action_withdraw()

    def test_reactivate_suspended(self):
        self.student.action_activate()
        self.student.action_suspend()
        self.student.action_reactivate()
        self.assertEqual(self.student.state, 'active')

    def test_reactivate_withdrawn(self):
        self.student.action_activate()
        self.student.action_withdraw()
        self.student.action_reactivate()
        self.assertEqual(self.student.state, 'active')

    def test_cannot_reactivate_active(self):
        self.student.action_activate()
        with self.assertRaises(ValidationError):
            self.student.action_reactivate()

    def test_graduation_sets_date(self):
        self.student.action_activate()
        self.assertFalse(self.student.actual_graduation_date)
        self.student.action_graduate()
        self.assertTrue(self.student.actual_graduation_date)

    def test_graduation_state_requires_date(self):
        with self.assertRaises(ValidationError):
            self.student.write({
                'state': 'graduated',
                'actual_graduation_date': False,
            })

    def test_date_validation_expected_before_admission(self):
        with self.assertRaises(ValidationError):
            self.student.write({
                'admission_date': '2024-09-01',
                'expected_graduation_date': '2023-06-30',
            })

    def test_date_validation_actual_before_admission(self):
        self.student.action_activate()
        with self.assertRaises(ValidationError):
            self.student.write({
                'actual_graduation_date': '2023-06-30',
            })

    def test_current_level_non_negative(self):
        with self.assertRaises(ValidationError):
            self.student.write({'current_level': -1})

    def test_gpa_computation_no_enrollments(self):
        self.assertEqual(self.student.cumulative_gpa, 0.0)

    def test_academic_standing_computation(self):
        self.assertEqual(self.student.academic_standing, 'good')

    def test_inferred_university_from_program(self):
        person = self.env['uni.person'].create({
            'name': 'Inferred Student',
            'university_id': self.university.id,
            'person_type': 'student',
        })
        s = self.env['uni.student'].create({
            'person_id': person.id,
            'program_id': self.program.id,
        })
        self.assertEqual(s.university_id, self.university)

    def test_enrollment_count(self):
        self.assertEqual(self.student.enrollment_count, 0)

    def test_document_count(self):
        self.assertEqual(self.student.document_count, 0)


@tagged('post_install', '-at_install')
class TestStudentEnrollment(TransactionCase):

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
        cls.level = cls.env['uni.program.level'].create({
            'name': 'Bachelor',
            'code': 'BSC',
        })
        cls.program = cls.env['uni.program'].create({
            'name': 'BS Computer Science',
            'code': 'BSCS',
            'university_id': cls.university.id,
            'college_id': cls.college.id,
            'department_id': cls.department.id,
            'level_id': cls.level.id,
            'credit_hours': 120,
        })
        cls.course = cls.env['uni.course'].create({
            'name': 'Intro to Programming',
            'code': 'CS101',
            'university_id': cls.university.id,
            'college_id': cls.college.id,
            'credit_hours': 3.0,
        })
        cls.course2 = cls.env['uni.course'].create({
            'name': 'Data Structures',
            'code': 'CS201',
            'university_id': cls.university.id,
            'college_id': cls.college.id,
            'credit_hours': 3.0,
        })
        cls.year = cls.env['uni.academic.year'].create({
            'name': '2024-2025',
            'code': '2024',
            'university_id': cls.university.id,
            'date_start': '2024-09-01',
            'date_end': '2025-06-30',
        })
        term_type = cls.env['uni.academic.term.type'].create({
            'name': 'Semester',
            'code': 'SEM',
            'terms_per_year': 2,
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
            'name': 'Enrolled Student',
            'university_id': cls.university.id,
            'person_type': 'student',
        })
        cls.student = cls.env['uni.student'].create({
            'person_id': cls.person.id,
            'program_id': cls.program.id,
            'college_id': cls.college.id,
            'state': 'active',
        })
        cls.enrollment = cls.env['uni.student.enrollment'].create({
            'student_id': cls.student.id,
            'academic_term_id': cls.term.id,
            'program_id': cls.program.id,
        })

    def test_create_enrollment(self):
        self.assertTrue(self.enrollment.name)
        self.assertEqual(self.enrollment.state, 'draft')
        self.assertEqual(self.enrollment.student_id, self.student)

    def test_unique_student_per_term(self):
        with self.assertRaises(Exception):
            self.env['uni.student.enrollment'].create({
                'student_id': self.student.id,
                'academic_term_id': self.term.id,
            })

    def test_state_workflow_draft_to_enrolled(self):
        self.env['uni.student.enrollment.line'].create({
            'enrollment_id': self.enrollment.id,
            'course_id': self.course.id,
        })
        self.enrollment.action_enroll()
        self.assertEqual(self.enrollment.state, 'enrolled')

    def test_enroll_requires_lines(self):
        with self.assertRaises(ValidationError):
            self.enrollment.action_enroll()

    def test_state_workflow_enrolled_to_completed(self):
        self.env['uni.student.enrollment.line'].create({
            'enrollment_id': self.enrollment.id,
            'course_id': self.course.id,
        })
        self.enrollment.action_enroll()
        self.enrollment.action_complete()
        self.assertEqual(self.enrollment.state, 'completed')

    def test_complete_requires_enrolled(self):
        with self.assertRaises(ValidationError):
            self.enrollment.action_complete()

    def test_state_workflow_to_cancelled(self):
        self.enrollment.action_cancel()
        self.assertEqual(self.enrollment.state, 'cancelled')

    def test_cannot_cancel_completed(self):
        self.env['uni.student.enrollment.line'].create({
            'enrollment_id': self.enrollment.id,
            'course_id': self.course.id,
        })
        self.enrollment.action_enroll()
        self.enrollment.action_complete()
        with self.assertRaises(ValidationError):
            self.enrollment.action_cancel()

    def test_state_workflow_to_draft(self):
        self.enrollment.action_cancel()
        self.enrollment.action_draft()
        self.assertEqual(self.enrollment.state, 'draft')

    def test_cannot_reset_completed_to_draft(self):
        self.env['uni.student.enrollment.line'].create({
            'enrollment_id': self.enrollment.id,
            'course_id': self.course.id,
        })
        self.enrollment.action_enroll()
        self.enrollment.action_complete()
        with self.assertRaises(ValidationError):
            self.enrollment.action_draft()

    def test_line_count_computation(self):
        self.assertEqual(self.enrollment.line_count, 0)
        self.env['uni.student.enrollment.line'].create({
            'enrollment_id': self.enrollment.id,
            'course_id': self.course.id,
        })
        self.enrollment.invalidate_recordset(['line_count'])
        self.assertEqual(self.enrollment.line_count, 1)

    def test_enrolled_state_requires_lines(self):
        self.enrollment.state = 'enrolled'
        with self.assertRaises(ValidationError):
            self.enrollment.write({'line_ids': [(5, 0, 0)]})

    def test_level_non_negative(self):
        with self.assertRaises(ValidationError):
            self.enrollment.write({'level': -1})


@tagged('post_install', '-at_install')
class TestEnrollmentLine(TransactionCase):

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
        cls.level = cls.env['uni.program.level'].create({
            'name': 'Bachelor',
            'code': 'BSC',
        })
        cls.program = cls.env['uni.program'].create({
            'name': 'BS Computer Science',
            'code': 'BSCS',
            'university_id': cls.university.id,
            'college_id': cls.college.id,
            'department_id': cls.department.id,
            'level_id': cls.level.id,
            'credit_hours': 120,
        })
        cls.course = cls.env['uni.course'].create({
            'name': 'Intro to Programming',
            'code': 'CS101',
            'university_id': cls.university.id,
            'college_id': cls.college.id,
            'credit_hours': 3.0,
        })
        cls.course2 = cls.env['uni.course'].create({
            'name': 'Data Structures',
            'code': 'CS201',
            'university_id': cls.university.id,
            'college_id': cls.college.id,
            'credit_hours': 3.0,
        })
        cls.year = cls.env['uni.academic.year'].create({
            'name': '2024-2025',
            'code': '2024',
            'university_id': cls.university.id,
            'date_start': '2024-09-01',
            'date_end': '2025-06-30',
        })
        term_type = cls.env['uni.academic.term.type'].create({
            'name': 'Semester',
            'code': 'SEM',
            'terms_per_year': 2,
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
            'name': 'Line Student',
            'university_id': cls.university.id,
            'person_type': 'student',
        })
        cls.student = cls.env['uni.student'].create({
            'person_id': cls.person.id,
            'program_id': cls.program.id,
            'college_id': cls.college.id,
            'state': 'active',
        })
        cls.enrollment = cls.env['uni.student.enrollment'].create({
            'student_id': cls.student.id,
            'academic_term_id': cls.term.id,
            'program_id': cls.program.id,
        })
        cls.line = cls.env['uni.student.enrollment.line'].create({
            'enrollment_id': cls.enrollment.id,
            'course_id': cls.course.id,
            'final_grade': 85.0,
        })

    def test_create_line(self):
        self.assertEqual(self.line.enrollment_id, self.enrollment)
        self.assertEqual(self.line.course_id, self.course)
        self.assertEqual(self.line.state, 'enrolled')

    def test_grade_validation_below_zero(self):
        with self.assertRaises(ValidationError):
            self.line.write({'final_grade': -1.0})

    def test_grade_validation_above_100(self):
        with self.assertRaises(ValidationError):
            self.line.write({'final_grade': 101.0})

    def test_grade_valid_range(self):
        self.line.final_grade = 50.0
        self.assertEqual(self.line.final_grade, 50.0)
        self.line.final_grade = 100.0
        self.assertEqual(self.line.final_grade, 100.0)

    def test_unique_course_per_enrollment(self):
        with self.assertRaises(ValidationError):
            self.env['uni.student.enrollment.line'].create({
                'enrollment_id': self.enrollment.id,
                'course_id': self.course.id,
            })

    def test_different_courses_allowed(self):
        line2 = self.env['uni.student.enrollment.line'].create({
            'enrollment_id': self.enrollment.id,
            'course_id': self.course2.id,
        })
        self.assertEqual(len(self.enrollment.line_ids), 2)

    def test_grade_letter_suggestion_a(self):
        line = self.env['uni.student.enrollment.line'].new({
            'final_grade': 95.0,
        })
        line._onchange_final_grade()
        self.assertEqual(line.grade_letter, 'A')

    def test_grade_letter_suggestion_b(self):
        line = self.env['uni.student.enrollment.line'].new({
            'final_grade': 85.0,
        })
        line._onchange_final_grade()
        self.assertEqual(line.grade_letter, 'B')

    def test_grade_letter_suggestion_c(self):
        line = self.env['uni.student.enrollment.line'].new({
            'final_grade': 75.0,
        })
        line._onchange_final_grade()
        self.assertEqual(line.grade_letter, 'C')

    def test_grade_letter_suggestion_d(self):
        line = self.env['uni.student.enrollment.line'].new({
            'final_grade': 65.0,
        })
        line._onchange_final_grade()
        self.assertEqual(line.grade_letter, 'D')

    def test_grade_letter_suggestion_f(self):
        line = self.env['uni.student.enrollment.line'].new({
            'final_grade': 50.0,
        })
        line._onchange_final_grade()
        self.assertEqual(line.grade_letter, 'F')

    def test_action_complete_line(self):
        self.line.action_complete_line()
        self.assertEqual(self.line.state, 'completed')

    def test_action_drop(self):
        self.line.action_drop()
        self.assertEqual(self.line.state, 'dropped')

    def test_cannot_drop_completed(self):
        self.line.action_complete_line()
        with self.assertRaises(ValidationError):
            self.line.action_drop()

    def test_action_fail(self):
        self.line.action_fail()
        self.assertEqual(self.line.state, 'failed')

    def test_only_enrolled_can_complete(self):
        self.line.action_drop()
        with self.assertRaises(ValidationError):
            self.line.action_complete_line()


@tagged('post_install', '-at_install')
class TestStudentDocument(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
            'code': 'TU',
        })
        cls.person = cls.env['uni.person'].create({
            'name': 'Doc Student',
            'university_id': cls.university.id,
            'person_type': 'student',
        })
        cls.student = cls.env['uni.student'].create({
            'person_id': cls.person.id,
            'state': 'active',
        })

    def test_create_document(self):
        doc = self.env['uni.student.document'].create({
            'name': 'National ID',
            'student_id': self.student.id,
            'document_type': 'id_card',
            'issue_date': '2024-01-01',
            'expiry_date': '2029-01-01',
            'file': 'dGVzdA==',
            'filename': 'id_card.pdf',
        })
        self.assertEqual(doc.name, 'National ID')
        self.assertEqual(doc.document_type, 'id_card')
        self.assertFalse(doc.verified)

    def test_date_validation_expiry_before_issue(self):
        with self.assertRaises(ValidationError):
            self.env['uni.student.document'].create({
                'name': 'Bad Dates',
                'student_id': self.student.id,
                'document_type': 'passport',
                'issue_date': '2024-12-31',
                'expiry_date': '2024-01-01',
                'file': 'dGVzdA==',
            })

    def test_verified_requires_file(self):
        doc = self.env['uni.student.document'].create({
            'name': 'No File Doc',
            'student_id': self.student.id,
            'document_type': 'certificate',
            'file': False,
        })
        with self.assertRaises(ValidationError):
            doc.action_verify()

    def test_action_verify(self):
        doc = self.env['uni.student.document'].create({
            'name': 'Verify Me',
            'student_id': self.student.id,
            'document_type': 'certificate',
            'file': 'dGVzdA==',
        })
        doc.action_verify()
        self.assertTrue(doc.verified)
        self.assertEqual(doc.verified_by.id, self.env.uid)
        self.assertTrue(doc.verified_date)

    def test_action_unverify(self):
        doc = self.env['uni.student.document'].create({
            'name': 'Unverify Me',
            'student_id': self.student.id,
            'document_type': 'certificate',
            'file': 'dGVzdA==',
        })
        doc.action_verify()
        doc.action_unverify()
        self.assertFalse(doc.verified)

    def test_cannot_verify_already_verified(self):
        doc = self.env['uni.student.document'].create({
            'name': 'Already Verified',
            'student_id': self.student.id,
            'document_type': 'certificate',
            'file': 'dGVzdA==',
        })
        doc.action_verify()
        with self.assertRaises(ValidationError):
            doc.action_verify()

    def test_cannot_unverify_not_verified(self):
        doc = self.env['uni.student.document'].create({
            'name': 'Not Verified',
            'student_id': self.student.id,
            'document_type': 'certificate',
            'file': 'dGVzdA==',
        })
        with self.assertRaises(ValidationError):
            doc.action_unverify()


@tagged('post_install', '-at_install')
class TestStudentAdvisor(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
            'code': 'TU',
        })
        cls.person = cls.env['uni.person'].create({
            'name': 'Advised Student',
            'university_id': cls.university.id,
            'person_type': 'student',
        })
        cls.student = cls.env['uni.student'].create({
            'person_id': cls.person.id,
            'state': 'active',
        })
        cls.advisor = cls.env['uni.student.advisor'].create({
            'student_id': cls.student.id,
            'advisor_name': 'Prof. Smith',
            'advisor_role': 'academic',
            'start_date': '2024-09-01',
        })

    def test_create_advisor(self):
        self.assertTrue(self.advisor.name)
        self.assertEqual(self.advisor.advisor_name, 'Prof. Smith')
        self.assertEqual(self.advisor.advisor_role, 'academic')
        self.assertTrue(self.advisor.is_current)

    def test_single_current_advisor_per_role(self):
        with self.assertRaises(ValidationError):
            self.env['uni.student.advisor'].create({
                'student_id': self.student.id,
                'advisor_name': 'Prof. Jones',
                'advisor_role': 'academic',
                'start_date': '2024-09-01',
            })

    def test_different_role_allowed(self):
        self.env['uni.student.advisor'].create({
            'student_id': self.student.id,
            'advisor_name': 'Prof. Thesis',
            'advisor_role': 'thesis',
            'start_date': '2024-09-01',
        })
        advisors = self.env['uni.student.advisor'].search([
            ('student_id', '=', self.student.id),
        ])
        self.assertEqual(len(advisors), 2)

    def test_action_end_advisory(self):
        self.advisor.action_end_advisory()
        self.assertFalse(self.advisor.is_current)
        self.assertTrue(self.advisor.end_date)

    def test_date_validation(self):
        with self.assertRaises(Exception):
            self.env['uni.student.advisor'].create({
                'student_id': self.student.id,
                'advisor_name': 'Bad Dates',
                'advisor_role': 'mentor',
                'start_date': '2024-12-31',
                'end_date': '2024-09-01',
            })


@tagged('post_install', '-at_install')
class TestStudentTransfer(TransactionCase):

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
        cls.level = cls.env['uni.program.level'].create({
            'name': 'Bachelor',
            'code': 'BSC',
        })
        cls.program1 = cls.env['uni.program'].create({
            'name': 'BS Computer Science',
            'code': 'BSCS',
            'university_id': cls.university.id,
            'college_id': cls.college.id,
            'department_id': cls.department.id,
            'level_id': cls.level.id,
        })
        cls.program2 = cls.env['uni.program'].create({
            'name': 'BS Information Technology',
            'code': 'BSIT',
            'university_id': cls.university.id,
            'college_id': cls.college.id,
            'department_id': cls.department.id,
            'level_id': cls.level.id,
        })
        cls.person = cls.env['uni.person'].create({
            'name': 'Transfer Student',
            'university_id': cls.university.id,
            'person_type': 'student',
        })
        cls.student = cls.env['uni.student'].create({
            'person_id': cls.person.id,
            'program_id': cls.program1.id,
            'college_id': cls.college.id,
            'state': 'active',
        })

    def test_create_transfer(self):
        transfer = self.env['uni.student.transfer'].create({
            'student_id': self.student.id,
            'to_program_id': self.program2.id,
            'transfer_type': 'internal',
        })
        self.assertTrue(transfer.name)
        self.assertEqual(transfer.state, 'draft')

    def test_different_programs_validation(self):
        with self.assertRaises(ValidationError):
            self.env['uni.student.transfer'].create({
                'student_id': self.student.id,
                'from_program_id': self.program1.id,
                'to_program_id': self.program1.id,
            })

    def test_internal_transfer_requires_same_university(self):
        other_university = self.env['uni.university'].create({
            'name': 'Other University',
            'code': 'OU',
        })
        other_college = self.env['uni.college'].create({
            'name': 'Other College',
            'code': 'OC',
            'university_id': other_university.id,
        })
        other_dept = self.env['uni.department'].create({
            'name': 'Other Dept',
            'code': 'OD',
            'university_id': other_university.id,
            'college_id': other_college.id,
        })
        other_level = self.env['uni.program.level'].create({
            'name': 'Master',
            'code': 'MSC',
        })
        other_program = self.env['uni.program'].create({
            'name': 'MS Other',
            'code': 'MSO',
            'university_id': other_university.id,
            'college_id': other_college.id,
            'department_id': other_dept.id,
            'level_id': other_level.id,
        })
        with self.assertRaises(ValidationError):
            self.env['uni.student.transfer'].create({
                'student_id': self.student.id,
                'from_program_id': self.program1.id,
                'to_program_id': other_program.id,
                'transfer_type': 'internal',
            })

    def test_internal_transfer_requires_source(self):
        with self.assertRaises(ValidationError):
            self.env['uni.student.transfer'].create({
                'student_id': self.student.id,
                'to_program_id': self.program2.id,
                'transfer_type': 'internal',
            })

    def test_state_workflow_draft_to_approved(self):
        transfer = self.env['uni.student.transfer'].create({
            'student_id': self.student.id,
            'to_program_id': self.program2.id,
            'transfer_type': 'internal',
        })
        transfer.action_approve()
        self.assertEqual(transfer.state, 'approved')
        self.assertEqual(transfer.approved_by.id, self.env.uid)

    def test_state_workflow_approved_to_completed(self):
        transfer = self.env['uni.student.transfer'].create({
            'student_id': self.student.id,
            'to_program_id': self.program2.id,
            'transfer_type': 'internal',
        })
        transfer.action_approve()
        transfer.action_complete()
        self.assertEqual(transfer.state, 'completed')
        self.assertEqual(self.student.program_id, self.program2)

    def test_complete_updates_student(self):
        transfer = self.env['uni.student.transfer'].create({
            'student_id': self.student.id,
            'to_program_id': self.program2.id,
            'transfer_type': 'internal',
        })
        transfer.action_approve()
        transfer.action_complete()
        self.assertEqual(self.student.program_id, self.program2)
        self.assertEqual(self.student.college_id, self.program2.college_id)

    def test_approve_requires_draft(self):
        transfer = self.env['uni.student.transfer'].create({
            'student_id': self.student.id,
            'to_program_id': self.program2.id,
            'transfer_type': 'internal',
        })
        transfer.action_approve()
        with self.assertRaises(ValidationError):
            transfer.action_approve()

    def test_complete_requires_approved(self):
        transfer = self.env['uni.student.transfer'].create({
            'student_id': self.student.id,
            'to_program_id': self.program2.id,
            'transfer_type': 'internal',
        })
        with self.assertRaises(ValidationError):
            transfer.action_complete()

    def test_state_workflow_to_rejected(self):
        transfer = self.env['uni.student.transfer'].create({
            'student_id': self.student.id,
            'to_program_id': self.program2.id,
            'transfer_type': 'internal',
        })
        transfer.action_reject()
        self.assertEqual(transfer.state, 'rejected')

    def test_state_workflow_rejected_to_draft(self):
        transfer = self.env['uni.student.transfer'].create({
            'student_id': self.student.id,
            'to_program_id': self.program2.id,
            'transfer_type': 'internal',
        })
        transfer.action_reject()
        transfer.action_draft()
        self.assertEqual(transfer.state, 'draft')

    def test_cannot_reset_approved_to_draft(self):
        transfer = self.env['uni.student.transfer'].create({
            'student_id': self.student.id,
            'to_program_id': self.program2.id,
            'transfer_type': 'internal',
        })
        transfer.action_approve()
        with self.assertRaises(ValidationError):
            transfer.action_draft()

    def test_onchange_student_fills_from(self):
        transfer = self.env['uni.student.transfer'].new({
            'student_id': self.student.id,
        })
        transfer._onchange_student_id()
        self.assertEqual(transfer.from_program_id, self.program1)

    def test_onchange_to_program_fills_college(self):
        transfer = self.env['uni.student.transfer'].new({
            'to_program_id': self.program2.id,
        })
        transfer._onchange_to_program_id()
        self.assertEqual(transfer.to_college_id, self.program2.college_id)


@tagged('post_install', '-at_install')
class TestAttendance(TransactionCase):

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
        cls.course = cls.env['uni.course'].create({
            'name': 'Intro to Programming',
            'code': 'CS101',
            'university_id': cls.university.id,
            'college_id': cls.college.id,
        })
        cls.year = cls.env['uni.academic.year'].create({
            'name': '2024-2025',
            'code': '2024',
            'university_id': cls.university.id,
            'date_start': '2024-09-01',
            'date_end': '2025-06-30',
        })
        term_type = cls.env['uni.academic.term.type'].create({
            'name': 'Semester',
            'code': 'SEM',
            'terms_per_year': 2,
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
            'name': 'Attend Student',
            'university_id': cls.university.id,
            'person_type': 'student',
        })
        cls.student = cls.env['uni.student'].create({
            'person_id': cls.person.id,
            'state': 'active',
        })
        cls.attendance = cls.env['uni.attendance'].create({
            'course_id': cls.course.id,
            'academic_term_id': cls.term.id,
            'date': '2024-09-15',
            'session_type': 'lecture',
        })

    def test_create_attendance(self):
        self.assertTrue(self.attendance.name)
        self.assertEqual(self.attendance.state, 'draft')
        self.assertEqual(self.attendance.session_type, 'lecture')

    def test_date_in_term_validation_before(self):
        with self.assertRaises(ValidationError):
            self.env['uni.attendance'].create({
                'course_id': self.course.id,
                'academic_term_id': self.term.id,
                'date': '2024-08-01',
            })

    def test_date_in_term_validation_after(self):
        with self.assertRaises(ValidationError):
            self.env['uni.attendance'].create({
                'course_id': self.course.id,
                'academic_term_id': self.term.id,
                'date': '2025-01-01',
            })

    def test_state_workflow_draft_to_validated(self):
        self.env['uni.attendance.line'].create({
            'attendance_id': self.attendance.id,
            'student_id': self.student.id,
            'status': 'present',
        })
        self.attendance.action_validate()
        self.assertEqual(self.attendance.state, 'validated')

    def test_validate_requires_lines(self):
        with self.assertRaises(ValidationError):
            self.attendance.action_validate()

    def test_state_workflow_to_draft(self):
        self.env['uni.attendance.line'].create({
            'attendance_id': self.attendance.id,
            'student_id': self.student.id,
            'status': 'present',
        })
        self.attendance.action_validate()
        self.attendance.action_draft()
        self.assertEqual(self.attendance.state, 'draft')

    def test_line_count_computation(self):
        self.assertEqual(self.attendance.line_count, 0)

    def test_present_count_computation(self):
        self.assertEqual(self.attendance.present_count, 0)

    def test_absent_count_computation(self):
        self.assertEqual(self.attendance.absent_count, 0)

    def test_attendance_percentage_computation(self):
        self.assertEqual(self.attendance.attendance_percentage, 0.0)


@tagged('post_install', '-at_install')
class TestAttendanceLine(TransactionCase):

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
        cls.course = cls.env['uni.course'].create({
            'name': 'Intro to Programming',
            'code': 'CS101',
            'university_id': cls.university.id,
            'college_id': cls.college.id,
        })
        cls.year = cls.env['uni.academic.year'].create({
            'name': '2024-2025',
            'code': '2024',
            'university_id': cls.university.id,
            'date_start': '2024-09-01',
            'date_end': '2025-06-30',
        })
        term_type = cls.env['uni.academic.term.type'].create({
            'name': 'Semester',
            'code': 'SEM',
            'terms_per_year': 2,
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
        cls.person1 = cls.env['uni.person'].create({
            'name': 'Student One',
            'university_id': cls.university.id,
            'person_type': 'student',
        })
        cls.student1 = cls.env['uni.student'].create({
            'person_id': cls.person1.id,
            'state': 'active',
        })
        cls.person2 = cls.env['uni.person'].create({
            'name': 'Student Two',
            'university_id': cls.university.id,
            'person_type': 'student',
        })
        cls.student2 = cls.env['uni.student'].create({
            'person_id': cls.person2.id,
            'state': 'active',
        })
        cls.attendance = cls.env['uni.attendance'].create({
            'course_id': cls.course.id,
            'academic_term_id': cls.term.id,
            'date': '2024-09-15',
        })

    def test_create_line(self):
        line = self.env['uni.attendance.line'].create({
            'attendance_id': self.attendance.id,
            'student_id': self.student1.id,
            'status': 'present',
            'arrival_time': 9.0,
            'departure_time': 11.0,
        })
        self.assertEqual(line.status, 'present')
        self.assertEqual(line.arrival_time, 9.0)

    def test_time_validation_arrival_negative(self):
        with self.assertRaises(ValidationError):
            self.env['uni.attendance.line'].create({
                'attendance_id': self.attendance.id,
                'student_id': self.student1.id,
                'arrival_time': -1.0,
            })

    def test_time_validation_arrival_over_24(self):
        with self.assertRaises(ValidationError):
            self.env['uni.attendance.line'].create({
                'attendance_id': self.attendance.id,
                'student_id': self.student1.id,
                'arrival_time': 25.0,
            })

    def test_time_validation_departure_before_arrival(self):
        with self.assertRaises(ValidationError):
            self.env['uni.attendance.line'].create({
                'attendance_id': self.attendance.id,
                'student_id': self.student1.id,
                'arrival_time': 10.0,
                'departure_time': 9.0,
            })

    def test_unique_student_per_session(self):
        self.env['uni.attendance.line'].create({
            'attendance_id': self.attendance.id,
            'student_id': self.student1.id,
            'status': 'present',
        })
        with self.assertRaises(ValidationError):
            self.env['uni.attendance.line'].create({
                'attendance_id': self.attendance.id,
                'student_id': self.student1.id,
                'status': 'absent',
            })

    def test_different_students_allowed(self):
        self.env['uni.attendance.line'].create({
            'attendance_id': self.attendance.id,
            'student_id': self.student1.id,
            'status': 'present',
        })
        self.env['uni.attendance.line'].create({
            'attendance_id': self.attendance.id,
            'student_id': self.student2.id,
            'status': 'absent',
        })
        self.assertEqual(len(self.attendance.line_ids), 2)

    def test_minutes_late_non_negative(self):
        with self.assertRaises(ValidationError):
            self.env['uni.attendance.line'].create({
                'attendance_id': self.attendance.id,
                'student_id': self.student1.id,
                'minutes_late': -5,
            })

    def test_onchange_attendance_id_fills_student(self):
        line = self.env['uni.attendance.line'].new({
            'attendance_id': self.attendance.id,
        })
        line._onchange_attendance_id()
        self.assertFalse(line.student_id)

    def test_onchange_times_computes_late(self):
        line = self.env['uni.attendance.line'].new({
            'arrival_time': 9.5,
        })
        line._onchange_times()
        self.assertEqual(line.minutes_late, 570)
