# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class UniProjectTheme(models.Model):
    """Project Theme / Knowledge Area — classifies graduation projects.

    Themes are hierarchical (parent/child) so a college can organize projects
    by broad area (e.g. ``Software Engineering``) and sub-area (e.g.
    ``Web Engineering``). Themes carry a color index for kanban / calendar
    visualization and a sequence for ordering in lists.
    """
    _name = 'uni.project.theme'
    _description = 'Project Theme'
    _order = 'sequence, name'

    name = fields.Char(string='Theme Name', required=True, translate=True, index=True)
    code = fields.Char(string='Code', required=True, copy=False, index=True)
    parent_id = fields.Many2one('uni.project.theme', string='Parent Theme',
                                ondelete='restrict', index=True)
    child_ids = fields.One2many('uni.project.theme', 'parent_id', string='Sub-Themes')
    sequence = fields.Integer(string='Sequence', default=10)
    description = fields.Text(string='Description')
    color = fields.Integer(string='Color Index', default=0)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_theme_code', 'unique(code)', 'Theme code must be unique!'),
    ]
