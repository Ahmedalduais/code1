# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError
from odoo import fields


@tagged('post_install', '-at_install')
class TestGradebook(TransactionCase):

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
        cls.year = cls.env['uni.academic.year'].create({
            'name': '2025-2026',
            'code': '2025',
            'university_id': cls.university.id,
            'date_start': '2025-09-01',
            'date_end': '2026-06-30',
        })
        term_type = cls.env['uni.academic.term.type'].create({
            'name': 'Semester',
            'code': 'SEM',
            'terms_per_year': 2,
        })
        cls.term = cls.env['uni.academic.term'].create({
            'name': 'Fall 2025',
            'code': 'F25',
            'university_id': cls.university.id,
            'academic_year_id': cls.year.id,
            'term_type_id': term_type.id,
            'date_start': '2025-09-01',
            'date_end': '2025-12-31',
        })
        cls.grading_system = cls.env['uni.grading.system'].create({
            'name': 'Standard 4.0',
            'code': 'STD-4.0',
            'scale_max': 100.0,
            'passing_grade': 60.0,
            'gpa_scale': 4.0,
            'system_type': 'percentage',
        })
        cls.person = cls.env['uni.person'].create({
            'name': 'Grade Student',
            'university_id': cls.university.id,
            'person_type': 'student',
        })
        cls.student = cls.env['uni.student'].create({
            'person_id': cls.person.id,
            'program_id': cls.program.id,
            'college_id': cls.college.id,
            'state': 'active',
        })
        cls.gradebook = cls.env['uni.gradebook'].create({
            'course_id': cls.course.id,
            'academic_term_id': cls.term.id,
            'grading_system_id': cls.grading_system.id,
            'section': 'A',
            'faculty_name': 'Prof. Smith',
        })

    def test_create_gradebook(self):
        self.assertTrue(self.gradebook.name)
        self.assertEqual(self.gradebook.course_id, self.course)
        self.assertEqual(self.gradebook.state, 'draft')

    def test_unique_course_term_section(self):
        with self.assertRaises(Exception):
            self.env['uni.gradebook'].create({
                'course_id': self.course.id,
                'academic_term_id': self.term.id,
                'grading_system_id': self.grading_system.id,
                'section': 'A',
            })

    def test_state_workflow_draft_to_active(self):
        self.env['uni.gradebook.line'].create({
            'gradebook_id': self.gradebook.id,
            'student_id': self.student.id,
        })
        self.gradebook.action_activate()
        self.assertEqual(self.gradebook.state, 'active')
        self.assertTrue(self.gradebook.publish_date)

    def test_activate_requires_lines(self):
        with self.assertRaises(ValidationError):
            self.gradebook.action_activate()

    def test_state_workflow_active_to_locked(self):
        self.env['uni.gradebook.line'].create({
            'gradebook_id': self.gradebook.id,
            'student_id': self.student.id,
        })
        self.gradebook.action_activate()
        self.gradebook.action_lock()
        self.assertEqual(self.gradebook.state, 'locked')
        self.assertTrue(self.gradebook.lock_date)

    def test_state_workflow_locked_to_closed(self):
        self.env['uni.gradebook.line'].create({
            'gradebook_id': self.gradebook.id,
            'student_id': self.student.id,
        })
        self.gradebook.action_activate()
        self.gradebook.action_lock()
        self.gradebook.action_close()
        self.assertEqual(self.gradebook.state, 'closed')

    def test_state_workflow_to_draft(self):
        self.env['uni.gradebook.line'].create({
            'gradebook_id': self.gradebook.id,
            'student_id': self.student.id,
        })
        self.gradebook.action_activate()
        self.gradebook.action_draft()
        self.assertEqual(self.gradebook.state, 'draft')

    def test_cannot_reset_closed_to_draft(self):
        self.env['uni.gradebook.line'].create({
            'gradebook_id': self.gradebook.id,
            'student_id': self.student.id,
        })
        self.gradebook.action_activate()
        self.gradebook.action_lock()
        self.gradebook.action_close()
        with self.assertRaises(ValidationError):
            self.gradebook.action_draft()

    def test_average_computation(self):
        self.assertEqual(self.gradebook.average_score, 0.0)

    def test_pass_rate_computation(self):
        self.assertEqual(self.gradebook.pass_rate, 0.0)


@tagged('post_install', '-at_install')
class TestGradebookLine(TransactionCase):

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
            'credit_hours': 3.0,
        })
        cls.year = cls.env['uni.academic.year'].create({
            'name': '2025-2026',
            'code': '2025',
            'university_id': cls.university.id,
            'date_start': '2025-09-01',
            'date_end': '2026-06-30',
        })
        term_type = cls.env['uni.academic.term.type'].create({
            'name': 'Semester',
            'code': 'SEM',
            'terms_per_year': 2,
        })
        cls.term = cls.env['uni.academic.term'].create({
            'name': 'Fall 2025',
            'code': 'F25',
            'university_id': cls.university.id,
            'academic_year_id': cls.year.id,
            'term_type_id': term_type.id,
            'date_start': '2025-09-01',
            'date_end': '2025-12-31',
        })
        cls.grading_system = cls.env['uni.grading.system'].create({
            'name': 'Standard 4.0',
            'code': 'STD-4.0',
            'scale_max': 100.0,
            'passing_grade': 60.0,
            'gpa_scale': 4.0,
        })
        cls.gradebook = cls.env['uni.gradebook'].create({
            'course_id': cls.course.id,
            'academic_term_id': cls.term.id,
            'grading_system_id': cls.grading_system.id,
            'section': 'A',
        })
        cls.person = cls.env['uni.person'].create({
            'name': 'Line Student',
            'university_id': cls.university.id,
            'person_type': 'student',
        })
        cls.student = cls.env['uni.student'].create({
            'person_id': cls.person.id,
            'program_id': cls.college.program_ids[:1].id if cls.college.program_ids else False,
            'college_id': cls.college.id,
            'state': 'active',
        })
        cls.line = cls.env['uni.gradebook.line'].create({
            'gradebook_id': cls.gradebook.id,
            'student_id': cls.student.id,
        })

    def test_create_line(self):
        self.assertTrue(self.line.name)
        self.assertEqual(self.line.state, 'active')

    def test_unique_student_per_gradebook(self):
        with self.assertRaises(Exception):
            self.env['uni.gradebook.line'].create({
                'gradebook_id': self.gradebook.id,
                'student_id': self.student.id,
            })

    def test_state_workflow_to_withdrawn(self):
        self.line.action_withdraw()
        self.assertEqual(self.line.state, 'withdrawn')
        self.assertTrue(self.line.is_withdrawn)

    def test_state_workflow_to_exempted(self):
        self.line.action_exempt()
        self.assertEqual(self.line.state, 'exempted')

    def test_reactivate_from_withdrawn(self):
        self.line.action_withdraw()
        self.line.action_reactivate()
        self.assertEqual(self.line.state, 'active')
        self.assertFalse(self.line.is_withdrawn)

    def test_cannot_withdraw_exempted(self):
        self.line.action_exempt()
        with self.assertRaises(ValidationError):
            self.line.action_withdraw()


@tagged('post_install', '-at_install')
class TestGradebookEntry(TransactionCase):

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
            'credit_hours': 3.0,
        })
        cls.year = cls.env['uni.academic.year'].create({
            'name': '2025-2026',
            'code': '2025',
            'university_id': cls.university.id,
            'date_start': '2025-09-01',
            'date_end': '2026-06-30',
        })
        term_type = cls.env['uni.academic.term.type'].create({
            'name': 'Semester',
            'code': 'SEM',
            'terms_per_year': 2,
        })
        cls.term = cls.env['uni.academic.term'].create({
            'name': 'Fall 2025',
            'code': 'F25',
            'university_id': cls.university.id,
            'academic_year_id': cls.year.id,
            'term_type_id': term_type.id,
            'date_start': '2025-09-01',
            'date_end': '2025-12-31',
        })
        cls.grading_system = cls.env['uni.grading.system'].create({
            'name': 'Standard 4.0',
            'code': 'STD-4.0',
            'scale_max': 100.0,
            'passing_grade': 60.0,
            'gpa_scale': 4.0,
        })
        cls.gradebook = cls.env['uni.gradebook'].create({
            'course_id': cls.course.id,
            'academic_term_id': cls.term.id,
            'grading_system_id': cls.grading_system.id,
            'section': 'A',
        })
        cls.person = cls.env['uni.person'].create({
            'name': 'Entry Student',
            'university_id': cls.university.id,
            'person_type': 'student',
        })
        cls.student = cls.env['uni.student'].create({
            'person_id': cls.person.id,
            'college_id': cls.college.id,
            'state': 'active',
        })
        cls.line = cls.env['uni.gradebook.line'].create({
            'gradebook_id': cls.gradebook.id,
            'student_id': cls.student.id,
        })
        cls.entry = cls.env['uni.gradebook.entry'].create({
            'gradebook_line_id': cls.line.id,
            'assessment_name': 'Midterm Exam',
            'score': 85.0,
            'max_score': 100.0,
            'weight': 30.0,
        })

    def test_create_entry(self):
        self.assertTrue(self.entry.name)
        self.assertEqual(self.entry.score, 85.0)
        self.assertEqual(self.entry.percentage, 85.0)

    def test_score_range_validation_negative(self):
        with self.assertRaises(ValidationError):
            self.env['uni.gradebook.entry'].create({
                'gradebook_line_id': self.line.id,
                'assessment_name': 'Bad Score',
                'score': -1.0,
                'max_score': 100.0,
            })

    def test_score_range_validation_exceeds_max(self):
        with self.assertRaises(ValidationError):
            self.env['uni.gradebook.entry'].create({
                'gradebook_line_id': self.line.id,
                'assessment_name': 'Over Max',
                'score': 101.0,
                'max_score': 100.0,
            })

    def test_weight_range_validation(self):
        with self.assertRaises(ValidationError):
            self.env['uni.gradebook.entry'].create({
                'gradebook_line_id': self.line.id,
                'assessment_name': 'Bad Weight',
                'weight': 101.0,
            })

    def test_unique_assessment_per_student(self):
        with self.assertRaises(Exception):
            self.env['uni.gradebook.entry'].create({
                'gradebook_line_id': self.line.id,
                'assessment_name': 'Midterm Exam',
                'score': 90.0,
            })


@tagged('post_install', '-at_install')
class TestGradebookFinal(TransactionCase):

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
            'credit_hours': 3.0,
        })
        cls.year = cls.env['uni.academic.year'].create({
            'name': '2025-2026',
            'code': '2025',
            'university_id': cls.university.id,
            'date_start': '2025-09-01',
            'date_end': '2026-06-30',
        })
        term_type = cls.env['uni.academic.term.type'].create({
            'name': 'Semester',
            'code': 'SEM',
            'terms_per_year': 2,
        })
        cls.term = cls.env['uni.academic.term'].create({
            'name': 'Fall 2025',
            'code': 'F25',
            'university_id': cls.university.id,
            'academic_year_id': cls.year.id,
            'term_type_id': term_type.id,
            'date_start': '2025-09-01',
            'date_end': '2025-12-31',
        })
        cls.grading_system = cls.env['uni.grading.system'].create({
            'name': 'Standard 4.0',
            'code': 'STD-4.0',
            'scale_max': 100.0,
            'passing_grade': 60.0,
            'gpa_scale': 4.0,
        })
        cls.gradebook = cls.env['uni.gradebook'].create({
            'course_id': cls.course.id,
            'academic_term_id': cls.term.id,
            'grading_system_id': cls.grading_system.id,
            'section': 'A',
        })
        cls.person = cls.env['uni.person'].create({
            'name': 'Final Student',
            'university_id': cls.university.id,
            'person_type': 'student',
        })
        cls.student = cls.env['uni.student'].create({
            'person_id': cls.person.id,
            'college_id': cls.college.id,
            'state': 'active',
        })
        cls.line = cls.env['uni.gradebook.line'].create({
            'gradebook_id': cls.gradebook.id,
            'student_id': cls.student.id,
        })
        cls.final = cls.env['uni.gradebook.final'].create({
            'gradebook_id': cls.gradebook.id,
            'gradebook_line_id': cls.line.id,
        })

    def test_create_final(self):
        self.assertTrue(self.final.name)
        self.assertEqual(self.final.state, 'computed')

    def test_unique_per_line(self):
        with self.assertRaises(Exception):
            self.env['uni.gradebook.final'].create({
                'gradebook_id': self.gradebook.id,
                'gradebook_line_id': self.line.id,
            })

    def test_final_score_computation(self):
        self.env['uni.gradebook.entry'].create({
            'gradebook_line_id': self.line.id,
            'assessment_name': 'Midterm',
            'score': 80.0,
            'max_score': 100.0,
            'weight': 50.0,
        })
        self.env['uni.gradebook.entry'].create({
            'gradebook_line_id': self.line.id,
            'assessment_name': 'Final',
            'score': 90.0,
            'max_score': 100.0,
            'weight': 50.0,
        })
        self.final._compute_final_score()
        self.final._compute_final_percentage()
        expected_score = 80.0 * 50.0 / 100.0 + 90.0 * 50.0 / 100.0
        self.assertAlmostEqual(self.final.final_score, expected_score, places=2)

    def test_is_passing_computation(self):
        self.env['uni.gradebook.entry'].create({
            'gradebook_line_id': self.line.id,
            'assessment_name': 'Test',
            'score': 80.0,
            'max_score': 100.0,
            'weight': 100.0,
        })
        self.final._compute_final_score()
        self.final._compute_final_percentage()
        self.final._compute_is_passing()
        self.assertTrue(self.final.is_passing)

    def test_rank_computation(self):
        person2 = self.env['uni.person'].create({
            'name': 'Rank Student 2',
            'university_id': self.university.id,
            'person_type': 'student',
        })
        student2 = self.env['uni.student'].create({
            'person_id': person2.id,
            'college_id': self.college.id,
            'state': 'active',
        })
        line2 = self.env['uni.gradebook.line'].create({
            'gradebook_id': self.gradebook.id,
            'student_id': student2.id,
        })
        final2 = self.env['uni.gradebook.final'].create({
            'gradebook_id': self.gradebook.id,
            'gradebook_line_id': line2.id,
        })
        self.env['uni.gradebook.entry'].create({
            'gradebook_line_id': self.line.id,
            'assessment_name': 'Test',
            'score': 90.0,
            'max_score': 100.0,
            'weight': 100.0,
        })
        self.env['uni.gradebook.entry'].create({
            'gradebook_line_id': line2.id,
            'assessment_name': 'Test',
            'score': 70.0,
            'max_score': 100.0,
            'weight': 100.0,
        })
        self.final._compute_final_score()
        self.final._compute_final_percentage()
        final2._compute_final_score()
        final2._compute_final_percentage()
        self.final._compute_rank()
        final2._compute_rank()
        self.assertEqual(self.final.rank, 1)
        self.assertEqual(final2.rank, 2)


@tagged('post_install', '-at_install')
class TestGradebookApproval(TransactionCase):

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
            'name': '2025-2026',
            'code': '2025',
            'university_id': cls.university.id,
            'date_start': '2025-09-01',
            'date_end': '2026-06-30',
        })
        term_type = cls.env['uni.academic.term.type'].create({
            'name': 'Semester',
            'code': 'SEM',
            'terms_per_year': 2,
        })
        cls.term = cls.env['uni.academic.term'].create({
            'name': 'Fall 2025',
            'code': 'F25',
            'university_id': cls.university.id,
            'academic_year_id': cls.year.id,
            'term_type_id': term_type.id,
            'date_start': '2025-09-01',
            'date_end': '2025-12-31',
        })
        cls.grading_system = cls.env['uni.grading.system'].create({
            'name': 'Standard 4.0',
            'code': 'STD-4.0',
            'scale_max': 100.0,
            'passing_grade': 60.0,
            'gpa_scale': 4.0,
        })
        cls.gradebook = cls.env['uni.gradebook'].create({
            'course_id': cls.course.id,
            'academic_term_id': cls.term.id,
            'grading_system_id': cls.grading_system.id,
            'section': 'A',
        })
        cls.approval = cls.env['uni.gradebook.approval'].create({
            'gradebook_id': cls.gradebook.id,
            'approval_type': 'submission',
        })

    def test_create_approval(self):
        self.assertTrue(self.approval.name)
        self.assertEqual(self.approval.state, 'draft')

    def test_state_workflow_draft_to_submitted(self):
        self.approval.action_submit()
        self.assertEqual(self.approval.state, 'submitted')

    def test_state_workflow_submitted_to_under_review(self):
        self.approval.action_submit()
        self.approval.action_start_review()
        self.assertEqual(self.approval.state, 'under_review')
        self.assertTrue(self.approval.reviewed_by)

    def test_state_workflow_under_review_to_approved(self):
        self.approval.action_submit()
        self.approval.action_start_review()
        self.approval.action_approve()
        self.assertEqual(self.approval.state, 'approved')
        self.assertTrue(self.approval.approved_by)

    def test_state_workflow_approved_to_published(self):
        self.approval.action_submit()
        self.approval.action_start_review()
        self.approval.action_approve()
        self.approval.action_publish()
        self.assertEqual(self.approval.state, 'published')
        self.assertTrue(self.approval.published_by)

    def test_state_workflow_to_rejected(self):
        self.approval.action_submit()
        self.approval.action_start_review()
        self.approval.action_reject()
        self.assertEqual(self.approval.state, 'rejected')

    def test_state_workflow_to_cancelled(self):
        self.approval.action_cancel()
        self.assertEqual(self.approval.state, 'cancelled')


@tagged('post_install', '-at_install')
class TestTranscript(TransactionCase):

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
            'name': 'Transcript Student',
            'university_id': cls.university.id,
            'person_type': 'student',
        })
        cls.student = cls.env['uni.student'].create({
            'person_id': cls.person.id,
            'college_id': cls.college.id,
            'state': 'active',
        })
        cls.transcript = cls.env['uni.transcript'].create({
            'student_id': cls.student.id,
        })

    def test_create_transcript(self):
        self.assertTrue(self.transcript.name)
        self.assertEqual(self.transcript.state, 'draft')

    def test_state_workflow_draft_to_issued(self):
        self.transcript.action_issue()
        self.assertEqual(self.transcript.state, 'issued')
        self.assertTrue(self.transcript.issue_date)

    def test_state_workflow_issued_to_verified(self):
        self.transcript.action_issue()
        self.transcript.action_verify()
        self.assertEqual(self.transcript.state, 'verified')
        self.assertTrue(self.transcript.official_stamp)

    def test_state_workflow_to_revoked(self):
        self.transcript.action_issue()
        self.transcript.action_revoke()
        self.assertEqual(self.transcript.state, 'revoked')
        self.assertFalse(self.transcript.official_stamp)

    def test_cannot_revoke_draft(self):
        with self.assertRaises(ValidationError):
            self.transcript.action_revoke()

    def test_state_workflow_to_draft_from_issued(self):
        self.transcript.action_issue()
        self.transcript.action_draft()
        self.assertEqual(self.transcript.state, 'draft')

    def test_cannot_reset_verified_to_draft(self):
        self.transcript.action_issue()
        self.transcript.action_verify()
        with self.assertRaises(ValidationError):
            self.transcript.action_draft()


@tagged('post_install', '-at_install')
class TestGpaCalculation(TransactionCase):

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
            'name': 'GPA Student',
            'university_id': cls.university.id,
            'person_type': 'student',
        })
        cls.student = cls.env['uni.student'].create({
            'person_id': cls.person.id,
            'college_id': cls.college.id,
            'state': 'active',
        })
        cls.grading_system = cls.env['uni.grading.system'].create({
            'name': 'Standard 4.0',
            'code': 'STD-4.0',
            'scale_max': 100.0,
            'passing_grade': 60.0,
            'gpa_scale': 4.0,
        })
        cls.year = cls.env['uni.academic.year'].create({
            'name': '2025-2026',
            'code': '2025',
            'university_id': cls.university.id,
            'date_start': '2025-09-01',
            'date_end': '2026-06-30',
        })
        term_type = cls.env['uni.academic.term.type'].create({
            'name': 'Semester',
            'code': 'SEM',
            'terms_per_year': 2,
        })
        cls.term = cls.env['uni.academic.term'].create({
            'name': 'Fall 2025',
            'code': 'F25',
            'university_id': cls.university.id,
            'academic_year_id': cls.year.id,
            'term_type_id': term_type.id,
            'date_start': '2025-09-01',
            'date_end': '2025-12-31',
        })
        cls.course = cls.env['uni.course'].create({
            'name': 'Intro to Programming',
            'code': 'CS101',
            'university_id': cls.university.id,
            'college_id': cls.college.id,
            'credit_hours': 3.0,
        })
        cls.gradebook = cls.env['uni.gradebook'].create({
            'course_id': cls.course.id,
            'academic_term_id': cls.term.id,
            'grading_system_id': cls.grading_system.id,
            'section': 'A',
        })
        cls.gpa_calc = cls.env['uni.gpa.calculation'].create({
            'student_id': cls.student.id,
            'university_id': cls.university.id,
            'grading_system_id': cls.grading_system.id,
            'academic_term_id': cls.term.id,
        })

    def test_create_gpa_calculation(self):
        self.assertTrue(self.gpa_calc.name)
        self.assertEqual(self.gpa_calc.state, 'draft')

    def test_calculate_term_gpa_with_finals(self):
        line = self.env['uni.gradebook.line'].create({
            'gradebook_id': self.gradebook.id,
            'student_id': self.student.id,
        })
        final = self.env['uni.gradebook.final'].create({
            'gradebook_id': self.gradebook.id,
            'gradebook_line_id': line.id,
        })
        self.env['uni.gradebook.entry'].create({
            'gradebook_line_id': line.id,
            'assessment_name': 'Final',
            'score': 85.0,
            'max_score': 100.0,
            'weight': 100.0,
        })
        final._compute_final_score()
        final._compute_final_percentage()
        final._compute_grade_letter()
        final._compute_gpa_value()
        self.gpa_calc.write({'final_ids': [(6, 0, [final.id])]})
        self.gpa_calc.action_calculate_term_gpa()
        self.assertEqual(self.gpa_calc.state, 'calculated')
        self.assertGreater(self.gpa_calc.term_gpa, 0.0)

    def test_calculate_term_gpa_no_finals(self):
        self.gpa_calc.action_calculate_term_gpa()
        self.assertEqual(self.gpa_calc.term_gpa, 0.0)
        self.assertEqual(self.gpa_calc.state, 'calculated')
