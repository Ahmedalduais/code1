# -*- coding: utf-8 -*-
from odoo import api, fields, models


class UniGradingEngine(models.AbstractModel):
    """محرك حساب الدرجات المجرد — يوفر المنطق الأساسي لحساب المعدلات."""
    _name = 'uni.grading.engine'
    _description = 'Grading Engine (Abstract)'

    @api.model
    def calculate_weighted_average(self, grade_lines):
        """حساب المتوسط المرجح لقائمة درجات.
        
        :param grade_lines: list of dicts with 'value' and 'weight' keys
        :return: weighted average as float
        """
        if not grade_lines:
            return 0.0
        total_weight = sum(line.get('weight', 0) for line in grade_lines)
        if total_weight <= 0:
            return 0.0
        weighted_sum = sum(
            line.get('value', 0) * line.get('weight', 0) for line in grade_lines
        )
        return weighted_sum / total_weight

    @api.model
    def calculate_gpa(self, course_grades, grading_system_id=False):
        """حساب المعدل التراكمي (GPA) لقائمة درجات مقررات.
        
        :param course_grades: list of dicts with 'gpa_value' and 'credit_hours' keys
        :param grading_system_id: optional grading system to use
        :return: GPA as float
        """
        if not course_grades:
            return 0.0
        total_credits = sum(c.get('credit_hours', 0) for c in course_grades)
        if total_credits <= 0:
            return 0.0
        weighted_points = sum(
            c.get('gpa_value', 0) * c.get('credit_hours', 0) for c in course_grades
        )
        return weighted_points / total_credits

    @api.model
    def calculate_cumulative_gpa(self, term_gpas):
        """حساب المعدل التراكمي عبر عدة فصول.
        
        :param term_gpas: list of dicts with 'gpa' and 'total_credits' keys
        :return: cumulative GPA as float
        """
        if not term_gpas:
            return 0.0
        total_credits = sum(t.get('total_credits', 0) for t in term_gpas)
        if total_credits <= 0:
            return 0.0
        weighted_gpa = sum(
            t.get('gpa', 0) * t.get('total_credits', 0) for t in term_gpas
        )
        return weighted_gpa / total_credits

    @api.model
    def convert_percentage_to_grade(self, percentage, grading_system_id):
        """تحويل نسبة إلى تقدير حرفي."""
        if not grading_system_id:
            return False
        system = self.env['uni.grading.system'].browse(grading_system_id)
        if not system.exists():
            return False
        return system.get_grade_letter_for_percentage(percentage)

    @api.model
    def determine_status(self, gpa, passing_gpa=2.0):
        """تحديد الحالة الأكاديمية بناءً على المعدل."""
        if gpa >= 3.5:
            return 'excellent'
        elif gpa >= 3.0:
            return 'very_good'
        elif gpa >= 2.5:
            return 'good'
        elif gpa >= 2.0:
            return 'acceptable'
        elif gpa >= 1.0:
            return 'probation'
        else:
            return 'dismissed'
