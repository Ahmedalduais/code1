# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniLibraryBook(models.Model):
    """الكتاب — يمثل نسخة كتاب في المكتبة الجامعية.

    يحتوي النموذج على كافة بيانات الكتاب الفهرسية (الاسم، ISBN، الناشر،
    الطبعة، اللغة، عدد الصفحات، نوع التجليد) بالإضافة إلى حالة النسخ
    المتاحة والمستعارة عبر علاقة One2many مع ``uni.library.borrow``.

    يوفّر النموذج:
        * حساب النسخ المتاحة والمستعارة تلقائياً من سجلات الاستعارة
        * دعم النسخ الإلكترونية (ملف + رابط رقمي)
        * حالة الكتاب (available/all_borrowed/lost/damaged/removed)
        * تتبع كامل عبر mail.thread
    """
    _name = 'uni.library.book'
    _description = 'Library Book'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'name'

    # ------------------------------------------------------------------
    # Identification
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Title', required=True, tracking=True, translate=True,
        help='Title of the book as it should appear in the catalog.')
    code = fields.Char(
        string='Code', copy=False, tracking=True, index=True,
        help='Unique internal code identifying the book (e.g. BK-0001).')
    isbn = fields.Char(
        string='ISBN', copy=False, tracking=True, index=True,
        help='International Standard Book Number (ISBN-10 or ISBN-13).')
    subtitle = fields.Char(
        string='Subtitle', translate=True,
        help='Optional subtitle of the book.')

    # ------------------------------------------------------------------
    # Authorship & Classification
    # ------------------------------------------------------------------
    author_ids = fields.Many2many(
        'uni.library.author', 'uni_library_author_book_rel',
        'book_id', 'author_id',
        string='Authors',
        help='Authors and co-authors of the book.')
    category_id = fields.Many2one(
        'uni.library.category', string='Category',
        ondelete='set null', tracking=True, index=True,
        help='Library classification category of the book.')

    # ------------------------------------------------------------------
    # Publication
    # ------------------------------------------------------------------
    publisher = fields.Char(
        string='Publisher', tracking=True,
        help='Name of the publishing house.')
    publication_date = fields.Date(
        string='Publication Date', tracking=True,
        help='Exact date the book was published.')
    publication_year = fields.Integer(
        string='Publication Year', tracking=True,
        help='Year of publication (4 digits, e.g. 2024).')
    edition = fields.Char(
        string='Edition', tracking=True,
        help='Edition label (e.g. "3rd Edition", "Revised").')
    language_id = fields.Many2one(
        'res.lang', string='Language',
        help='Primary language of the book content.')
    pages = fields.Integer(
        string='Pages',
        help='Total number of pages in the book.')
    binding_type = fields.Selection([
        ('hardcover', 'Hardcover'),
        ('paperback', 'Paperback'),
        ('ebook', 'E-Book'),
        ('audio', 'Audio Book'),
        ('other', 'Other'),
    ], string='Binding Type', default='paperback', tracking=True,
        help='Physical or digital format of the book.')

    # ------------------------------------------------------------------
    # Descriptive content
    # ------------------------------------------------------------------
    description = fields.Text(
        string='Description', translate=True,
        help='Long description of the book content.')
    summary = fields.Text(
        string='Summary', translate=True,
        help='Short summary used in catalogs and search results.')
    cover_image = fields.Image(
        string='Cover Image', max_width=1024, max_height=1024,
        help='Cover image of the book.')

    # ------------------------------------------------------------------
    # Digital assets
    # ------------------------------------------------------------------
    file = fields.Binary(
        string='Digital File', attachment=True,
        help='Electronic copy of the book (PDF, EPUB, etc.).')
    filename = fields.Char(
        string='Filename',
        help='Original filename of the attached digital copy.')
    digital_url = fields.Char(
        string='Digital URL',
        help='External URL to access the digital copy of the book.')
    is_digital = fields.Boolean(
        string='Is Digital', compute='_compute_is_digital', store=True,
        help='True if the book has a digital file or URL available.')

    # ------------------------------------------------------------------
    # Copies & Inventory
    # ------------------------------------------------------------------
    total_copies = fields.Integer(
        string='Total Copies', default=1, required=True, tracking=True,
        help='Total number of physical copies owned by the library.')
    available_copies = fields.Integer(
        string='Available Copies', compute='_compute_available',
        store=True, tracking=True,
        help='Number of copies currently available for borrowing.')
    borrowed_count = fields.Integer(
        string='Borrowed Count', compute='_compute_borrowed', store=True,
        help='Number of copies currently on loan.')
    reserved_count = fields.Integer(
        string='Reserved Count', default=0, tracking=True,
        help='Number of copies reserved for specific borrowers.')
    location = fields.Char(
        string='Shelf Location', tracking=True,
        help='Shelf location code (e.g. A-12-3) for physical retrieval.')
    acquisition_date = fields.Date(
        string='Acquisition Date', default=fields.Date.context_today,
        tracking=True,
        help='Date the book was acquired by the library.')
    acquisition_price = fields.Float(
        string='Acquisition Price', digits=(16, 2), default=0.0,
        tracking=True,
        help='Price paid to acquire the book.')
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
        help='Currency for the acquisition price.')
    is_reference_only = fields.Boolean(
        string='Reference Only', default=False, tracking=True,
        help='If checked, the book cannot be borrowed and is for '
             'in-library reference only.')
    tags = fields.Char(
        string='Tags',
        help='Comma-separated list of free-text tags for search.')

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------
    state = fields.Selection([
        ('available', 'Available'),
        ('all_borrowed', 'All Borrowed'),
        ('lost', 'Lost'),
        ('damaged', 'Damaged'),
        ('removed', 'Removed'),
    ], string='State', default='available', required=True,
        tracking=True, index=True, group_expand='_group_expand_states',
        help='Lifecycle state of the book record.')

    # ------------------------------------------------------------------
    # Relations
    # ------------------------------------------------------------------
    borrow_ids = fields.One2many(
        'uni.library.borrow', 'book_id', string='Borrow History',
        help='All borrow records linked to this book.')
    active = fields.Boolean(default=True, tracking=True)

    _sql_constraints = [
        ('unique_book_code', 'unique(code)',
         'Book code must be unique!'),
        ('check_total_copies_positive',
         'check(total_copies >= 0)',
         'Total copies cannot be negative!'),
        ('check_reserved_non_negative',
         'check(reserved_count >= 0)',
         'Reserved count cannot be negative!'),
        ('check_pages_positive',
         'check(pages >= 0)',
         'Pages cannot be negative!'),
    ]

    # ------------------------------------------------------------------
    # Computations
    # ------------------------------------------------------------------
    @api.depends('file', 'digital_url', 'binding_type')
    def _compute_is_digital(self):
        """A book is digital if it has a digital file, URL, or e-book binding."""
        for rec in self:
            rec.is_digital = bool(
                rec.file or rec.digital_url
                or rec.binding_type in ('ebook', 'audio'))

    @api.depends('total_copies', 'borrow_ids.state', 'borrow_ids.actual_return_date')
    def _compute_available(self):
        """Available = total - currently borrowed (state in borrowed/overdue)."""
        for rec in self:
            borrowed = rec.borrow_ids.filtered(
                lambda b: b.state in ('borrowed', 'overdue'))
            borrowed_count = len(borrowed)
            available = rec.total_copies - borrowed_count - rec.reserved_count
            rec.available_copies = max(available, 0)

    @api.depends('borrow_ids.state', 'borrow_ids.actual_return_date')
    def _compute_borrowed(self):
        """Count currently active borrows (state in borrowed/overdue)."""
        for rec in self:
            rec.borrowed_count = len(rec.borrow_ids.filtered(
                lambda b: b.state in ('borrowed', 'overdue')))

    # ------------------------------------------------------------------
    # Group expand for state
    # ------------------------------------------------------------------
    @api.model
    def _group_expand_states(self, states, domain, order):
        """Return all known state keys for grouping."""
        return [key for key, _label in self._fields['state'].selection]

    # ------------------------------------------------------------------
    # Workflows
    # ------------------------------------------------------------------
    def action_mark_lost(self):
        """Mark the book as lost."""
        for rec in self:
            rec.state = 'lost'
            rec.message_post(body=_("Book marked as LOST."))

    def action_mark_damaged(self):
        """Mark the book as damaged."""
        for rec in self:
            rec.state = 'damaged'
            rec.message_post(body=_("Book marked as DAMAGED."))

    def action_restore(self):
        """Restore the book to available state."""
        for rec in self:
            rec.state = 'available'
            rec.message_post(body=_("Book restored to AVAILABLE."))

    # ------------------------------------------------------------------
    # Smart buttons
    # ------------------------------------------------------------------
    def action_open_borrows(self):
        """Open the borrow history for this book."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Borrow History'),
            'res_model': 'uni.library.borrow',
            'view_mode': 'list,form',
            'domain': [('book_id', '=', self.id)],
            'context': {'default_book_id': self.id},
        }

    def action_open_authors(self):
        """Open authors linked to this book."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Authors'),
            'res_model': 'uni.library.author',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.author_ids.ids)],
        }

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('publication_year')
    def _check_publication_year(self):
        """Year must be a realistic 4-digit value."""
        for rec in self:
            if rec.publication_year and (
                    rec.publication_year < 1400
                    or rec.publication_year > 2100):
                raise ValidationError(_(
                    "Publication year %(year)d is not realistic for "
                    "book %(book)s.") % {
                    'year': rec.publication_year,
                    'book': rec.display_name,
                })

    @api.constrains('is_reference_only', 'borrow_ids')
    def _check_reference_only_not_borrowed(self):
        """Reference-only books cannot have active borrows."""
        for rec in self:
            if rec.is_reference_only:
                active = rec.borrow_ids.filtered(
                    lambda b: b.state in ('borrowed', 'overdue'))
                if active:
                    raise ValidationError(_(
                        "Reference-only book %(book)s cannot have active "
                        "borrows.") % {'book': rec.display_name})

    @api.onchange('total_copies', 'reserved_count')
    def _onchange_check_copies(self):
        """Warn via exception when reserved exceeds total (server-side check)."""
        if self.total_copies and self.reserved_count is not False:
            if self.reserved_count > self.total_copies:
                return {
                    'warning': {
                        'title': _('Warning'),
                        'message': _(
                            'Reserved count (%d) exceeds total copies (%d). '
                            'Available copies will be 0.') % (
                            self.reserved_count, self.total_copies),
                    }
                }
