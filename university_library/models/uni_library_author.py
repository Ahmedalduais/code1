# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniLibraryAuthor(models.Model):
    """المؤلف — يصف مؤلف كتاب أو وثيقة في المكتبة الجامعية.

    يُستخدم لتسجيل البيانات الأساسية للمؤلف (الاسم، الكود، تواريخ
    الميلاد والوفاة، الجنسية، السيرة الذاتية) كما يربط المؤلف بكتبه
    عبر علاقة Many2many مع ``uni.library.book``.

    يوفّر النموذج:
        * كوداً فريداً لكل مؤلف يُستخدم في البحث والمراجع
        * حساب عدد الكتب المرتبطة بالمؤلف تلقائياً
        * تحقّقاً يمنع إدخال وفاة قبل الميلاد
        * صفحة ويب اختيارية للمؤلف
    """
    _name = 'uni.library.author'
    _description = 'Library Author'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'name'

    name = fields.Char(
        string='Author Name', required=True, tracking=True, translate=True,
        help='Full name of the author as it should appear in catalogs.')
    code = fields.Char(
        string='Code', copy=False, tracking=True, index=True,
        help='Short unique code identifying the author (e.g. AUTH-001).')
    birth_date = fields.Date(
        string='Birth Date', tracking=True,
        help='Date of birth of the author.')
    death_date = fields.Date(
        string='Death Date', tracking=True,
        help='Date of death of the author (leave blank if still living).')
    nationality_id = fields.Many2one(
        'res.country', string='Nationality',
        help='Country of nationality of the author.')
    biography = fields.Text(
        string='Biography', translate=True,
        help='Short biographical note about the author.')
    website = fields.Char(
        string='Website',
        help='Personal or official website of the author.')
    book_ids = fields.Many2many(
        'uni.library.book', 'uni_library_author_book_rel',
        'author_id', 'book_id',
        string='Books',
        help='Books authored or co-authored by this person.')
    book_count = fields.Integer(
        string='Book Count', compute='_compute_book_count', store=True,
        help='Total number of books linked to this author.')
    active = fields.Boolean(default=True, tracking=True)

    _sql_constraints = [
        ('unique_author_code', 'unique(code)',
         'Author code must be unique!'),
    ]

    @api.depends('book_ids')
    def _compute_book_count(self):
        """Count books linked to each author."""
        for rec in self:
            rec.book_count = len(rec.book_ids)

    @api.constrains('birth_date', 'death_date')
    def _check_dates(self):
        """Death date must be after birth date if both are set."""
        for rec in self:
            if rec.birth_date and rec.death_date \
                    and rec.death_date < rec.birth_date:
                raise ValidationError(_(
                    "Death date (%(death)s) cannot be before birth date "
                    "(%(birth)s) for author %(author)s.") % {
                    'death': rec.death_date,
                    'birth': rec.birth_date,
                    'author': rec.display_name,
                })

    def _compute_display_name(self):
        """Append code if available for clarity in selections."""
        for rec in self:
            if rec.code:
                rec.display_name = _('%(name)s [%(code)s]') % {
                    'name': rec.name, 'code': rec.code}
            else:
                rec.display_name = rec.name

    def action_open_books(self):
        """Open the book list filtered by this author."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Books by %s') % self.display_name,
            'res_model': 'uni.library.book',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.book_ids.ids)],
            'context': {'default_author_ids': [(6, 0, self.ids)]},
        }
