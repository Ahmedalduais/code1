# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError
from odoo import fields


@tagged('post_install', '-at_install')
class TestClassroomType(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.classroom_type = cls.env['uni.classroom.type'].create({
            'name': 'Lecture Hall',
            'code': 'LEC',
            'capacity': 120,
            'has_projector': True,
            'has_ac': True,
        })

    def test_create_type(self):
        self.assertEqual(self.classroom_type.name, 'Lecture Hall')
        self.assertEqual(self.classroom_type.code, 'LEC')
        self.assertEqual(self.classroom_type.capacity, 120)
        self.assertTrue(self.classroom_type.has_projector)

    def test_code_uniqueness(self):
        with self.assertRaises(Exception):
            self.env['uni.classroom.type'].create({
                'name': 'Duplicate Type',
                'code': 'LEC',
            })

    def test_capacity_non_negative(self):
        with self.assertRaises(Exception):
            self.env['uni.classroom.type'].create({
                'name': 'Bad Capacity',
                'code': 'BAD',
                'capacity': -1,
            })

    def test_classroom_count_computation(self):
        self.assertEqual(self.classroom_type.classroom_count, 0)


@tagged('post_install', '-at_install')
class TestClassroom(TransactionCase):

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
        cls.classroom_type = cls.env['uni.classroom.type'].create({
            'name': 'Lecture Hall',
            'code': 'LEC',
            'capacity': 120,
        })
        cls.classroom = cls.env['uni.classroom'].create({
            'name': 'Hall A',
            'code': 'HA01',
            'university_id': cls.university.id,
            'classroom_type_id': cls.classroom_type.id,
            'capacity': 100,
            'building': 'Building A',
            'floor': '1',
            'room_number': '101',
        })

    def test_create_classroom(self):
        self.assertEqual(self.classroom.name, 'Hall A')
        self.assertEqual(self.classroom.code, 'HA01')
        self.assertEqual(self.classroom.capacity, 100)
        self.assertEqual(self.classroom.state, 'available')

    def test_code_uniqueness_per_university(self):
        with self.assertRaises(Exception):
            self.env['uni.classroom'].create({
                'name': 'Duplicate Room',
                'code': 'HA01',
                'university_id': self.university.id,
                'classroom_type_id': self.classroom_type.id,
            })

    def test_different_code_same_university_allowed(self):
        room = self.env['uni.classroom'].create({
            'name': 'Hall B',
            'code': 'HA02',
            'university_id': self.university.id,
            'classroom_type_id': self.classroom_type.id,
        })
        self.assertEqual(room.code, 'HA02')

    def test_capacity_non_negative(self):
        with self.assertRaises(ValidationError):
            self.classroom.write({'capacity': -1})

    def test_state_workflow_available_to_maintenance(self):
        self.classroom.action_maintenance()
        self.assertEqual(self.classroom.state, 'maintenance')

    def test_state_workflow_maintenance_to_available(self):
        self.classroom.action_maintenance()
        self.classroom.action_available()
        self.assertEqual(self.classroom.state, 'available')

    def test_booking_count_computation(self):
        self.assertEqual(self.classroom.booking_count, 0)

    def test_onchange_type_suggests_capacity(self):
        room = self.env['uni.classroom'].new({
            'classroom_type_id': self.classroom_type.id,
        })
        room._onchange_classroom_type_id()
        self.assertEqual(room.capacity, 120)


@tagged('post_install', '-at_install')
class TestTimetableSlot(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.slot = cls.env['uni.timetable.slot'].create({
            'name': 'Period 1',
            'code': 'P1',
            'day_of_week': 'monday',
            'start_time': 8.0,
            'end_time': 9.5,
        })

    def test_create_slot(self):
        self.assertEqual(self.slot.name, 'Period 1')
        self.assertEqual(self.slot.day_of_week, 'monday')
        self.assertEqual(self.slot.start_time, 8.0)
        self.assertEqual(self.slot.end_time, 9.5)

    def test_time_validation_end_before_start(self):
        with self.assertRaises(ValidationError):
            self.env['uni.timetable.slot'].create({
                'name': 'Bad Slot',
                'code': 'BS',
                'day_of_week': 'monday',
                'start_time': 10.0,
                'end_time': 9.0,
            })

    def test_time_validation_negative_start(self):
        with self.assertRaises(Exception):
            self.env['uni.timetable.slot'].create({
                'name': 'Negative Slot',
                'code': 'NS',
                'day_of_week': 'monday',
                'start_time': -1.0,
                'end_time': 1.0,
            })

    def test_time_validation_over_24(self):
        with self.assertRaises(Exception):
            self.env['uni.timetable.slot'].create({
                'name': 'Over 24 Slot',
                'code': 'O24',
                'day_of_week': 'monday',
                'start_time': 23.0,
                'end_time': 25.0,
            })

    def test_unique_day_start_time(self):
        with self.assertRaises(Exception):
            self.env['uni.timetable.slot'].create({
                'name': 'Duplicate Slot',
                'code': 'DS',
                'day_of_week': 'monday',
                'start_time': 8.0,
                'end_time': 9.5,
            })

    def test_duration_computation(self):
        self.assertEqual(self.slot.duration, 1.5)

    def test_duration_different_times(self):
        slot = self.env['uni.timetable.slot'].create({
            'name': 'Period 2',
            'code': 'P2',
            'day_of_week': 'tuesday',
            'start_time': 10.0,
            'end_time': 11.25,
        })
        self.assertAlmostEqual(slot.duration, 1.25, places=2)

    def test_break_slot(self):
        break_slot = self.env['uni.timetable.slot'].create({
            'name': 'Break',
            'code': 'BRK',
            'day_of_week': 'monday',
            'start_time': 9.5,
            'end_time': 10.0,
            'break_slot': True,
        })
        self.assertTrue(break_slot.break_slot)

    def test_different_days_allowed_same_time(self):
        self.env['uni.timetable.slot'].create({
            'name': 'Tuesday Period 1',
            'code': 'TP1',
            'day_of_week': 'tuesday',
            'start_time': 8.0,
            'end_time': 9.5,
        })
        slots = self.env['uni.timetable.slot'].search([
            ('start_time', '=', 8.0),
            ('end_time', '=', 9.5),
        ])
        self.assertEqual(len(slots), 2)


@tagged('post_install', '-at_install')
class TestTimetable(TransactionCase):

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
        cls.timetable = cls.env['uni.timetable'].create({
            'name': 'Fall 2024 CS Timetable',
            'code': 'TT-CS-F24',
            'university_id': cls.university.id,
            'college_id': cls.college.id,
            'department_id': cls.department.id,
            'program_id': cls.program.id,
            'academic_term_id': cls.term.id,
        })

    def test_create_timetable(self):
        self.assertEqual(self.timetable.name, 'Fall 2024 CS Timetable')
        self.assertEqual(self.timetable.code, 'TT-CS-F24')
        self.assertEqual(self.timetable.state, 'draft')

    def test_code_uniqueness_per_term(self):
        with self.assertRaises(Exception):
            self.env['uni.timetable'].create({
                'name': 'Duplicate Timetable',
                'code': 'TT-CS-F24',
                'university_id': self.university.id,
                'academic_term_id': self.term.id,
            })

    def test_state_workflow_draft_to_active(self):
        slot = self.env['uni.timetable.slot'].create({
            'name': 'Period 1',
            'code': 'P1',
            'day_of_week': 'monday',
            'start_time': 8.0,
            'end_time': 9.5,
        })
        person = self.env['uni.person'].create({
            'name': 'Test Faculty',
            'university_id': self.university.id,
            'person_type': 'faculty',
        })
        faculty = self.env['uni.faculty'].create({
            'person_id': person.id,
            'faculty_code': 'FAC-TT001',
        })
        course = self.env['uni.course'].create({
            'name': 'Test Course',
            'code': 'TC101',
            'university_id': self.university.id,
            'college_id': self.college.id,
        })
        self.env['uni.timetable.line'].create({
            'timetable_id': self.timetable.id,
            'course_id': course.id,
            'faculty_id': faculty.id,
            'slot_id': slot.id,
        })
        self.timetable.action_activate()
        self.assertEqual(self.timetable.state, 'active')
        self.assertTrue(self.timetable.publish_date)

    def test_activate_requires_lines(self):
        with self.assertRaises(ValidationError):
            self.timetable.action_activate()

    def test_state_workflow_active_to_closed(self):
        slot = self.env['uni.timetable.slot'].create({
            'name': 'Period 1',
            'code': 'P1',
            'day_of_week': 'monday',
            'start_time': 8.0,
            'end_time': 9.5,
        })
        person = self.env['uni.person'].create({
            'name': 'Test Faculty',
            'university_id': self.university.id,
            'person_type': 'faculty',
        })
        faculty = self.env['uni.faculty'].create({
            'person_id': person.id,
            'faculty_code': 'FAC-TT002',
        })
        course = self.env['uni.course'].create({
            'name': 'Test Course 2',
            'code': 'TC102',
            'university_id': self.university.id,
            'college_id': self.college.id,
        })
        self.env['uni.timetable.line'].create({
            'timetable_id': self.timetable.id,
            'course_id': course.id,
            'faculty_id': faculty.id,
            'slot_id': slot.id,
        })
        self.timetable.action_activate()
        self.timetable.action_close()
        self.assertEqual(self.timetable.state, 'closed')

    def test_state_workflow_to_draft(self):
        slot = self.env['uni.timetable.slot'].create({
            'name': 'Period 1',
            'code': 'P1',
            'day_of_week': 'monday',
            'start_time': 8.0,
            'end_time': 9.5,
        })
        person = self.env['uni.person'].create({
            'name': 'Test Faculty',
            'university_id': self.university.id,
            'person_type': 'faculty',
        })
        faculty = self.env['uni.faculty'].create({
            'person_id': person.id,
            'faculty_code': 'FAC-TT003',
        })
        course = self.env['uni.course'].create({
            'name': 'Test Course 3',
            'code': 'TC103',
            'university_id': self.university.id,
            'college_id': self.college.id,
        })
        self.env['uni.timetable.line'].create({
            'timetable_id': self.timetable.id,
            'course_id': course.id,
            'faculty_id': faculty.id,
            'slot_id': slot.id,
        })
        self.timetable.action_activate()
        self.timetable.action_draft()
        self.assertEqual(self.timetable.state, 'draft')

    def test_line_count_computation(self):
        self.assertEqual(self.timetable.line_count, 0)


@tagged('post_install', '-at_install')
class TestTimetableLine(TransactionCase):

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
        cls.timetable = cls.env['uni.timetable'].create({
            'name': 'CS Timetable',
            'code': 'TT-CS',
            'university_id': cls.university.id,
            'college_id': cls.college.id,
            'department_id': cls.department.id,
            'academic_term_id': cls.term.id,
        })
        cls.slot = cls.env['uni.timetable.slot'].create({
            'name': 'Period 1',
            'code': 'P1',
            'day_of_week': 'monday',
            'start_time': 8.0,
            'end_time': 9.5,
        })
        cls.slot2 = cls.env['uni.timetable.slot'].create({
            'name': 'Period 2',
            'code': 'P2',
            'day_of_week': 'monday',
            'start_time': 10.0,
            'end_time': 11.5,
        })
        cls.person1 = cls.env['uni.person'].create({
            'name': 'Dr. Faculty One',
            'university_id': cls.university.id,
            'person_type': 'faculty',
        })
        cls.faculty1 = cls.env['uni.faculty'].create({
            'person_id': cls.person1.id,
            'faculty_code': 'FAC-TL001',
        })
        cls.person2 = cls.env['uni.person'].create({
            'name': 'Dr. Faculty Two',
            'university_id': cls.university.id,
            'person_type': 'faculty',
        })
        cls.faculty2 = cls.env['uni.faculty'].create({
            'person_id': cls.person2.id,
            'faculty_code': 'FAC-TL002',
        })
        cls.course1 = cls.env['uni.course'].create({
            'name': 'Programming',
            'code': 'CS101',
            'university_id': cls.university.id,
            'college_id': cls.college.id,
        })
        cls.course2 = cls.env['uni.course'].create({
            'name': 'Algorithms',
            'code': 'CS201',
            'university_id': cls.university.id,
            'college_id': cls.college.id,
        })
        cls.classroom_type = cls.env['uni.classroom.type'].create({
            'name': 'Lecture Hall',
            'code': 'LH',
            'capacity': 100,
        })
        cls.classroom = cls.env['uni.classroom'].create({
            'name': 'Room A',
            'code': 'RA01',
            'university_id': cls.university.id,
            'classroom_type_id': cls.classroom_type.id,
            'capacity': 100,
        })

    def test_create_line(self):
        line = self.env['uni.timetable.line'].create({
            'timetable_id': self.timetable.id,
            'course_id': self.course1.id,
            'faculty_id': self.faculty1.id,
            'slot_id': self.slot.id,
            'classroom_id': self.classroom.id,
        })
        self.assertTrue(line.name)
        self.assertEqual(line.timetable_id, self.timetable)
        self.assertEqual(line.day_of_week, 'monday')
        self.assertEqual(line.start_time, 8.0)

    def test_faculty_conflict_detection(self):
        self.env['uni.timetable.line'].create({
            'timetable_id': self.timetable.id,
            'course_id': self.course1.id,
            'faculty_id': self.faculty1.id,
            'slot_id': self.slot.id,
        })
        with self.assertRaises(ValidationError):
            self.env['uni.timetable.line'].create({
                'timetable_id': self.timetable.id,
                'course_id': self.course2.id,
                'faculty_id': self.faculty1.id,
                'slot_id': self.slot.id,
            })

    def test_faculty_no_conflict_different_slot(self):
        self.env['uni.timetable.line'].create({
            'timetable_id': self.timetable.id,
            'course_id': self.course1.id,
            'faculty_id': self.faculty1.id,
            'slot_id': self.slot.id,
        })
        line2 = self.env['uni.timetable.line'].create({
            'timetable_id': self.timetable.id,
            'course_id': self.course2.id,
            'faculty_id': self.faculty1.id,
            'slot_id': self.slot2.id,
        })
        self.assertTrue(line2)

    def test_classroom_conflict_detection(self):
        self.env['uni.timetable.line'].create({
            'timetable_id': self.timetable.id,
            'course_id': self.course1.id,
            'faculty_id': self.faculty1.id,
            'slot_id': self.slot.id,
            'classroom_id': self.classroom.id,
        })
        with self.assertRaises(ValidationError):
            self.env['uni.timetable.line'].create({
                'timetable_id': self.timetable.id,
                'course_id': self.course2.id,
                'faculty_id': self.faculty2.id,
                'slot_id': self.slot.id,
                'classroom_id': self.classroom.id,
            })

    def test_classroom_no_conflict_different_slot(self):
        self.env['uni.timetable.line'].create({
            'timetable_id': self.timetable.id,
            'course_id': self.course1.id,
            'faculty_id': self.faculty1.id,
            'slot_id': self.slot.id,
            'classroom_id': self.classroom.id,
        })
        line2 = self.env['uni.timetable.line'].create({
            'timetable_id': self.timetable.id,
            'course_id': self.course2.id,
            'faculty_id': self.faculty2.id,
            'slot_id': self.slot2.id,
            'classroom_id': self.classroom.id,
        })
        self.assertTrue(line2)

    def test_course_section_conflict(self):
        self.env['uni.timetable.line'].create({
            'timetable_id': self.timetable.id,
            'course_id': self.course1.id,
            'faculty_id': self.faculty1.id,
            'slot_id': self.slot.id,
            'section': 'A',
        })
        with self.assertRaises(ValidationError):
            self.env['uni.timetable.line'].create({
                'timetable_id': self.timetable.id,
                'course_id': self.course1.id,
                'faculty_id': self.faculty2.id,
                'slot_id': self.slot.id,
                'section': 'A',
            })

    def test_course_different_section_no_conflict(self):
        self.env['uni.timetable.line'].create({
            'timetable_id': self.timetable.id,
            'course_id': self.course1.id,
            'faculty_id': self.faculty1.id,
            'slot_id': self.slot.id,
            'section': 'A',
        })
        line2 = self.env['uni.timetable.line'].create({
            'timetable_id': self.timetable.id,
            'course_id': self.course1.id,
            'faculty_id': self.faculty2.id,
            'slot_id': self.slot.id,
            'section': 'B',
        })
        self.assertTrue(line2)

    def test_classroom_university_validation(self):
        other_university = self.env['uni.university'].create({
            'name': 'Other University',
            'code': 'OU',
        })
        other_type = self.env['uni.classroom.type'].create({
            'name': 'Other Hall',
            'code': 'OH',
        })
        other_classroom = self.env['uni.classroom'].create({
            'name': 'Other Room',
            'code': 'OR01',
            'university_id': other_university.id,
            'classroom_type_id': other_type.id,
        })
        with self.assertRaises(ValidationError):
            self.env['uni.timetable.line'].create({
                'timetable_id': self.timetable.id,
                'course_id': self.course1.id,
                'faculty_id': self.faculty1.id,
                'slot_id': self.slot.id,
                'classroom_id': other_classroom.id,
            })

    def test_makeup_session_no_faculty_conflict(self):
        self.env['uni.timetable.line'].create({
            'timetable_id': self.timetable.id,
            'course_id': self.course1.id,
            'faculty_id': self.faculty1.id,
            'slot_id': self.slot.id,
            'is_makeup': False,
        })
        line2 = self.env['uni.timetable.line'].create({
            'timetable_id': self.timetable.id,
            'course_id': self.course1.id,
            'faculty_id': self.faculty1.id,
            'slot_id': self.slot.id,
            'is_makeup': True,
        })
        self.assertTrue(line2)

    def test_makeup_makeup_conflict(self):
        self.env['uni.timetable.line'].create({
            'timetable_id': self.timetable.id,
            'course_id': self.course1.id,
            'faculty_id': self.faculty1.id,
            'slot_id': self.slot.id,
            'is_makeup': True,
        })
        with self.assertRaises(ValidationError):
            self.env['uni.timetable.line'].create({
                'timetable_id': self.timetable.id,
                'course_id': self.course2.id,
                'faculty_id': self.faculty1.id,
                'slot_id': self.slot.id,
                'is_makeup': True,
            })


@tagged('post_install', '-at_install')
class TestClassroomBooking(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
            'code': 'TU',
        })
        cls.classroom_type = cls.env['uni.classroom.type'].create({
            'name': 'Lecture Hall',
            'code': 'LH',
            'capacity': 100,
        })
        cls.classroom = cls.env['uni.classroom'].create({
            'name': 'Room A',
            'code': 'RA01',
            'university_id': cls.university.id,
            'classroom_type_id': cls.classroom_type.id,
            'capacity': 100,
        })
        cls.booking = cls.env['uni.classroom.booking'].create({
            'classroom_id': cls.classroom.id,
            'booking_date': '2024-09-15',
            'start_time': 8.0,
            'end_time': 10.0,
            'purpose': 'CS101 Lecture',
        })

    def test_create_booking(self):
        self.assertTrue(self.booking.name)
        self.assertEqual(self.booking.state, 'draft')
        self.assertEqual(self.booking.classroom_id, self.classroom)

    def test_conflict_detection_overlapping(self):
        with self.assertRaises(ValidationError):
            self.env['uni.classroom.booking'].create({
                'classroom_id': self.classroom.id,
                'booking_date': '2024-09-15',
                'start_time': 9.0,
                'end_time': 11.0,
            })

    def test_conflict_detection_exact_same(self):
        with self.assertRaises(Exception):
            self.env['uni.classroom.booking'].create({
                'classroom_id': self.classroom.id,
                'booking_date': '2024-09-15',
                'start_time': 8.0,
                'end_time': 10.0,
            })

    def test_no_conflict_different_date(self):
        booking2 = self.env['uni.classroom.booking'].create({
            'classroom_id': self.classroom.id,
            'booking_date': '2024-09-16',
            'start_time': 8.0,
            'end_time': 10.0,
        })
        self.assertTrue(booking2)

    def test_no_conflict_adjacent_times(self):
        booking2 = self.env['uni.classroom.booking'].create({
            'classroom_id': self.classroom.id,
            'booking_date': '2024-09-15',
            'start_time': 10.0,
            'end_time': 12.0,
        })
        self.assertTrue(booking2)

    def test_no_conflict_different_classroom(self):
        other_type = self.env['uni.classroom.type'].create({
            'name': 'Lab',
            'code': 'LB',
        })
        other_room = self.env['uni.classroom'].create({
            'name': 'Room B',
            'code': 'RB01',
            'university_id': self.university.id,
            'classroom_type_id': other_type.id,
        })
        booking2 = self.env['uni.classroom.booking'].create({
            'classroom_id': other_room.id,
            'booking_date': '2024-09-15',
            'start_time': 8.0,
            'end_time': 10.0,
        })
        self.assertTrue(booking2)

    def test_cancelled_booking_no_conflict(self):
        self.booking.action_cancel()
        booking2 = self.env['uni.classroom.booking'].create({
            'classroom_id': self.classroom.id,
            'booking_date': '2024-09-15',
            'start_time': 8.0,
            'end_time': 10.0,
        })
        self.assertTrue(booking2)

    def test_state_workflow_draft_to_confirmed(self):
        self.booking.action_confirm()
        self.assertEqual(self.booking.state, 'confirmed')

    def test_state_workflow_confirmed_to_completed(self):
        self.booking.action_confirm()
        self.booking.action_complete()
        self.assertEqual(self.booking.state, 'completed')

    def test_state_workflow_to_cancelled(self):
        self.booking.action_cancel()
        self.assertEqual(self.booking.state, 'cancelled')

    def test_confirm_requires_draft(self):
        self.booking.action_confirm()
        with self.assertRaises(ValidationError):
            self.booking.action_confirm()

    def test_complete_requires_confirmed(self):
        with self.assertRaises(ValidationError):
            self.booking.action_complete()

    def test_cannot_cancel_completed(self):
        self.booking.action_confirm()
        self.booking.action_complete()
        with self.assertRaises(ValidationError):
            self.booking.action_cancel()

    def test_time_validation_end_before_start(self):
        with self.assertRaises(Exception):
            self.env['uni.classroom.booking'].create({
                'classroom_id': self.classroom.id,
                'booking_date': '2024-09-15',
                'start_time': 10.0,
                'end_time': 8.0,
            })

    def test_state_workflow_to_draft(self):
        self.booking.action_draft()
        self.assertEqual(self.booking.state, 'draft')
