# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError
from odoo import fields


@tagged('post_install', '-at_install')
class TestFeeType(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fee_type = cls.env['uni.fee.type'].create({
            'name': 'Tuition Fee',
            'code': 'TUITION',
            'fee_category': 'tuition',
            'is_recurring': True,
            'default_amount': 5000.0,
        })

    def test_create_fee_type(self):
        self.assertEqual(self.fee_type.name, 'Tuition Fee')
        self.assertEqual(self.fee_type.code, 'TUITION')
        self.assertTrue(self.fee_type.is_recurring)
        self.assertEqual(self.fee_type.default_amount, 5000.0)

    def test_code_uniqueness(self):
        with self.assertRaises(Exception):
            self.env['uni.fee.type'].create({
                'name': 'Duplicate Fee',
                'code': 'TUITION',
            })

    def test_amount_validation_negative(self):
        with self.assertRaises(Exception):
            self.env['uni.fee.type'].create({
                'name': 'Negative Fee',
                'code': 'NEG-FEE',
                'default_amount': -100.0,
            })


@tagged('post_install', '-at_install')
class TestFeeStructure(TransactionCase):

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
        cls.fee_type_tuition = cls.env['uni.fee.type'].create({
            'name': 'Tuition Fee',
            'code': 'TUITION',
            'fee_category': 'tuition',
            'default_amount': 5000.0,
        })
        cls.fee_type_lab = cls.env['uni.fee.type'].create({
            'name': 'Lab Fee',
            'code': 'LAB',
            'fee_category': 'lab',
            'default_amount': 500.0,
        })
        cls.structure = cls.env['uni.fee.structure'].create({
            'name': 'BS CS 2025 Fee Structure',
            'code': 'FSTRUCT-BSCS-2025',
            'university_id': cls.university.id,
            'college_id': cls.college.id,
            'effective_date': '2025-09-01',
            'expiry_date': '2026-06-30',
            'line_ids': [
                (0, 0, {
                    'fee_type_id': cls.fee_type_tuition.id,
                    'amount': 5000.0,
                }),
                (0, 0, {
                    'fee_type_id': cls.fee_type_lab.id,
                    'amount': 500.0,
                }),
            ],
        })

    def test_create_structure(self):
        self.assertEqual(self.structure.name, 'BS CS 2025 Fee Structure')
        self.assertEqual(self.structure.state, 'draft')
        self.assertEqual(len(self.structure.line_ids), 2)

    def test_code_uniqueness(self):
        with self.assertRaises(Exception):
            self.env['uni.fee.structure'].create({
                'name': 'Duplicate Structure',
                'code': 'FSTRUCT-BSCS-2025',
                'university_id': self.university.id,
            })

    def test_date_validation_expiry_before_effective(self):
        with self.assertRaises(ValidationError):
            self.env['uni.fee.structure'].create({
                'name': 'Bad Dates Structure',
                'code': 'FSTRUCT-BAD',
                'university_id': self.university.id,
                'effective_date': '2026-06-30',
                'expiry_date': '2025-09-01',
            })

    def test_total_computation(self):
        self.assertEqual(self.structure.total_amount, 5500.0)

    def test_activate_structure(self):
        self.structure.action_activate()
        self.assertEqual(self.structure.state, 'active')

    def test_activate_requires_lines(self):
        empty_structure = self.env['uni.fee.structure'].create({
            'name': 'Empty Structure',
            'code': 'FSTRUCT-EMPTY',
            'university_id': self.university.id,
        })
        with self.assertRaises(ValidationError):
            empty_structure.action_activate()

    def test_close_structure(self):
        self.structure.action_activate()
        self.structure.action_close()
        self.assertEqual(self.structure.state, 'closed')

    def test_reopen_to_draft(self):
        self.structure.action_activate()
        self.structure.action_draft()
        self.assertEqual(self.structure.state, 'draft')


@tagged('post_install', '-at_install')
class TestScholarship(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
            'code': 'TU',
        })
        cls.person = cls.env['uni.person'].create({
            'name': 'Scholarship Student',
            'university_id': cls.university.id,
            'person_type': 'student',
        })
        cls.student = cls.env['uni.student'].create({
            'person_id': cls.person.id,
            'state': 'active',
        })
        cls.scholarship_type = cls.env['uni.scholarship.type'].create({
            'name': 'Merit Scholarship',
            'code': 'SCH-MERIT',
            'scholarship_nature': 'merit',
            'default_percentage': 50.0,
        })
        cls.scholarship = cls.env['uni.scholarship'].create({
            'student_id': cls.student.id,
            'scholarship_type_id': cls.scholarship_type.id,
            'discount_percentage': 50.0,
            'start_date': '2025-09-01',
            'end_date': '2026-06-30',
        })

    def test_create_scholarship(self):
        self.assertTrue(self.scholarship.name)
        self.assertEqual(self.scholarship.discount_percentage, 50.0)
        self.assertEqual(self.scholarship.approval_status, 'draft')

    def test_amount_validation_negative_percentage(self):
        with self.assertRaises(ValidationError):
            self.env['uni.scholarship'].create({
                'student_id': self.student.id,
                'scholarship_type_id': self.scholarship_type.id,
                'discount_percentage': -10.0,
            })

    def test_amount_validation_negative_discount(self):
        with self.assertRaises(Exception):
            self.env['uni.scholarship'].create({
                'student_id': self.student.id,
                'scholarship_type_id': self.scholarship_type.id,
                'discount_amount': -100.0,
            })

    def test_date_validation_end_before_start(self):
        with self.assertRaises(ValidationError):
            self.env['uni.scholarship'].create({
                'student_id': self.student.id,
                'scholarship_type_id': self.scholarship_type.id,
                'start_date': '2026-06-30',
                'end_date': '2025-09-01',
            })

    def test_state_workflow_draft_to_pending(self):
        self.scholarship.action_submit()
        self.assertEqual(self.scholarship.approval_status, 'pending')

    def test_state_workflow_pending_to_approved(self):
        self.scholarship.action_submit()
        self.scholarship.action_approve()
        self.assertEqual(self.scholarship.approval_status, 'approved')
        self.assertTrue(self.scholarship.approved_by)

    def test_state_workflow_approved_to_active(self):
        self.scholarship.action_submit()
        self.scholarship.action_approve()
        self.scholarship.action_activate()
        self.assertEqual(self.scholarship.approval_status, 'active')

    def test_state_workflow_active_to_terminated(self):
        self.scholarship.action_submit()
        self.scholarship.action_approve()
        self.scholarship.action_activate()
        self.scholarship.action_terminate()
        self.assertEqual(self.scholarship.approval_status, 'terminated')

    def test_state_workflow_pending_to_rejected(self):
        self.scholarship.action_submit()
        self.scholarship.action_reject()
        self.assertEqual(self.scholarship.approval_status, 'rejected')

    def test_state_workflow_rejected_to_draft(self):
        self.scholarship.action_submit()
        self.scholarship.action_reject()
        self.scholarship.action_draft()
        self.assertEqual(self.scholarship.approval_status, 'draft')


@tagged('post_install', '-at_install')
class TestInvoiceStudent(TransactionCase):

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
            'name': 'Invoice Student',
            'university_id': cls.university.id,
            'person_type': 'student',
        })
        cls.student = cls.env['uni.student'].create({
            'person_id': cls.person.id,
            'college_id': cls.college.id,
            'state': 'active',
        })
        cls.fee_type = cls.env['uni.fee.type'].create({
            'name': 'Tuition Fee',
            'code': 'TUITION',
            'fee_category': 'tuition',
            'default_amount': 5000.0,
        })
        cls.invoice = cls.env['uni.invoice.student'].create({
            'student_id': cls.student.id,
            'invoice_date': '2025-09-01',
            'due_date': '2025-10-01',
            'line_ids': [
                (0, 0, {
                    'fee_type_id': cls.fee_type.id,
                    'description': 'Tuition Fee',
                    'quantity': 1.0,
                    'price_unit': 5000.0,
                }),
            ],
        })

    def test_create_invoice(self):
        self.assertTrue(self.invoice.name)
        self.assertEqual(self.invoice.state, 'draft')
        self.assertEqual(self.invoice.amount_total, 5000.0)

    def test_total_computation(self):
        self.assertEqual(self.invoice.amount_total, 5000.0)
        self.assertEqual(self.invoice.amount_paid, 0.0)
        self.assertEqual(self.invoice.amount_due, 5000.0)

    def test_state_workflow_draft_to_confirmed(self):
        self.invoice.action_confirm()
        self.assertEqual(self.invoice.state, 'confirmed')

    def test_confirm_requires_lines(self):
        empty_invoice = self.env['uni.invoice.student'].create({
            'student_id': self.student.id,
            'invoice_date': '2025-09-01',
        })
        with self.assertRaises(ValidationError):
            empty_invoice.action_confirm()

    def test_state_workflow_to_cancelled(self):
        self.invoice.action_cancel()
        self.assertEqual(self.invoice.state, 'cancelled')

    def test_state_workflow_cancelled_to_draft(self):
        self.invoice.action_cancel()
        self.invoice.action_draft()
        self.assertEqual(self.invoice.state, 'draft')

    def test_cannot_confirm_non_draft(self):
        self.invoice.action_confirm()
        with self.assertRaises(ValidationError):
            self.invoice.action_confirm()

    def test_cannot_reset_non_cancelled_to_draft(self):
        with self.assertRaises(ValidationError):
            self.invoice.action_draft()

    def test_discount_validation_exceeds_total(self):
        with self.assertRaises(ValidationError):
            self.invoice.write({'discount_amount': 6000.0})

    def test_date_validation_due_before_invoice(self):
        with self.assertRaises(ValidationError):
            self.env['uni.invoice.student'].create({
                'student_id': self.student.id,
                'invoice_date': '2025-10-01',
                'due_date': '2025-09-01',
            })


@tagged('post_install', '-at_install')
class TestPaymentPlan(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.university = cls.env['uni.university'].create({
            'name': 'Test University',
            'code': 'TU',
        })
        cls.person = cls.env['uni.person'].create({
            'name': 'Payment Student',
            'university_id': cls.university.id,
            'person_type': 'student',
        })
        cls.student = cls.env['uni.student'].create({
            'person_id': cls.person.id,
            'state': 'active',
        })
        cls.plan = cls.env['uni.payment.plan'].create({
            'student_id': cls.student.id,
            'total_amount': 12000.0,
            'installments_count': 4,
            'start_date': '2025-09-01',
            'frequency': 'monthly',
        })

    def test_create_plan(self):
        self.assertTrue(self.plan.name)
        self.assertEqual(self.plan.state, 'draft')
        self.assertEqual(self.plan.total_amount, 12000.0)

    def test_installment_computation(self):
        self.plan.action_generate_installments()
        self.assertEqual(len(self.plan.line_ids), 4)
        for line in self.plan.line_ids:
            self.assertEqual(line.amount, 3000.0)

    def test_activate_plan(self):
        self.plan.action_activate()
        self.assertEqual(self.plan.state, 'active')
        self.assertEqual(len(self.plan.line_ids), 4)

    def test_activate_requires_installments(self):
        plan_no_installments = self.env['uni.payment.plan'].create({
            'student_id': self.student.id,
            'total_amount': 5000.0,
            'installments_count': 0,
            'start_date': '2025-09-01',
        })
        with self.assertRaises(ValidationError):
            plan_no_installments.action_activate()

    def test_cancel_plan(self):
        self.plan.action_activate()
        self.plan.action_cancel()
        self.assertEqual(self.plan.state, 'cancelled')

    def test_state_workflow_cancelled_to_draft(self):
        self.plan.action_activate()
        self.plan.action_cancel()
        self.plan.action_draft()
        self.assertEqual(self.plan.state, 'draft')

    def test_complete_plan(self):
        self.plan.action_activate()
        for line in self.plan.line_ids:
            line.action_mark_paid()
        self.plan.action_complete()
        self.assertEqual(self.plan.state, 'completed')

    def test_complete_requires_all_paid(self):
        self.plan.action_activate()
        self.plan.line_ids[0].action_mark_paid()
        with self.assertRaises(ValidationError):
            self.plan.action_complete()

    def test_paid_amount_computation(self):
        self.plan.action_activate()
        self.assertEqual(self.plan.paid_amount, 0.0)
        self.plan.line_ids[0].action_mark_paid()
        self.plan.invalidate_recordset(['paid_amount'])
        self.assertEqual(self.plan.paid_amount, 3000.0)
