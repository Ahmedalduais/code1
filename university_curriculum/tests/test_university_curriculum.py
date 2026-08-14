# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestCourse(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Curriculum Test University',
            'code': 'CTU',
        })
        cls.college = cls.env['uni.college'].create({
            'name': 'Engineering College',
            'code': 'ECC',
            'university_id': cls.university.id,
        })
        cls.college2 = cls.env['uni.college'].create({
            'name': 'Science College',
            'code': 'SCC',
            'university_id': cls.university.id,
        })
        cls.department = cls.env['uni.department'].create({
            'name': 'CS Department',
            'code': 'CSD',
            'university_id': cls.university.id,
            'college_id': cls.college.id,
        })

    def _create_course(self, code='CS101', college=None, credit_hours=3.0, contact_hours=3.0):
        return self.env['uni.course'].create({
            'name': 'Intro to CS',
            'code': code,
            'university_id': self.university.id,
            'college_id': (college or self.college).id,
            'credit_hours': credit_hours,
            'contact_hours': contact_hours,
        })

    def test_create_course(self):
        course = self._create_course()
        self.assertEqual(course.state, 'draft')
        self.assertTrue(course.active)

    def test_code_uniqueness_per_college(self):
        self._create_course('CS101')
        with self.assertRaises(Exception):
            self._create_course('CS101')

    def test_code_allowed_across_colleges(self):
        self._create_course('CS101', college=self.college)
        course2 = self._create_course('CS101', college=self.college2)
        self.assertTrue(course2)

    def test_credit_hours_validation_negative(self):
        with self.assertRaises(Exception):
            self._create_course('CS102', credit_hours=-1)

    def test_contact_hours_validation_negative(self):
        with self.assertRaises(Exception):
            self._create_course('CS103', contact_hours=-1)

    def test_contact_hours_less_than_credit_hours(self):
        with self.assertRaises(ValidationError):
            self._create_course('CS104', credit_hours=3.0, contact_hours=2.0)

    def test_state_workflow_draft_to_active(self):
        course = self._create_course()
        course.action_activate()
        self.assertEqual(course.state, 'active')

    def test_state_workflow_active_to_suspended(self):
        course = self._create_course()
        course.action_activate()
        course.action_suspend()
        self.assertEqual(course.state, 'suspended')

    def test_state_workflow_suspended_to_closed(self):
        course = self._create_course()
        course.action_activate()
        course.action_suspend()
        course.action_close()
        self.assertEqual(course.state, 'closed')

    def test_state_workflow_closed_to_draft(self):
        course = self._create_course()
        course.action_activate()
        course.action_suspend()
        course.action_close()
        course.action_draft()
        self.assertEqual(course.state, 'draft')

    def test_onchange_college_id(self):
        course = self.env['uni.course'].new({
            'name': 'New Course',
            'code': 'NC01',
            'college_id': self.college.id,
            'university_id': False,
        })
        course._onchange_college_id()
        self.assertEqual(course.university_id, self.university)

    def test_onchange_department_id(self):
        course = self.env['uni.course'].new({
            'name': 'Dept Course',
            'code': 'DC01',
            'department_id': self.department.id,
            'college_id': False,
            'university_id': False,
        })
        course._onchange_department_id()
        self.assertEqual(course.college_id, self.department.college_id)
        self.assertEqual(course.university_id, self.department.university_id)

    def test_self_prerequisite_constraint(self):
        course = self._create_course()
        with self.assertRaises(ValidationError):
            self.env['uni.course.prerequisite'].create({
                'course_id': course.id,
                'prerequisite_course_id': course.id,
            })

    def test_self_equivalent_constraint(self):
        course = self._create_course()
        with self.assertRaises(ValidationError):
            self.env['uni.course.equivalent'].create({
                'course_id': course.id,
                'equivalent_course_id': course.id,
            })

    def test_program_count_computation(self):
        course = self._create_course()
        self.assertEqual(course.program_count, 0)

    def test_action_view_program_links(self):
        course = self._create_course()
        action = course.action_view_program_links()
        self.assertEqual(action['res_model'], 'uni.program.course')


@tagged('post_install', '-at_install')
class TestCourseType(TransactionCase):

    def test_create_course_type(self):
        ct = self.env['uni.course.type'].create({
            'name': 'Theoretical',
            'code': 'TH',
            'course_nature': 'theoretical',
            'default_credit_hours': 3,
            'default_contact_hours': 45,
        })
        self.assertEqual(ct.name, 'Theoretical')
        self.assertEqual(ct.course_nature, 'theoretical')
        self.assertTrue(ct.active)

    def test_code_uniqueness(self):
        self.env['uni.course.type'].create({
            'name': 'Practical',
            'code': 'PR',
            'course_nature': 'practical',
        })
        with self.assertRaises(Exception):
            self.env['uni.course.type'].create({
                'name': 'Practical Dup',
                'code': 'PR',
                'course_nature': 'practical',
            })

    def test_course_nature_selection(self):
        for nature in ['theoretical', 'practical', 'hybrid', 'clinical',
                       'laboratory', 'field_work', 'seminar', 'research', 'project']:
            ct = self.env['uni.course.type'].create({
                'name': f'Type {nature}',
                'code': f'T{nature[:2].upper()}',
                'course_nature': nature,
            })
            self.assertEqual(ct.course_nature, nature)

    def test_action_apply_defaults_to_courses(self):
        university = self.env['uni.university'].create({
            'name': 'Apply Default Uni',
            'code': 'ADU',
        })
        college = self.env['uni.college'].create({
            'name': 'Apply Default College',
            'code': 'ADC',
            'university_id': university.id,
        })
        ct = self.env['uni.course.type'].create({
            'name': 'Lab Type',
            'code': 'LT',
            'course_nature': 'laboratory',
            'default_credit_hours': 4,
            'default_contact_hours': 60,
        })
        course = self.env['uni.course'].create({
            'name': 'Lab Course',
            'code': 'LC01',
            'university_id': university.id,
            'college_id': college.id,
            'course_type_id': ct.id,
            'credit_hours': 0,
            'contact_hours': 0,
        })
        ct.action_apply_defaults_to_courses()
        self.assertEqual(course.credit_hours, 4)
        self.assertEqual(course.contact_hours, 60)


@tagged('post_install', '-at_install')
class TestCoursePrerequisite(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Prereq Test University',
            'code': 'PRU',
        })
        cls.college = cls.env['uni.college'].create({
            'name': 'Prereq College',
            'code': 'PRC',
            'university_id': cls.university.id,
        })
        cls.course1 = cls.env['uni.course'].create({
            'name': 'Intro to Programming',
            'code': 'PRG101',
            'university_id': cls.university.id,
            'college_id': cls.college.id,
            'credit_hours': 3.0,
            'contact_hours': 3.0,
        })
        cls.course2 = cls.env['uni.course'].create({
            'name': 'Data Structures',
            'code': 'PRG201',
            'university_id': cls.university.id,
            'college_id': cls.college.id,
            'credit_hours': 3.0,
            'contact_hours': 3.0,
        })
        cls.course3 = cls.env['uni.course'].create({
            'name': 'Algorithms',
            'code': 'PRG301',
            'university_id': cls.university.id,
            'college_id': cls.college.id,
            'credit_hours': 3.0,
            'contact_hours': 3.0,
        })

    def test_create_prerequisite(self):
        prereq = self.env['uni.course.prerequisite'].create({
            'course_id': self.course2.id,
            'prerequisite_course_id': self.course1.id,
            'minimum_grade': 'C',
            'is_strict': True,
        })
        self.assertEqual(prereq.course_id, self.course2)
        self.assertEqual(prereq.prerequisite_course_id, self.course1)

    def test_unique_prerequisite(self):
        self.env['uni.course.prerequisite'].create({
            'course_id': self.course2.id,
            'prerequisite_course_id': self.course1.id,
        })
        with self.assertRaises(Exception):
            self.env['uni.course.prerequisite'].create({
                'course_id': self.course2.id,
                'prerequisite_course_id': self.course1.id,
            })

    def test_self_prerequisite(self):
        with self.assertRaises(ValidationError):
            self.env['uni.course.prerequisite'].create({
                'course_id': self.course1.id,
                'prerequisite_course_id': self.course1.id,
            })

    def test_different_prerequisites_allowed(self):
        self.env['uni.course.prerequisite'].create({
            'course_id': self.course2.id,
            'prerequisite_course_id': self.course1.id,
        })
        prereq = self.env['uni.course.prerequisite'].create({
            'course_id': self.course2.id,
            'prerequisite_course_id': self.course3.id,
        })
        self.assertTrue(prereq)

    def test_minimum_grade_field(self):
        prereq = self.env['uni.course.prerequisite'].create({
            'course_id': self.course3.id,
            'prerequisite_course_id': self.course2.id,
            'minimum_grade': 'B',
        })
        self.assertEqual(prereq.minimum_grade, 'B')

    def test_prerequisite_code_stored(self):
        prereq = self.env['uni.course.prerequisite'].create({
            'course_id': self.course2.id,
            'prerequisite_course_id': self.course1.id,
        })
        self.assertEqual(prereq.prerequisite_course_code, self.course1.code)


@tagged('post_install', '-at_install')
class TestCourseEquivalent(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Equiv Test University',
            'code': 'ETU',
        })
        cls.college = cls.env['uni.college'].create({
            'name': 'Equiv College',
            'code': 'ECC',
            'university_id': cls.university.id,
        })
        cls.college2 = cls.env['uni.college'].create({
            'name': 'Other College',
            'code': 'OEC',
            'university_id': cls.university.id,
        })
        cls.course1 = cls.env['uni.course'].create({
            'name': 'Physics I',
            'code': 'PHY101',
            'university_id': cls.university.id,
            'college_id': cls.college.id,
            'credit_hours': 3.0,
            'contact_hours': 3.0,
        })
        cls.course2 = cls.env['uni.course'].create({
            'name': 'Physics I Applied',
            'code': 'PHY102',
            'university_id': cls.university.id,
            'college_id': cls.college2.id,
            'credit_hours': 3.0,
            'contact_hours': 3.0,
        })

    def test_create_equivalent(self):
        equiv = self.env['uni.course.equivalent'].create({
            'course_id': self.course1.id,
            'equivalent_course_id': self.course2.id,
            'equivalence_type': 'full',
            'equivalent_credit_hours': 3.0,
        })
        self.assertEqual(equiv.course_id, self.course1)
        self.assertEqual(equiv.equivalent_course_id, self.course2)
        self.assertEqual(equiv.equivalence_type, 'full')

    def test_unique_equivalent(self):
        self.env['uni.course.equivalent'].create({
            'course_id': self.course1.id,
            'equivalent_course_id': self.course2.id,
        })
        with self.assertRaises(Exception):
            self.env['uni.course.equivalent'].create({
                'course_id': self.course1.id,
                'equivalent_course_id': self.course2.id,
            })

    def test_self_equivalent(self):
        with self.assertRaises(ValidationError):
            self.env['uni.course.equivalent'].create({
                'course_id': self.course1.id,
                'equivalent_course_id': self.course1.id,
            })

    def test_equivalence_type_selection(self):
        for etype in ['full', 'partial']:
            equiv = self.env['uni.course.equivalent'].create({
                'course_id': self.course1.id,
                'equivalent_course_id': self.course2.id,
                'equivalence_type': etype,
            })
            self.assertEqual(equiv.equivalence_type, etype)

    def test_equivalent_credit_hours(self):
        equiv = self.env['uni.course.equivalent'].create({
            'course_id': self.course1.id,
            'equivalent_course_id': self.course2.id,
            'equivalent_credit_hours': 2.5,
        })
        self.assertEqual(equiv.equivalent_credit_hours, 2.5)

    def test_equivalent_code_stored(self):
        equiv = self.env['uni.course.equivalent'].create({
            'course_id': self.course1.id,
            'equivalent_course_id': self.course2.id,
        })
        self.assertEqual(equiv.equivalent_course_code, self.course2.code)


@tagged('post_install', '-at_install')
class TestEvaluationType(TransactionCase):

    def test_create_evaluation_type(self):
        et = self.env['uni.evaluation.type'].create({
            'name': 'Final Exam',
            'code': 'FE',
            'weight_type': 'percentage',
            'default_weight': 40.0,
            'description': 'End of term final examination.',
        })
        self.assertEqual(et.name, 'Final Exam')
        self.assertEqual(et.weight_type, 'percentage')
        self.assertEqual(et.default_weight, 40.0)
        self.assertTrue(et.active)

    def test_code_uniqueness(self):
        self.env['uni.evaluation.type'].create({
            'name': 'Midterm',
            'code': 'MT',
            'weight_type': 'percentage',
            'default_weight': 30.0,
        })
        with self.assertRaises(Exception):
            self.env['uni.evaluation.type'].create({
                'name': 'Midterm Dup',
                'code': 'MT',
                'weight_type': 'percentage',
            })

    def test_weight_type_selection(self):
        for wtype in ['percentage', 'points']:
            et = self.env['uni.evaluation.type'].create({
                'name': f'Type {wtype}',
                'code': f'T{wtype[:2].upper()}',
                'weight_type': wtype,
            })
            self.assertEqual(et.weight_type, wtype)

    def test_default_weight(self):
        et = self.env['uni.evaluation.type'].create({
            'name': 'Quiz',
            'code': 'QZ',
            'weight_type': 'percentage',
            'default_weight': 15.0,
        })
        self.assertEqual(et.default_weight, 15.0)


@tagged('post_install', '-at_install')
class TestProgramCourse(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'PC Test University',
            'code': 'PCU',
        })
        cls.college = cls.env['uni.college'].create({
            'name': 'PC College',
            'code': 'PCC',
            'university_id': cls.university.id,
        })
        cls.department = cls.env['uni.department'].create({
            'name': 'PC Department',
            'code': 'PCD',
            'university_id': cls.university.id,
            'college_id': cls.college.id,
        })
        cls.level = cls.env['uni.program.level'].create({
            'name': 'Bachelor',
            'code': 'BSPC',
        })
        cls.program = cls.env['uni.program'].create({
            'name': 'CS Program',
            'code': 'CSP',
            'university_id': cls.university.id,
            'college_id': cls.college.id,
            'department_id': cls.department.id,
            'level_id': cls.level.id,
        })
        cls.course1 = cls.env['uni.course'].create({
            'name': 'Intro to CS',
            'code': 'ICS101',
            'university_id': cls.university.id,
            'college_id': cls.college.id,
            'credit_hours': 3.0,
            'contact_hours': 3.0,
        })
        cls.course2 = cls.env['uni.course'].create({
            'name': 'Data Structures',
            'code': 'DS201',
            'university_id': cls.university.id,
            'college_id': cls.college.id,
            'credit_hours': 3.0,
            'contact_hours': 3.0,
        })

    def test_create_program_course(self):
        pc = self.env['uni.program.course'].create({
            'program_id': self.program.id,
            'course_id': self.course1.id,
            'level': '1',
            'semester': 1,
            'credit_hours': 3.0,
            'is_mandatory': True,
        })
        self.assertEqual(pc.program_id, self.program)
        self.assertEqual(pc.course_id, self.course1)
        self.assertTrue(pc.is_mandatory)

    def test_unique_program_course(self):
        self.env['uni.program.course'].create({
            'program_id': self.program.id,
            'course_id': self.course1.id,
        })
        with self.assertRaises(Exception):
            self.env['uni.program.course'].create({
                'program_id': self.program.id,
                'course_id': self.course1.id,
            })

    def test_same_course_different_programs(self):
        program2 = self.env['uni.program'].create({
            'name': 'EE Program',
            'code': 'EEP',
            'university_id': self.university.id,
            'college_id': self.college.id,
            'level_id': self.level.id,
        })
        self.env['uni.program.course'].create({
            'program_id': self.program.id,
            'course_id': self.course1.id,
        })
        pc2 = self.env['uni.program.course'].create({
            'program_id': program2.id,
            'course_id': self.course1.id,
        })
        self.assertTrue(pc2)

    def test_effective_credit_hours_from_course(self):
        pc = self.env['uni.program.course'].create({
            'program_id': self.program.id,
            'course_id': self.course1.id,
            'credit_hours': 0.0,
        })
        pc._compute_effective_credit_hours()
        self.assertEqual(pc.effective_credit_hours, 3.0)

    def test_effective_credit_hours_override(self):
        pc = self.env['uni.program.course'].create({
            'program_id': self.program.id,
            'course_id': self.course1.id,
            'credit_hours': 4.0,
        })
        pc._compute_effective_credit_hours()
        self.assertEqual(pc.effective_credit_hours, 4.0)

    def test_semester_positive_constraint(self):
        with self.assertRaises(Exception):
            self.env['uni.program.course'].create({
                'program_id': self.program.id,
                'course_id': self.course1.id,
                'semester': 0,
            })

    def test_credit_hours_positive_constraint(self):
        with self.assertRaises(Exception):
            self.env['uni.program.course'].create({
                'program_id': self.program.id,
                'course_id': self.course1.id,
                'credit_hours': -1.0,
            })

    def test_onchange_course_id(self):
        pc = self.env['uni.program.course'].new({
            'program_id': self.program.id,
            'course_id': self.course1.id,
            'credit_hours': 0.0,
        })
        pc._onchange_course_id()
        self.assertEqual(pc.credit_hours, 3.0)

    def test_onchange_course_id_no_override(self):
        pc = self.env['uni.program.course'].new({
            'program_id': self.program.id,
            'course_id': self.course1.id,
            'credit_hours': 5.0,
        })
        pc._onchange_course_id()
        self.assertEqual(pc.credit_hours, 5.0)

    def test_self_prerequisite_in_program(self):
        pc = self.env['uni.program.course'].create({
            'program_id': self.program.id,
            'course_id': self.course1.id,
        })
        with self.assertRaises(ValidationError):
            pc.write({
                'prerequisite_course_ids': [(6, 0, [self.course1.id])],
            })

    def test_related_fields(self):
        pc = self.env['uni.program.course'].create({
            'program_id': self.program.id,
            'course_id': self.course1.id,
        })
        self.assertEqual(pc.university_id, self.university)
        self.assertEqual(pc.college_id, self.college)
        self.assertEqual(pc.department_id, self.department)

    def test_action_view_lines(self):
        pc = self.env['uni.program.course'].create({
            'program_id': self.program.id,
            'course_id': self.course1.id,
        })
        action = pc.action_view_lines()
        self.assertEqual(action['res_model'], 'uni.program.course.line')
