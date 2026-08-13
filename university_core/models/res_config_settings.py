# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    """الإعدادات المرنة للنظام الجامعي (مدمجة من uni_config)."""
    _inherit = 'res.config.settings'

    default_university_id = fields.Many2one(
        'uni.university', string='Default University',
        config_parameter='university_core.default_university_id',
        default_model='uni.person',
    )
    default_term_type_id = fields.Many2one(
        'uni.academic.term.type', string='Default Term Type',
        config_parameter='university_core.default_term_type_id',
    )
    module_university_grading = fields.Boolean(string='Grading System', default=True)
    module_university_curriculum = fields.Boolean(string='Curriculum Management', default=True)
    module_university_faculty = fields.Boolean(string='Faculty Management', default=True)
    module_university_student = fields.Boolean(string='Student Management', default=True)
    module_university_timetable = fields.Boolean(string='Timetable Management', default=True)
    group_university_multi_branch = fields.Boolean(
        string='Multi-Branch Management',
        implied_group='university_core.group_university_multi_branch',
    )
    university_code_prefix = fields.Char(
        string='University Code Prefix',
        config_parameter='university_core.code_prefix',
        default='UNI',
    )
    student_code_prefix = fields.Char(
        string='Student Code Prefix',
        config_parameter='university_core.student_code_prefix',
        default='STU',
    )
    faculty_code_prefix = fields.Char(
        string='Faculty Code Prefix',
        config_parameter='university_core.faculty_code_prefix',
        default='FAC',
    )
    auto_generate_codes = fields.Boolean(
        string='Auto Generate Codes',
        config_parameter='university_core.auto_generate_codes',
        default=True,
    )
