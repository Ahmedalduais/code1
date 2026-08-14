# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError
from odoo import fields


@tagged('post_install', '-at_install')
class TestExamType(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.exam_type = cls.env['uni.exam.type'].create({
            'name': 'Final Exam',
            'code': 'EX-TYPE-FINAL',
            'exam_nature': 'written',
            'default_duration': 2.0,
            'default_max_score': 100.0,
            'weight_percentage': 30.0,
            'passing_percentage': 50.0,
            'is_final': True,
            'is_midterm': False,
        })

    def test_create_type(self):
        self.assertEqual(self.exam_type.name, 'Final Exam')
        self.assertEqual(self.exam_type.code, 'EX-TYPE-FINAL')
        self.assertTrue(self.exam_type.is_final)
        self.assertFalse(self.exam_type.is_midterm)

    def test_code_uniqueness(self):
        with self.assertRaises(Exception):
            self.env['uni.exam.type'].create({
                'name': 'Duplicate Type',
                'code': 'EX-TYPE-FINAL',
            })

    def test_duration_validation_negative(self):
        with self.assertRaises(Exception):
            self.env['uni.exam.type'].create({
                'name': 'Bad Duration',
                'code': 'EX-BAD-DUR',
                'default_duration': -1.0,
            })

    def test_max_score_validation_negative(self):
        with self.assertRaises(Exception):
            self.env['uni.exam.type'].create({
                'name': 'Bad Score',
                'code': 'EX-BAD-SCR',
                'default_max_score': -1.0,
            })

    def test_weight_validation_over_100(self):
        with self.assertRaises(Exception):
            self.env['uni.exam.type'].create({
                'name': 'Bad Weight',
                'code': 'EX-BAD-WGT',
                'weight_percentage': 101.0,
            })

    def test_final_xor_midterm(self):
        with self.assertRaises(ValidationError):
            self.env['uni.exam.type'].create({
                'name': 'Both Final Midterm',
                'code': 'EX-BOTH',
                'is_final': True,
                'is_midterm': True,
            })


@tagged('post_install', '-at_install')
class TestExam(TransactionCase):

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
        cls.exam_type = cls.env['uni.exam.type'].create({
            'name': 'Final Exam',
            'code': 'EX-TYPE-FINAL',
            'default_duration': 2.0,
            'default_max_score': 100.0,
        })
        cls.exam = cls.env['uni.exam'].create({
            'name': 'CS101 Final',
            'course_id': cls.course.id,
            'academic_term_id': cls.term.id,
            'exam_type_id': cls.exam_type.id,
            'max_score': 100.0,
            'passing_score': 50.0,
            'duration': 2.0,
            'exam_date': '2025-12-15 09:00:00',
        })

    def test_create_exam(self):
        self.assertTrue(self.exam.name)
        self.assertEqual(self.exam.course_id, self.course)
        self.assertEqual(self.exam.state, 'draft')

    def test_code_uniqueness_per_term(self):
        with self.assertRaises(Exception):
            self.env['uni.exam'].create({
                'name': 'Duplicate Exam',
                'code': self.exam.code,
                'course_id': self.course.id,
                'academic_term_id': self.term.id,
                'exam_type_id': self.exam_type.id,
            })

    def test_score_validation_passing_exceeds_max(self):
        with self.assertRaises(ValidationError):
            self.env['uni.exam'].create({
                'name': 'Bad Score Exam',
                'course_id': self.course.id,
                'academic_term_id': self.term.id,
                'exam_type_id': self.exam_type.id,
                'max_score': 100.0,
                'passing_score': 110.0,
            })

    def test_time_validation_end_before_start(self):
        with self.assertRaises(ValidationError):
            self.env['uni.exam'].create({
                'name': 'Bad Time Exam',
                'course_id': self.course.id,
                'academic_term_id': self.term.id,
                'exam_type_id': self.exam_type.id,
                'start_time': 10.0,
                'end_time': 9.0,
            })

    def test_state_workflow_draft_to_scheduled(self):
        self.exam.action_schedule()
        self.assertEqual(self.exam.state, 'scheduled')

    def test_schedule_requires_date(self):
        exam_no_date = self.env['uni.exam'].create({
            'name': 'No Date Exam',
            'course_id': self.course.id,
            'academic_term_id': self.term.id,
            'exam_type_id': self.exam_type.id,
        })
        with self.assertRaises(ValidationError):
            exam_no_date.action_schedule()

    def test_state_workflow_scheduled_to_ongoing(self):
        self.exam.action_schedule()
        self.exam.action_start()
        self.assertEqual(self.exam.state, 'ongoing')

    def test_state_workflow_ongoing_to_completed(self):
        self.exam.action_schedule()
        self.exam.action_start()
        self.exam.action_complete()
        self.assertEqual(self.exam.state, 'completed')

    def test_state_workflow_to_cancelled(self):
        self.exam.action_cancel()
        self.assertEqual(self.exam.state, 'cancelled')

    def test_cannot_start_non_scheduled(self):
        with self.assertRaises(ValidationError):
            self.exam.action_start()

    def test_cannot_complete_non_ongoing(self):
        self.exam.action_schedule()
        with self.assertRaises(ValidationError):
            self.exam.action_complete()

    def test_cannot_cancel_completed(self):
        self.exam.action_schedule()
        self.exam.action_start()
        self.exam.action_complete()
        with self.assertRaises(ValidationError):
            self.exam.action_cancel()

    def test_rooms_university_validation(self):
        other_university = self.env['uni.university'].create({
            'name': 'Other University',
            'code': 'OU',
        })
        room = self.env['uni.exam.room'].create({
            'name': 'Room 101',
            'code': 'R101',
            'university_id': other_university.id,
            'capacity': 30,
        })
        with self.assertRaises(ValidationError):
            self.exam.write({'room_ids': [(6, 0, [room.id])]})

    def test_draft_reset(self):
        self.exam.action_draft()
        self.assertEqual(self.exam.state, 'draft')


@tagged('post_install', '-at_install')
class TestExamSchedule(TransactionCase):

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
        })
        cls.exam_type = cls.env['uni.exam.type'].create({
            'name': 'Final Exam',
            'code': 'EX-TYPE-FINAL',
        })
        cls.schedule = cls.env['uni.exam.schedule'].create({
            'name': 'Fall 2025 Final Exams',
            'code': 'SCH-F25-FINAL',
            'academic_term_id': cls.term.id,
            'college_id': cls.college.id,
        })

    def test_create_schedule(self):
        self.assertEqual(self.schedule.name, 'Fall 2025 Final Exams')
        self.assertEqual(self.schedule.state, 'draft')

    def test_code_uniqueness_per_term(self):
        with self.assertRaises(Exception):
            self.env['uni.exam.schedule'].create({
                'name': 'Duplicate Schedule',
                'code': 'SCH-F25-FINAL',
                'academic_term_id': self.term.id,
            })

    def test_college_university_validation(self):
        other_university = self.env['uni.university'].create({
            'name': 'Other University',
            'code': 'OU',
        })
        other_college = self.env['uni.college'].create({
            'name': 'Other College',
            'code': 'OC',
            'university_id': other_university.id,
        })
        with self.assertRaises(ValidationError):
            self.env['uni.exam.schedule'].create({
                'name': 'Bad College Schedule',
                'academic_term_id': self.term.id,
                'college_id': other_college.id,
            })

    def test_state_workflow_draft_to_published(self):
        exam = self.env['uni.exam'].create({
            'name': 'CS101 Final',
            'course_id': self.course.id,
            'academic_term_id': self.term.id,
            'exam_type_id': self.exam_type.id,
        })
        self.schedule.exam_ids = [(6, 0, [exam.id])]
        self.schedule.action_publish()
        self.assertEqual(self.schedule.state, 'published')
        self.assertTrue(self.schedule.publish_date)

    def test_publish_requires_exams(self):
        with self.assertRaises(ValidationError):
            self.schedule.action_publish()

    def test_state_workflow_published_to_closed(self):
        exam = self.env['uni.exam'].create({
            'name': 'CS101 Final',
            'course_id': self.course.id,
            'academic_term_id': self.term.id,
            'exam_type_id': self.exam_type.id,
        })
        self.schedule.exam_ids = [(6, 0, [exam.id])]
        self.schedule.action_publish()
        self.schedule.action_close()
        self.assertEqual(self.schedule.state, 'closed')

    def test_state_workflow_to_draft(self):
        exam = self.env['uni.exam'].create({
            'name': 'CS101 Final',
            'course_id': self.course.id,
            'academic_term_id': self.term.id,
            'exam_type_id': self.exam_type.id,
        })
        self.schedule.exam_ids = [(6, 0, [exam.id])]
        self.schedule.action_publish()
        self.schedule.action_draft()
        self.assertEqual(self.schedule.state, 'draft')


@tagged('post_install', '-at_install')
class TestExamRoom(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
            'code': 'TU',
        })
        cls.room = cls.env['uni.exam.room'].create({
            'name': 'Room 101',
            'code': 'R101',
            'university_id': cls.university.id,
            'capacity': 60,
            'has_ac': True,
        })

    def test_create_room(self):
        self.assertEqual(self.room.name, 'Room 101')
        self.assertEqual(self.room.capacity, 60)
        self.assertEqual(self.room.state, 'available')

    def test_code_uniqueness_per_university(self):
        with self.assertRaises(Exception):
            self.env['uni.exam.room'].create({
                'name': 'Duplicate Room',
                'code': 'R101',
                'university_id': self.university.id,
            })

    def test_capacity_validation_negative(self):
        with self.assertRaises(Exception):
            self.env['uni.exam.room'].create({
                'name': 'Bad Capacity Room',
                'code': 'R-BAD',
                'university_id': self.university.id,
                'capacity': -1,
            })

    def test_state_workflow_to_maintenance(self):
        self.room.action_maintenance()
        self.assertEqual(self.room.state, 'maintenance')

    def test_state_workflow_to_available(self):
        self.room.action_maintenance()
        self.room.action_available()
        self.assertEqual(self.room.state, 'available')


@tagged('post_install', '-at_install')
class TestExamInvigilator(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.invigilator = cls.env['uni.exam.invigilator'].create({
            'name': 'Prof. Smith',
            'code': 'INV-001',
            'role': 'chief_invigilator',
            'phone': '+1234567890',
            'email': 'smith@example.com',
        })

    def test_create_invigilator(self):
        self.assertEqual(self.invigilator.name, 'Prof. Smith')
        self.assertEqual(self.invigilator.role, 'chief_invigilator')

    def test_code_uniqueness(self):
        with self.assertRaises(Exception):
            self.env['uni.exam.invigilator'].create({
                'name': 'Duplicate Invigilator',
                'code': 'INV-001',
            })


@tagged('post_install', '-at_install')
class TestExamViolation(TransactionCase):

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
        cls.exam_type = cls.env['uni.exam.type'].create({
            'name': 'Final Exam',
            'code': 'EX-TYPE-FINAL',
        })
        cls.exam = cls.env['uni.exam'].create({
            'name': 'CS101 Final',
            'course_id': cls.course.id,
            'academic_term_id': cls.term.id,
            'exam_type_id': cls.exam_type.id,
        })
        cls.violation = cls.env['uni.exam.violation'].create({
            'exam_id': cls.exam.id,
            'student_name': 'Cheating Student',
            'student_code': 'STU-001',
            'violation_type': 'cheating',
            'severity': 'minor',
            'description': 'Using unauthorized notes during the exam.',
        })

    def test_create_violation(self):
        self.assertTrue(self.violation.name)
        self.assertEqual(self.violation.student_name, 'Cheating Student')
        self.assertEqual(self.violation.state, 'reported')

    def test_critical_severity_requires_action(self):
        with self.assertRaises(ValidationError):
            self.env['uni.exam.violation'].create({
                'exam_id': self.exam.id,
                'student_name': 'Critical Student',
                'violation_type': 'cheating',
                'severity': 'critical',
                'action_taken': 'no_action',
                'description': 'Severe cheating.',
            })

    def test_state_workflow_reported_to_investigated(self):
        self.violation.action_investigate()
        self.assertEqual(self.violation.state, 'investigated')

    def test_state_workflow_investigated_to_decided(self):
        self.violation.action_investigate()
        self.violation.action_decide()
        self.assertEqual(self.violation.state, 'decided')

    def test_decide_requires_action_taken(self):
        self.violation.action_investigate()
        with self.assertRaises(ValidationError):
            self.violation.action_decide()

    def test_state_workflow_decided_to_closed(self):
        self.violation.action_investigate()
        self.violation.action_decide()
        self.violation.action_close()
        self.assertEqual(self.violation.state, 'closed')

    def test_action_reopen(self):
        self.violation.action_investigate()
        self.violation.action_decide()
        self.violation.action_reopen()
        self.assertEqual(self.violation.state, 'investigated')


@tagged('post_install', '-at_install')
class TestExamAccommodation(TransactionCase):

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
        cls.exam_type = cls.env['uni.exam.type'].create({
            'name': 'Final Exam',
            'code': 'EX-TYPE-FINAL',
        })
        cls.exam = cls.env['uni.exam'].create({
            'name': 'CS101 Final',
            'course_id': cls.course.id,
            'academic_term_id': cls.term.id,
            'exam_type_id': cls.exam_type.id,
        })
        cls.accommodation = cls.env['uni.exam.accommodation'].create({
            'exam_id': cls.exam.id,
            'student_name': 'Special Student',
            'student_code': 'STU-SP-001',
            'accommodation_type': 'extra_time',
            'extra_time_minutes': 30,
            'accommodation_details': 'Extra time due to learning disability.',
        })

    def test_create_accommodation(self):
        self.assertTrue(self.accommodation.name)
        self.assertEqual(self.accommodation.student_name, 'Special Student')
        self.assertEqual(self.accommodation.state, 'draft')

    def test_extra_time_validation(self):
        with self.assertRaises(ValidationError):
            self.env['uni.exam.accommodation'].create({
                'exam_id': self.exam.id,
                'student_name': 'No Time Student',
                'student_code': 'STU-NT-001',
                'accommodation_type': 'extra_time',
                'extra_time_minutes': 0,
                'extra_time_percentage': 0,
                'accommodation_details': 'No extra time specified.',
            })

    def test_state_workflow_draft_to_submitted(self):
        self.accommodation.action_submit()
        self.assertEqual(self.accommodation.state, 'submitted')

    def test_state_workflow_submitted_to_under_review(self):
        self.accommodation.action_submit()
        self.accommodation.action_start_review()
        self.assertEqual(self.accommodation.state, 'under_review')

    def test_state_workflow_under_review_to_approved(self):
        self.accommodation.action_submit()
        self.accommodation.action_start_review()
        self.accommodation.action_approve()
        self.assertEqual(self.accommodation.state, 'approved')
        self.assertTrue(self.accommodation.approved_by)

    def test_deny_requires_reason(self):
        self.accommodation.action_submit()
        self.accommodation.action_start_review()
        with self.assertRaises(ValidationError):
            self.accommodation.action_deny()

    def test_state_workflow_to_applied(self):
        self.accommodation.action_submit()
        self.accommodation.action_start_review()
        self.accommodation.action_approve()
        self.accommodation.action_apply()
        self.assertEqual(self.accommodation.state, 'applied')

    def test_state_workflow_to_cancelled(self):
        self.accommodation.action_cancel()
        self.assertEqual(self.accommodation.state, 'cancelled')

    def test_reset_to_draft_from_denied(self):
        self.accommodation.action_submit()
        self.accommodation.action_start_review()
        self.accommodation.write({'denial_reason': 'Not supported'})
        self.accommodation.action_deny()
        self.accommodation.action_reset_to_draft()
        self.assertEqual(self.accommodation.state, 'draft')
