# -*- coding: utf-8 -*-
from odoo import api, fields, models


class UniGradingCalculator(models.Model):
    """حاسبة GPA — ترث من محرك الدرجات المجرد (وراثة كلاسيكية).
    
    توفر واجهة محسوبة لحساب المعدلات مع تخزين النتائج.
    """
    _name = 'uni.grading.calculator'
    _inherit = ['uni.grading.engine', 'mail.thread', 'mail.activity.mixin']
    _description = 'GPA Calculator'

    name = fields.Char(string='Calculation Reference', required=True, copy=False,
                      readonly=True, default='New', index=True)
    university_id = fields.Many2one('uni.university', string='University',
                                    required=True, ondelete='restrict', tracking=True, index=True)
    grading_system_id = fields.Many2one('uni.grading.system', string='Grading System',
                                        required=True, ondelete='restrict', tracking=True, index=True)
    calc_date = fields.Datetime(string='Calculation Date', default=fields.Datetime.now,
                                readonly=True, tracking=True)
    student_ref = fields.Char(string='Student Reference', tracking=True)
    input_data = fields.Text(string='Input Data (JSON)',
                             help='JSON array of {value, weight} or {gpa_value, credit_hours}.')
    result_gpa = fields.Float(string='Result GPA', digits=(4, 2), readonly=True, tracking=True)
    result_percentage = fields.Float(string='Result %', digits=(5, 2), readonly=True)
    result_grade_letter = fields.Char(string='Grade Letter', readonly=True)
    result_status = fields.Selection([
        ('excellent', 'Excellent'),
        ('very_good', 'Very Good'),
        ('good', 'Good'),
        ('acceptable', 'Acceptable'),
        ('probation', 'Probation'),
        ('dismissed', 'Dismissed'),
    ], string='Academic Status', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('calculated', 'Calculated'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('unique_calculator_name', 'unique(name)', 'Calculation reference must be unique!'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('uni.grading.calculator') or 'New'
        return super().create(vals_list)

    def action_calculate(self):
        """تنفيذ عملية حساب المعدل."""
        import json
        for rec in self:
            if not rec.input_data:
                continue
            try:
                data = json.loads(rec.input_data)
            except (ValueError, TypeError):
                data = []
            if not data:
                continue
            # Detect data type
            if isinstance(data, list) and data and 'gpa_value' in data[0]:
                gpa = rec.calculate_gpa(data, rec.grading_system_id.id)
                rec.result_gpa = gpa
                rec.result_status = rec.determine_status(
                    gpa, rec.grading_system_id.passing_grade / 25.0)
            elif isinstance(data, list) and data and 'value' in data[0]:
                percentage = rec.calculate_weighted_average(data)
                rec.result_percentage = percentage
                grade_letter = rec.convert_percentage_to_grade(
                    percentage, rec.grading_system_id.id)
                if grade_letter:
                    rec.result_grade_letter = grade_letter.code
                    rec.result_gpa = grade_letter.gpa_value
                else:
                    rec.result_gpa = rec.grading_system_id.compute_gpa_value(percentage)
                rec.result_status = rec.determine_status(
                    rec.result_gpa, rec.grading_system_id.passing_grade / 25.0)
            rec.state = 'calculated'
            rec.calc_date = fields.Datetime.now()

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'

    def action_reset(self):
        for rec in self:
            rec.state = 'draft'
            rec.result_gpa = 0.0
            rec.result_percentage = 0.0
            rec.result_grade_letter = False
            rec.result_status = False
