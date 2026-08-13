# -*- coding: utf-8 -*-
from odoo import api, fields, models


class UniAcademicTermType(models.Model):
    """نوع النظام الدراسي (فصلي، ثلاثي، سنوي...)."""
    _name = 'uni.academic.term.type'
    _description = 'Academic Term Type'
    _order = 'sequence, name'

    name = fields.Char(string='Type Name', required=True, translate=True)
    code = fields.Char(string='Code', required=True, copy=False, index=True)
    sequence = fields.Integer(string='Sequence', default=10)
    terms_per_year = fields.Integer(string='Terms per Year', default=2,
                                    help='Number of terms in one academic year.')
    weeks_per_term = fields.Integer(string='Weeks per Term', default=16)
    description = fields.Text(string='Description')
    term_ids = fields.One2many('uni.academic.term', 'term_type_id', string='Terms')
    term_count = fields.Integer(compute='_compute_term_count', string='Terms')

    _sql_constraints = [
        ('unique_term_type_code', 'unique(code)', 'Term type code must be unique!'),
    ]

    @api.depends('term_ids')
    def _compute_term_count(self):
        for rec in self:
            rec.term_count = len(rec.term_ids)
