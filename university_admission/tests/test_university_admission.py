# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError
from odoo import fields


@tagged('post_install', '-at_install')
class TestAdmissionCriteria(TransactionCase):

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
        cls.criteria = cls.env['uni.admission.criteria'].create({
            'name': 'Standard Admission Criteria',
            'code': 'CRIT-STD-001',
            'university_id': cls.university.id,
            'college_id': cls.college.id,
            'program_id': cls.program.id,
            'min_high_school_grade': 70.0,
            'min_gpa': 2.5,
            'min_test_score': 1000.0,
            'min_age': 16,
            'max_age': 30,
            'interview_required': False,
            'application_fee': 50.0,
            'is_active': True,
        })

    def test_create_criteria(self):
        self.assertEqual(self.criteria.name, 'Standard Admission Criteria')
        self.assertEqual(self.criteria.code, 'CRIT-STD-001')
        self.assertEqual(self.criteria.university_id, self.university)
        self.assertEqual(self.criteria.min_high_school_grade, 70.0)
        self.assertEqual(self.criteria.min_gpa, 2.5)
        self.assertTrue(self.criteria.is_active)

    def test_code_uniqueness(self):
        with self.assertRaises(Exception):
            self.env['uni.admission.criteria'].create({
                'name': 'Duplicate Criteria',
                'code': 'CRIT-STD-001',
                'university_id': self.university.id,
            })

    def test_age_range_validation_max_below_min(self):
        with self.assertRaises(ValidationError):
            self.env['uni.admission.criteria'].create({
                'name': 'Bad Age Criteria',
                'code': 'CRIT-BAD-AGE',
                'university_id': self.university.id,
                'min_age': 30,
                'max_age': 16,
            })

    def test_age_range_validation_negative_min(self):
        with self.assertRaises(ValidationError):
            self.env['uni.admission.criteria'].create({
                'name': 'Negative Min Age',
                'code': 'CRIT-NEG-AGE',
                'university_id': self.university.id,
                'min_age': -1,
            })

    def test_threshold_validation_negative_gpa(self):
        with self.assertRaises(ValidationError):
            self.env['uni.admission.criteria'].create({
                'name': 'Negative GPA',
                'code': 'CRIT-NEG-GPA',
                'university_id': self.university.id,
                'min_gpa': -1.0,
            })

    def test_threshold_validation_negative_grade(self):
        with self.assertRaises(ValidationError):
            self.env['uni.admission.criteria'].create({
                'name': 'Negative Grade',
                'code': 'CRIT-NEG-GRD',
                'university_id': self.university.id,
                'min_high_school_grade': -1.0,
            })

    def test_evaluate_application_passes(self):
        application = self.env['uni.admission.application'].create({
            'applicant_name': 'Test Applicant',
            'applicant_email': 'test@example.com',
            'university_id': self.university.id,
            'program_id': self.program.id,
            'college_id': self.college.id,
            'high_school_grade': 85.0,
            'high_school_grade_type': 'percentage',
            'applicant_birth_date': '2000-01-01',
        })
        result = self.criteria.evaluate_application(application)
        self.assertTrue(result)

    def test_evaluate_application_fails_low_grade(self):
        application = self.env['uni.admission.application'].create({
            'applicant_name': 'Low Grade Applicant',
            'applicant_email': 'low@example.com',
            'university_id': self.university.id,
            'program_id': self.program.id,
            'high_school_grade': 50.0,
            'high_school_grade_type': 'percentage',
            'applicant_birth_date': '2000-01-01',
        })
        result = self.criteria.evaluate_application(application)
        self.assertFalse(result)

    def test_evaluate_application_empty_returns_false(self):
        result = self.criteria.evaluate_application(False)
        self.assertFalse(result)


@tagged('post_install', '-at_install')
class TestAdmissionRequirement(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
            'code': 'TU',
        })
        cls.requirement = cls.env['uni.admission.requirement'].create({
            'name': 'High School Transcript',
            'code': 'REQ-HST-001',
            'requirement_type': 'document',
            'is_mandatory': True,
        })

    def test_create_requirement(self):
        self.assertEqual(self.requirement.name, 'High School Transcript')
        self.assertEqual(self.requirement.code, 'REQ-HST-001')
        self.assertTrue(self.requirement.is_mandatory)
        self.assertEqual(self.requirement.requirement_type, 'document')

    def test_code_uniqueness(self):
        with self.assertRaises(Exception):
            self.env['uni.admission.requirement'].create({
                'name': 'Duplicate Requirement',
                'code': 'REQ-HST-001',
            })


@tagged('post_install', '-at_install')
class TestAdmissionRequirementLine(TransactionCase):

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
        cls.requirement = cls.env['uni.admission.requirement'].create({
            'name': 'High School Transcript',
            'code': 'REQ-HST-001',
            'requirement_type': 'document',
            'is_mandatory': True,
        })
        cls.application = cls.env['uni.admission.application'].create({
            'applicant_name': 'Test Applicant',
            'applicant_email': 'test@example.com',
            'university_id': cls.university.id,
            'college_id': cls.college.id,
        })
        cls.line = cls.env['uni.admission.requirement.line'].create({
            'application_id': cls.application.id,
            'requirement_id': cls.requirement.id,
        })

    def test_create_line(self):
        self.assertEqual(self.line.application_id, self.application)
        self.assertEqual(self.line.requirement_id, self.requirement)
        self.assertFalse(self.line.is_fulfilled)

    def test_unique_application_requirement(self):
        with self.assertRaises(Exception):
            self.env['uni.admission.requirement.line'].create({
                'application_id': self.application.id,
                'requirement_id': self.requirement.id,
            })

    def test_document_requires_file_for_fulfilled(self):
        with self.assertRaises(ValidationError):
            self.line.write({
                'is_fulfilled': True,
                'file': False,
            })

    def test_mark_fulfilled_with_file(self):
        self.line.write({
            'file': 'dGVzdA==',
            'filename': 'transcript.pdf',
            'is_fulfilled': True,
        })
        self.assertTrue(self.line.is_fulfilled)
        self.assertTrue(self.line.fulfilled_date)

    def test_action_mark_unfulfilled(self):
        self.line.write({
            'file': 'dGVzdA==',
            'is_fulfilled': True,
        })
        self.line.action_mark_unfulfilled()
        self.assertFalse(self.line.is_fulfilled)


@tagged('post_install', '-at_install')
class TestAdmissionApplication(TransactionCase):

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
        cls.application = cls.env['uni.admission.application'].create({
            'applicant_name': 'Ahmed Student',
            'applicant_email': 'ahmed@example.com',
            'applicant_phone': '+1234567890',
            'university_id': cls.university.id,
            'college_id': cls.college.id,
            'department_id': cls.department.id,
            'program_id': cls.program.id,
            'level_id': cls.level.id,
            'academic_term_id': cls.term.id,
            'high_school_name': 'Test High School',
            'high_school_graduation_year': 2025,
            'high_school_grade': 85.0,
            'high_school_grade_type': 'percentage',
        })

    def test_create_application(self):
        self.assertTrue(self.application.name)
        self.assertEqual(self.application.applicant_name, 'Ahmed Student')
        self.assertEqual(self.application.status, 'draft')
        self.assertEqual(self.application.university_id, self.university)

    def test_email_format_validation(self):
        with self.assertRaises(ValidationError):
            self.env['uni.admission.application'].create({
                'applicant_name': 'Bad Email',
                'applicant_email': 'not-an-email',
                'university_id': self.university.id,
            })

    def test_graduation_year_validation_future(self):
        current_year = fields.Date.today().year
        with self.assertRaises(ValidationError):
            self.env['uni.admission.application'].create({
                'applicant_name': 'Future Grad',
                'university_id': self.university.id,
                'high_school_graduation_year': current_year + 3,
            })

    def test_high_school_grade_percentage_validation(self):
        with self.assertRaises(ValidationError):
            self.env['uni.admission.application'].create({
                'applicant_name': 'Bad Grade',
                'university_id': self.university.id,
                'high_school_grade': 105.0,
                'high_school_grade_type': 'percentage',
            })

    def test_high_school_grade_gpa_validation(self):
        with self.assertRaises(ValidationError):
            self.env['uni.admission.application'].create({
                'applicant_name': 'Bad GPA',
                'university_id': self.university.id,
                'high_school_grade': 11.0,
                'high_school_grade_type': 'gpa',
            })

    def test_state_workflow_draft_to_submitted(self):
        self.application.action_submit()
        self.assertEqual(self.application.status, 'submitted')
        self.assertTrue(self.application.submission_date)

    def test_submit_requires_email_or_mobile(self):
        app = self.env['uni.admission.application'].create({
            'applicant_name': 'No Contact',
            'university_id': self.university.id,
        })
        with self.assertRaises(ValidationError):
            app.action_submit()

    def test_state_workflow_submitted_to_under_review(self):
        self.application.action_submit()
        self.application.action_review()
        self.assertEqual(self.application.status, 'under_review')

    def test_state_workflow_under_review_to_interview(self):
        self.application.action_submit()
        self.application.action_review()
        self.env['uni.admission.interview'].create({
            'application_id': self.application.id,
            'interviewer_name': 'Prof. Smith',
            'start_time': 9.0,
            'end_time': 10.0,
        })
        self.application.action_schedule_interview()
        self.assertEqual(self.application.status, 'interview_scheduled')

    def test_state_workflow_to_accepted(self):
        self.application.action_submit()
        self.application.action_accept()
        self.assertEqual(self.application.status, 'accepted')

    def test_state_workflow_to_rejected(self):
        self.application.action_submit()
        self.application.action_reject()
        self.assertEqual(self.application.status, 'rejected')

    def test_action_enroll_creates_student(self):
        self.application.action_submit()
        self.application.action_accept()
        self.application.action_enroll()
        self.assertEqual(self.application.status, 'enrolled')
        self.assertTrue(self.application.student_id)
        self.assertEqual(self.application.student_id.name, 'Ahmed Student')

    def test_cannot_enroll_non_accepted(self):
        self.application.action_submit()
        with self.assertRaises(ValidationError):
            self.application.action_enroll()

    def test_cannot_enroll_twice(self):
        self.application.action_submit()
        self.application.action_accept()
        self.application.action_enroll()
        with self.assertRaises(ValidationError):
            self.application.action_enroll()

    def test_cannot_submit_non_draft(self):
        self.application.action_submit()
        with self.assertRaises(ValidationError):
            self.application.action_submit()

    def test_cannot_review_non_submitted(self):
        with self.assertRaises(ValidationError):
            self.application.action_review()


@tagged('post_install', '-at_install')
class TestAdmissionInterview(TransactionCase):

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
        cls.application = cls.env['uni.admission.application'].create({
            'applicant_name': 'Interview Applicant',
            'applicant_email': 'interview@example.com',
            'university_id': cls.university.id,
            'college_id': cls.college.id,
        })
        cls.interview = cls.env['uni.admission.interview'].create({
            'application_id': cls.application.id,
            'interviewer_name': 'Prof. Smith',
            'interview_date': '2025-10-01',
            'start_time': 9.0,
            'end_time': 10.0,
            'location': 'Room 101',
            'score': 85.0,
            'score_max': 100.0,
        })

    def test_create_interview(self):
        self.assertTrue(self.interview.name)
        self.assertEqual(self.interview.interviewer_name, 'Prof. Smith')
        self.assertEqual(self.interview.state, 'scheduled')

    def test_time_validation_start_over_24(self):
        with self.assertRaises(ValidationError):
            self.env['uni.admission.interview'].create({
                'application_id': self.application.id,
                'interviewer_name': 'Prof. Bad',
                'start_time': 25.0,
                'end_time': 26.0,
            })

    def test_time_validation_end_before_start(self):
        with self.assertRaises(ValidationError):
            self.env['uni.admission.interview'].create({
                'application_id': self.application.id,
                'interviewer_name': 'Prof. Bad',
                'start_time': 10.0,
                'end_time': 9.0,
            })

    def test_score_range_validation_negative(self):
        with self.assertRaises(ValidationError):
            self.env['uni.admission.interview'].create({
                'application_id': self.application.id,
                'interviewer_name': 'Prof. Bad',
                'score': -1.0,
                'score_max': 100.0,
            })

    def test_score_range_validation_exceeds_max(self):
        with self.assertRaises(ValidationError):
            self.env['uni.admission.interview'].create({
                'application_id': self.application.id,
                'interviewer_name': 'Prof. Bad',
                'score': 101.0,
                'score_max': 100.0,
            })

    def test_online_requires_url(self):
        with self.assertRaises(ValidationError):
            self.env['uni.admission.interview'].create({
                'application_id': self.application.id,
                'interviewer_name': 'Prof. Online',
                'is_online': True,
                'meeting_url': False,
            })

    def test_state_workflow_scheduled_to_completed(self):
        self.interview.action_complete()
        self.assertEqual(self.interview.state, 'completed')

    def test_state_workflow_to_cancelled(self):
        self.interview.action_cancel()
        self.assertEqual(self.interview.state, 'cancelled')

    def test_state_workflow_to_no_show(self):
        self.interview.action_no_show()
        self.assertEqual(self.interview.state, 'no_show')

    def test_cannot_complete_non_scheduled(self):
        self.interview.action_complete()
        with self.assertRaises(ValidationError):
            self.interview.action_complete()

    def test_cannot_cancel_completed(self):
        self.interview.action_complete()
        with self.assertRaises(ValidationError):
            self.interview.action_cancel()

    def test_reschedule_from_cancelled(self):
        self.interview.action_cancel()
        self.interview.action_reschedule()
        self.assertEqual(self.interview.state, 'scheduled')

    def test_reschedule_from_no_show(self):
        self.interview.action_no_show()
        self.interview.action_reschedule()
        self.assertEqual(self.interview.state, 'scheduled')


@tagged('post_install', '-at_install')
class TestAdmissionDecision(TransactionCase):

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
        cls.application = cls.env['uni.admission.application'].create({
            'applicant_name': 'Decision Applicant',
            'applicant_email': 'decision@example.com',
            'university_id': cls.university.id,
            'college_id': cls.college.id,
        })
        cls.decision = cls.env['uni.admission.decision'].create({
            'application_id': cls.application.id,
            'decision_type': 'accept',
        })

    def test_create_decision(self):
        self.assertTrue(self.decision.name)
        self.assertEqual(self.decision.decision_type, 'accept')
        self.assertEqual(self.decision.state, 'draft')

    def test_unique_decision_per_application(self):
        with self.assertRaises(Exception):
            self.env['uni.admission.decision'].create({
                'application_id': self.application.id,
                'decision_type': 'reject',
            })

    def test_scholarship_validation_no_amount(self):
        with self.assertRaises(ValidationError):
            self.env['uni.admission.decision'].create({
                'application_id': self.application.id,
                'decision_type': 'accept',
                'scholarship_offered': True,
                'scholarship_amount': 0.0,
            })

    def test_scholarship_validation_amount_without_flag(self):
        with self.assertRaises(ValidationError):
            self.env['uni.admission.decision'].create({
                'application_id': self.application.id,
                'decision_type': 'accept',
                'scholarship_offered': False,
                'scholarship_amount': 1000.0,
            })

    def test_conditional_accept_requires_conditions(self):
        with self.assertRaises(ValidationError):
            self.env['uni.admission.decision'].create({
                'application_id': self.application.id,
                'decision_type': 'conditional_accept',
                'conditions': False,
            })

    def test_state_workflow_draft_to_finalized(self):
        self.decision.action_finalize()
        self.assertEqual(self.decision.state, 'finalized')
        self.assertTrue(self.decision.finalized_by)
        self.assertTrue(self.decision.finalized_date)

    def test_finalized_propagates_to_application(self):
        self.application.action_submit()
        self.decision.action_finalize()
        self.assertEqual(self.application.status, 'accepted')
        self.assertEqual(self.application.decision_id, self.decision)

    def test_reject_finalizes_to_rejected(self):
        app2 = self.env['uni.admission.application'].create({
            'applicant_name': 'Reject Applicant',
            'applicant_email': 'reject@example.com',
            'university_id': self.university.id,
            'college_id': self.college.id,
        })
        app2.action_submit()
        dec = self.env['uni.admission.decision'].create({
            'application_id': app2.id,
            'decision_type': 'reject',
        })
        dec.action_finalize()
        self.assertEqual(app2.status, 'rejected')

    def test_cannot_finalize_non_draft(self):
        self.decision.action_finalize()
        with self.assertRaises(ValidationError):
            self.decision.action_finalize()

    def test_back_to_draft(self):
        self.decision.action_finalize()
        self.decision.action_back_to_draft()
        self.assertEqual(self.decision.state, 'draft')
