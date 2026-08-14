# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError


@tagged('post_install', '-at_install')
class TestUniInternshipEvaluation(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
        })
        cls.entity = cls.env['uni.internship.training.entity'].create({
            'name': 'Eval Entity',
            'entity_code': 'EE001',
            'entity_type': 'private',
        })
        cls.course = cls.env['uni.course'].create({
            'name': 'Eval Course',
            'code': 'EC001',
            'university_id': cls.university.id,
        })
        cls.internship = cls.env['uni.internship'].create({
            'course_id': cls.course.id,
            'training_entity_id': cls.entity.id,
        })
        cls.evaluation = cls.env['uni.internship.evaluation'].create({
            'internship_id': cls.internship.id,
            'evaluation_type': 'individual',
            'evaluator_type': 'academic',
            'individual_score': 85.0,
            'max_score': 100.0,
        })

    def test_create_evaluation(self):
        self.assertTrue(self.evaluation)
        self.assertTrue(self.evaluation.name)
        self.assertEqual(self.evaluation.state, 'draft')

    def test_evaluation_workflow(self):
        self.evaluation.action_complete()
        self.assertEqual(self.evaluation.state, 'completed')
        self.evaluation.action_finalize()
        self.assertEqual(self.evaluation.state, 'finalized')

    def test_evaluation_score_percentage(self):
        self.assertEqual(self.evaluation.score_percentage, 85.0)
        self.assertTrue(self.evaluation.is_passing)

    def test_evaluation_appeal(self):
        self.evaluation.action_complete()
        self.evaluation.action_appeal()
        self.assertEqual(self.evaluation.state, 'appealed')

    def test_evaluation_type_constraint(self):
        with self.assertRaises(ValidationError):
            self.env['uni.internship.evaluation'].create({
                'internship_id': self.internship.id,
                'evaluation_type': 'team',
                'evaluator_type': 'academic',
                'team_score': 80.0,
            })
