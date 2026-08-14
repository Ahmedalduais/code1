# -*- coding: utf-8 -*-
import json

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestGradeLetter(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.grade_a = cls.env['uni.grade.letter'].create({
            'name': 'A',
            'code': 'A',
            'gpa_value': 4.0,
            'percentage_min': 90.0,
            'percentage_max': 100.0,
            'sequence': 1,
        })
        cls.grade_b = cls.env['uni.grade.letter'].create({
            'name': 'B',
            'code': 'B',
            'gpa_value': 3.0,
            'percentage_min': 80.0,
            'percentage_max': 89.99,
            'sequence': 2,
        })
        cls.grade_c = cls.env['uni.grade.letter'].create({
            'name': 'C',
            'code': 'C',
            'gpa_value': 2.0,
            'percentage_min': 70.0,
            'percentage_max': 79.99,
            'sequence': 3,
        })
        cls.grade_d = cls.env['uni.grade.letter'].create({
            'name': 'D',
            'code': 'D',
            'gpa_value': 1.0,
            'percentage_min': 60.0,
            'percentage_max': 69.99,
            'sequence': 4,
        })
        cls.grade_f = cls.env['uni.grade.letter'].create({
            'name': 'F',
            'code': 'F',
            'gpa_value': 0.0,
            'percentage_min': 0.0,
            'percentage_max': 59.99,
            'sequence': 5,
        })

    def test_create_grade_letter(self):
        self.assertEqual(self.grade_a.name, 'A')
        self.assertEqual(self.grade_a.gpa_value, 4.0)
        self.assertEqual(self.grade_a.percentage_min, 90.0)
        self.assertEqual(self.grade_a.percentage_max, 100.0)

    def test_code_uniqueness(self):
        with self.assertRaises(Exception):
            self.env['uni.grade.letter'].create({
                'name': 'A Duplicate',
                'code': 'A',
                'gpa_value': 4.0,
                'percentage_min': 90.0,
                'percentage_max': 100.0,
            })

    def test_gpa_value_positive(self):
        with self.assertRaises(Exception):
            self.env['uni.grade.letter'].create({
                'name': 'Neg',
                'code': 'NEG',
                'gpa_value': -1.0,
            })

    def test_percentage_range_constraint(self):
        with self.assertRaises(Exception):
            self.env['uni.grade.letter'].create({
                'name': 'Bad Range',
                'code': 'BR',
                'gpa_value': 2.0,
                'percentage_min': 80.0,
                'percentage_max': 50.0,
            })

    def test_get_grade_for_percentage(self):
        grade = self.env['uni.grade.letter'].get_grade_for_percentage(95.0)
        self.assertEqual(grade.code, 'A')

        grade = self.env['uni.grade.letter'].get_grade_for_percentage(85.0)
        self.assertEqual(grade.code, 'B')

        grade = self.env['uni.grade.letter'].get_grade_for_percentage(75.0)
        self.assertEqual(grade.code, 'C')

        grade = self.env['uni.grade.letter'].get_grade_for_percentage(65.0)
        self.assertEqual(grade.code, 'D')

        grade = self.env['uni.grade.letter'].get_grade_for_percentage(50.0)
        self.assertEqual(grade.code, 'F')

    def test_get_grade_for_percentage_boundary(self):
        grade = self.env['uni.grade.letter'].get_grade_for_percentage(90.0)
        self.assertEqual(grade.code, 'A')

        grade = self.env['uni.grade.letter'].get_grade_for_percentage(100.0)
        self.assertEqual(grade.code, 'A')

        grade = self.env['uni.grade.letter'].get_grade_for_percentage(0.0)
        self.assertEqual(grade.code, 'F')

    def test_archived_grade_not_returned(self):
        self.grade_a.active = False
        grade = self.env['uni.grade.letter'].get_grade_for_percentage(95.0)
        self.assertNotEqual(grade.code, 'A')


@tagged('post_install', '-at_install')
class TestGradingSystem(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.grade_letters = {}
        for name, code, gpa, pmin, pmax, seq in [
            ('A', 'A', 4.0, 90, 100, 1),
            ('B', 'B', 3.0, 80, 89.99, 2),
            ('C', 'C', 2.0, 70, 79.99, 3),
            ('D', 'D', 1.0, 60, 69.99, 4),
            ('F', 'F', 0.0, 0, 59.99, 5),
        ]:
            cls.grade_letters[code] = cls.env['uni.grade.letter'].create({
                'name': name,
                'code': code,
                'gpa_value': gpa,
                'percentage_min': pmin,
                'percentage_max': pmax,
                'sequence': seq,
            })

        cls.system = cls.env['uni.grading.system'].create({
            'name': 'Standard 4.0',
            'code': 'STD4',
            'scale_max': 100.0,
            'passing_grade': 60.0,
            'gpa_scale': 4.0,
            'system_type': 'percentage',
            'grade_letter_ids': [(6, 0, list(cls.grade_letters.values()))],
        })
        cls.gl_a = cls.grade_letters['A']
        cls.gl_b = cls.grade_letters['B']
        cls.gl_c = cls.grade_letters['C']
        cls.gl_d = cls.grade_letters['D']
        cls.gl_f = cls.grade_letters['F']

    def _create_scale_lines(self):
        lines = [
            (0, 0, {
                'grade_letter_id': self.gl_a.id,
                'percentage_min': 90,
                'percentage_max': 100,
            }),
            (0, 0, {
                'grade_letter_id': self.gl_b.id,
                'percentage_min': 80,
                'percentage_max': 89.99,
            }),
            (0, 0, {
                'grade_letter_id': self.gl_c.id,
                'percentage_min': 70,
                'percentage_max': 79.99,
            }),
            (0, 0, {
                'grade_letter_id': self.gl_d.id,
                'percentage_min': 60,
                'percentage_max': 69.99,
            }),
            (0, 0, {
                'grade_letter_id': self.gl_f.id,
                'percentage_min': 0,
                'percentage_max': 59.99,
            }),
        ]
        self.system.write({'scale_line_ids': lines})

    def test_create_grading_system(self):
        self.assertEqual(self.system.name, 'Standard 4.0')
        self.assertEqual(self.system.scale_max, 100.0)
        self.assertEqual(self.system.passing_grade, 60.0)

    def test_code_uniqueness(self):
        with self.assertRaises(Exception):
            self.env['uni.grading.system'].create({
                'name': 'Duplicate',
                'code': 'STD4',
                'scale_max': 100.0,
                'passing_grade': 60.0,
                'gpa_scale': 4.0,
            })

    def test_add_scale_lines(self):
        self._create_scale_lines()
        self.assertEqual(len(self.system.scale_line_ids), 5)

    def test_get_grade_letter_for_percentage(self):
        self._create_scale_lines()
        grade = self.system.get_grade_letter_for_percentage(95.0)
        self.assertEqual(grade.code, 'A')

        grade = self.system.get_grade_letter_for_percentage(85.0)
        self.assertEqual(grade.code, 'B')

        grade = self.system.get_grade_letter_for_percentage(50.0)
        self.assertEqual(grade.code, 'F')

    def test_get_grade_letter_for_percentage_no_match(self):
        self._create_scale_lines()
        grade = self.system.get_grade_letter_for_percentage(150.0)
        self.assertFalse(grade)

    def test_compute_gpa_value(self):
        gpa = self.system.compute_gpa_value(100.0)
        self.assertAlmostEqual(gpa, 4.0, places=2)

        gpa = self.system.compute_gpa_value(50.0)
        self.assertAlmostEqual(gpa, 2.0, places=2)

        gpa = self.system.compute_gpa_value(0.0)
        self.assertAlmostEqual(gpa, 0.0, places=2)

    def test_is_default_uniqueness(self):
        self.system.is_default = True
        system2 = self.env['uni.grading.system'].create({
            'name': 'Second System',
            'code': 'SEC2',
            'scale_max': 100.0,
            'passing_grade': 60.0,
            'gpa_scale': 4.0,
        })
        system2.is_default = True
        system2._check_is_default()
        self.assertFalse(self.system.is_default)
        self.assertTrue(system2.is_default)

    def test_get_default_system(self):
        self.system.is_default = True
        default = self.env['uni.grading.system'].get_default_system()
        self.assertEqual(default, self.system)

    def test_get_default_system_fallback(self):
        self.system.is_default = False
        default = self.env['uni.grading.system'].get_default_system()
        self.assertEqual(default, self.system)

    def test_onchange_system_type_percentage(self):
        sys = self.env['uni.grading.system'].new({
            'system_type': 'percentage',
            'gpa_scale': 4.0,
        })
        sys._onchange_system_type()
        self.assertEqual(sys.scale_max, 100.0)

    def test_onchange_system_type_gpa(self):
        sys = self.env['uni.grading.system'].new({
            'system_type': 'gpa',
            'gpa_scale': 5.0,
        })
        sys._onchange_system_type()
        self.assertEqual(sys.scale_max, 5.0)


@tagged('post_install', '-at_install')
class TestGradingEngine(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.engine = cls.env['uni.grading.engine']

    def test_calculate_weighted_average(self):
        lines = [
            {'value': 90, 'weight': 30},
            {'value': 80, 'weight': 30},
            {'value': 70, 'weight': 40},
        ]
        result = self.engine.calculate_weighted_average(lines)
        expected = (90 * 30 + 80 * 30 + 70 * 40) / 100
        self.assertAlmostEqual(result, expected, places=2)

    def test_calculate_weighted_average_empty(self):
        result = self.engine.calculate_weighted_average([])
        self.assertEqual(result, 0.0)

    def test_calculate_weighted_average_zero_weight(self):
        lines = [
            {'value': 90, 'weight': 0},
            {'value': 80, 'weight': 0},
        ]
        result = self.engine.calculate_weighted_average(lines)
        self.assertEqual(result, 0.0)

    def test_calculate_gpa(self):
        course_grades = [
            {'gpa_value': 4.0, 'credit_hours': 3},
            {'gpa_value': 3.0, 'credit_hours': 4},
            {'gpa_value': 2.0, 'credit_hours': 3},
        ]
        result = self.engine.calculate_gpa(course_grades)
        expected = (4.0 * 3 + 3.0 * 4 + 2.0 * 3) / 10
        self.assertAlmostEqual(result, expected, places=2)

    def test_calculate_gpa_empty(self):
        result = self.engine.calculate_gpa([])
        self.assertEqual(result, 0.0)

    def test_calculate_gpa_zero_credits(self):
        result = self.engine.calculate_gpa([
            {'gpa_value': 4.0, 'credit_hours': 0},
        ])
        self.assertEqual(result, 0.0)

    def test_calculate_cumulative_gpa(self):
        term_gpas = [
            {'gpa': 3.5, 'total_credits': 15},
            {'gpa': 3.2, 'total_credits': 18},
        ]
        result = self.engine.calculate_cumulative_gpa(term_gpas)
        expected = (3.5 * 15 + 3.2 * 18) / 33
        self.assertAlmostEqual(result, expected, places=2)

    def test_calculate_cumulative_gpa_empty(self):
        result = self.engine.calculate_cumulative_gpa([])
        self.assertEqual(result, 0.0)

    def test_determine_status_excellent(self):
        self.assertEqual(self.engine.determine_status(3.8), 'excellent')

    def test_determine_status_very_good(self):
        self.assertEqual(self.engine.determine_status(3.2), 'very_good')

    def test_determine_status_good(self):
        self.assertEqual(self.engine.determine_status(2.7), 'good')

    def test_determine_status_acceptable(self):
        self.assertEqual(self.engine.determine_status(2.0), 'acceptable')

    def test_determine_status_probation(self):
        self.assertEqual(self.engine.determine_status(1.5), 'probation')

    def test_determine_status_dismissed(self):
        self.assertEqual(self.engine.determine_status(0.5), 'dismissed')


@tagged('post_install', '-at_install')
class TestGradingCalculator(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Calc Test University',
            'code': 'CTU',
        })
        cls.grade_letters = {}
        for name, code, gpa, pmin, pmax, seq in [
            ('A', 'A', 4.0, 90, 100, 1),
            ('B', 'B', 3.0, 80, 89.99, 2),
            ('C', 'C', 2.0, 70, 79.99, 3),
            ('D', 'D', 1.0, 60, 69.99, 4),
            ('F', 'F', 0.0, 0, 59.99, 5),
        ]:
            cls.grade_letters[code] = cls.env['uni.grade.letter'].create({
                'name': name,
                'code': code,
                'gpa_value': gpa,
                'percentage_min': pmin,
                'percentage_max': pmax,
                'sequence': seq,
            })
        cls.system = cls.env['uni.grading.system'].create({
            'name': 'Calculator System',
            'code': 'CALC',
            'scale_max': 100.0,
            'passing_grade': 60.0,
            'gpa_scale': 4.0,
            'system_type': 'percentage',
            'grade_letter_ids': [(6, 0, list(cls.grade_letters.values()))],
        })
        cls.system.write({'scale_line_ids': [
            (0, 0, {
                'grade_letter_id': cls.grade_letters['A'].id,
                'percentage_min': 90,
                'percentage_max': 100,
            }),
            (0, 0, {
                'grade_letter_id': cls.grade_letters['B'].id,
                'percentage_min': 80,
                'percentage_max': 89.99,
            }),
            (0, 0, {
                'grade_letter_id': cls.grade_letters['C'].id,
                'percentage_min': 70,
                'percentage_max': 79.99,
            }),
            (0, 0, {
                'grade_letter_id': cls.grade_letters['D'].id,
                'percentage_min': 60,
                'percentage_max': 69.99,
            }),
            (0, 0, {
                'grade_letter_id': cls.grade_letters['F'].id,
                'percentage_min': 0,
                'percentage_max': 59.99,
            }),
        ]})

    def test_action_calculate_weighted_grades(self):
        calc = self.env['uni.grading.calculator'].create({
            'name': 'Test Calc 1',
            'university_id': self.university.id,
            'grading_system_id': self.system.id,
            'input_data': json.dumps([
                {'value': 90, 'weight': 30},
                {'value': 80, 'weight': 30},
                {'value': 70, 'weight': 40},
            ]),
        })
        calc.action_calculate()
        self.assertEqual(calc.state, 'calculated')
        self.assertTrue(calc.calc_date)
        expected = (90 * 30 + 80 * 30 + 70 * 40) / 100
        self.assertAlmostEqual(calc.result_percentage, expected, places=2)

    def test_action_calculate_gpa_courses(self):
        calc = self.env['uni.grading.calculator'].create({
            'name': 'Test Calc 2',
            'university_id': self.university.id,
            'grading_system_id': self.system.id,
            'input_data': json.dumps([
                {'gpa_value': 4.0, 'credit_hours': 3},
                {'gpa_value': 3.0, 'credit_hours': 4},
            ]),
        })
        calc.action_calculate()
        self.assertEqual(calc.state, 'calculated')
        expected = (4.0 * 3 + 3.0 * 4) / 7
        self.assertAlmostEqual(calc.result_gpa, expected, places=2)

    def test_action_calculate_empty_data(self):
        calc = self.env['uni.grading.calculator'].create({
            'name': 'Test Calc Empty',
            'university_id': self.university.id,
            'grading_system_id': self.system.id,
            'input_data': '[]',
        })
        calc.action_calculate()
        self.assertEqual(calc.state, 'calculated')
        self.assertEqual(calc.result_gpa, 0.0)

    def test_action_calculate_invalid_json(self):
        calc = self.env['uni.grading.calculator'].create({
            'name': 'Test Calc Bad JSON',
            'university_id': self.university.id,
            'grading_system_id': self.system.id,
            'input_data': 'not json',
        })
        calc.action_calculate()
        self.assertEqual(calc.state, 'calculated')
        self.assertEqual(calc.result_gpa, 0.0)

    def test_action_cancel(self):
        calc = self.env['uni.grading.calculator'].create({
            'name': 'Test Calc Cancel',
            'university_id': self.university.id,
            'grading_system_id': self.system.id,
        })
        calc.action_cancel()
        self.assertEqual(calc.state, 'cancelled')

    def test_action_reset(self):
        calc = self.env['uni.grading.calculator'].create({
            'name': 'Test Calc Reset',
            'university_id': self.university.id,
            'grading_system_id': self.system.id,
            'input_data': json.dumps([
                {'value': 95, 'weight': 100},
            ]),
        })
        calc.action_calculate()
        self.assertEqual(calc.state, 'calculated')
        self.assertGreater(calc.result_gpa, 0)
        calc.action_reset()
        self.assertEqual(calc.state, 'draft')
        self.assertEqual(calc.result_gpa, 0.0)
        self.assertEqual(calc.result_percentage, 0.0)
        self.assertFalse(calc.result_grade_letter)

    def test_name_auto_generation(self):
        calc = self.env['uni.grading.calculator'].create({
            'university_id': self.university.id,
            'grading_system_id': self.system.id,
        })
        self.assertNotEqual(calc.name, 'New')


@tagged('post_install', '-at_install')
class TestGradeConversion(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.grade_letters = {}
        for name, code, gpa, pmin, pmax, seq in [
            ('A', 'A', 4.0, 90, 100, 1),
            ('B', 'B', 3.0, 80, 89.99, 2),
            ('C', 'C', 2.0, 70, 79.99, 3),
            ('D', 'D', 1.0, 60, 69.99, 4),
            ('F', 'F', 0.0, 0, 59.99, 5),
        ]:
            cls.grade_letters[code] = cls.env['uni.grade.letter'].create({
                'name': name,
                'code': code,
                'gpa_value': gpa,
                'percentage_min': pmin,
                'percentage_max': pmax,
                'sequence': seq,
            })

        cls.system_4 = cls.env['uni.grading.system'].create({
            'name': '4.0 Scale',
            'code': 'S4',
            'scale_max': 100.0,
            'passing_grade': 60.0,
            'gpa_scale': 4.0,
            'system_type': 'percentage',
            'grade_letter_ids': [(6, 0, list(cls.grade_letters.values()))],
        })
        cls.system_5 = cls.env['uni.grading.system'].create({
            'name': '5.0 Scale',
            'code': 'S5',
            'scale_max': 100.0,
            'passing_grade': 60.0,
            'gpa_scale': 5.0,
            'system_type': 'percentage',
            'grade_letter_ids': [(6, 0, list(cls.grade_letters.values()))],
        })

        cls.grade_a_plus = cls.env['uni.grade.letter'].create({
            'name': 'A+',
            'code': 'A+',
            'gpa_value': 5.0,
            'percentage_min': 90.0,
            'percentage_max': 100.0,
            'sequence': 1,
        })
        cls.grade_b_plus = cls.env['uni.grade.letter'].create({
            'name': 'B+',
            'code': 'B+',
            'gpa_value': 4.0,
            'percentage_min': 80.0,
            'percentage_max': 89.99,
            'sequence': 2,
        })

    def test_create_conversion(self):
        conv = self.env['uni.grade.conversion'].create({
            'from_system_id': self.system_4.id,
            'to_system_id': self.system_5.id,
            'from_grade_letter_id': self.grade_letters['A'].id,
            'to_grade_letter_id': self.grade_a_plus.id,
            'from_value_min': 90.0,
            'from_value_max': 100.0,
            'to_value': 5.0,
        })
        self.assertTrue(conv.name)
        self.assertIn('4.0 Scale', conv.name)
        self.assertIn('5.0 Scale', conv.name)

    def test_unique_conversion_constraint(self):
        self.env['uni.grade.conversion'].create({
            'from_system_id': self.system_4.id,
            'to_system_id': self.system_5.id,
            'from_grade_letter_id': self.grade_letters['A'].id,
            'to_grade_letter_id': self.grade_a_plus.id,
        })
        with self.assertRaises(Exception):
            self.env['uni.grade.conversion'].create({
                'from_system_id': self.system_4.id,
                'to_system_id': self.system_5.id,
                'from_grade_letter_id': self.grade_letters['A'].id,
                'to_grade_letter_id': self.grade_a_plus.id,
            })

    def test_different_systems_constraint(self):
        with self.assertRaises(Exception):
            self.env['uni.grade.conversion'].create({
                'from_system_id': self.system_4.id,
                'to_system_id': self.system_4.id,
                'from_grade_letter_id': self.grade_letters['A'].id,
                'to_grade_letter_id': self.grade_a_plus.id,
            })

    def test_convert_grade(self):
        self.env['uni.grade.conversion'].create({
            'from_system_id': self.system_4.id,
            'to_system_id': self.system_5.id,
            'from_grade_letter_id': self.grade_letters['A'].id,
            'to_grade_letter_id': self.grade_a_plus.id,
        })
        result = self.env['uni.grade.conversion'].convert_grade(
            self.system_4.id, self.system_5.id, self.grade_letters['A'].id
        )
        self.assertEqual(result, self.grade_a_plus)

    def test_convert_grade_no_conversion(self):
        result = self.env['uni.grade.conversion'].convert_grade(
            self.system_4.id, self.system_5.id, self.grade_letters['F'].id
        )
        self.assertFalse(result)

    def test_compute_name(self):
        conv = self.env['uni.grade.conversion'].create({
            'from_system_id': self.system_4.id,
            'to_system_id': self.system_5.id,
            'from_grade_letter_id': self.grade_letters['B'].id,
            'to_grade_letter_id': self.grade_b_plus.id,
        })
        self.assertEqual(
            conv.name,
            f'{self.system_4.name} \u2192 {self.system_5.name} ({self.grade_letters["B"].code})'
        )
