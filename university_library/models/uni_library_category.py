# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniLibraryCategory(models.Model):
    """تصنيف المكتبة — يصف هرمية تصنيفات الكتب.

    يدعم النموذج هرمية غير محدودة من التصنيفات عبر ``parent_id`` /
    ``child_ids`` كما يدعم أنظمة تصنيف متعددة (ديوي العشري،
    كونجرس، مخصص) مع كود تصنيف لكل فئة.

    يوفّر النموذج:
        * هرمية تصنيفات مع منع التكرار الدائري
        * نظام تصنيف موحّد لكل فئة (dewey/library_of_congress/custom)
        * كود تصنيف اختياري يُستخدم في الفهرسة
    """
    _name = 'uni.library.category'
    _description = 'Library Category'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'sequence, name'
    _parent_store = True

    name = fields.Char(
        string='Category Name', required=True, tracking=True, translate=True,
        help='Name of the category as it appears in catalogs.')
    code = fields.Char(
        string='Code', required=True, copy=False, tracking=True, index=True,
        help='Short unique code identifying the category (e.g. CS, MATH).')
    parent_id = fields.Many2one(
        'uni.library.category', string='Parent Category',
        ondelete='restrict', index=True,
        help='Parent category for hierarchical classification.')
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many(
        'uni.library.category', 'parent_id', string='Sub-Categories',
        help='Direct children categories of this category.')
    description = fields.Text(
        string='Description', translate=True,
        help='Short description of the category scope.')
    classification_system = fields.Selection([
        ('dewey_decimal', 'Dewey Decimal'),
        ('library_of_congress', 'Library of Congress'),
        ('custom', 'Custom'),
    ], string='Classification System', default='custom', required=True,
        tracking=True, index=True,
        help='Standard classification system used for this category.')
    classification_code = fields.Char(
        string='Classification Code',
        help='Code under the chosen classification system '
             '(e.g. 004.21 for Dewey, QA76.5 for Library of Congress).')
    sequence = fields.Integer(
        string='Sequence', default=10,
        help='Used to order categories in lists.')
    active = fields.Boolean(default=True, tracking=True)
    book_count = fields.Integer(
        string='Book Count', compute='_compute_book_count', store=True,
        help='Number of books directly assigned to this category.')

    _sql_constraints = [
        ('unique_category_code', 'unique(code)',
         'Category code must be unique!'),
    ]

    def _compute_book_count(self):
        """Count books directly linked to each category."""
        # uni.library.book has category_id pointing back to this model;
        # we count books per category manually without declaring a
        # One2many on this side to keep the contract minimal.
        reads = self.env['uni.library.book'].read_group(
            [('category_id', 'in', self.ids)],
            ['category_id'], ['category_id'])
        mapped = {r['category_id'][0]: r['category_id_count']
                  for r in reads if r['category_id']}
        for rec in self:
            rec.book_count = mapped.get(rec.id, 0)

    @api.constrains('parent_id')
    def _check_category_recursion(self):
        """Prevent recursion in category hierarchy."""
        for rec in self:
            if not rec.parent_id:
                continue
            if rec.parent_id == rec:
                raise ValidationError(_(
                    "A category cannot be its own parent."))
            # Walk up the parent chain to detect cycles.
            current = rec.parent_id
            while current:
                if current == rec:
                    raise ValidationError(_(
                        "Circular reference detected in category "
                        "hierarchy for %s.") % rec.display_name)
                current = current.parent_id

    def _compute_display_name(self):
        """Show code alongside the name for clarity."""
        for rec in self:
            rec.display_name = _('%(name)s [%(code)s]') % {
                'name': rec.name, 'code': rec.code}

    def action_open_books(self):
        """Open books assigned to this category."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Books in %s') % self.display_name,
            'res_model': 'uni.library.book',
            'view_mode': 'list,form',
            'domain': [('category_id', '=', self.id)],
            'context': {'default_category_id': self.id},
        }

    def action_open_children(self):
        """Open sub-categories of this category."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sub-Categories of %s') % self.display_name,
            'res_model': 'uni.library.category',
            'view_mode': 'list,form',
            'domain': [('parent_id', '=', self.id)],
            'context': {'default_parent_id': self.id},
        }
