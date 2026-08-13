# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class UniLibraryDigital(models.Model):
    """المستودع الرقمي — وثيقة رقمية في المكتبة الجامعية.

    يخزّن النموذج الوثائق الرقمية الأكاديمية (أطروحات، رسائل، مقالات،
    أوراق بحثية، محاضرات) مع مستويات وصول قابلة للتحكم وعدّادات
    للتنزيل والعرض.

    يوفّر النموذج:
        * تصنيف الوثيقة (thesis/dissertation/journal_article/...)
        * ربط اختياري بالطالب/عضو هيئة التدريس/القسم
        * مستوى وصول (public/university_only/department_only/restricted)
        * DOI و URL خارجي اختياريان
        * سير حالة (draft → published → archived)
        * عدّادات تنزيل وعرض تُحدَّث عند كل عملية
    """
    _name = 'uni.library.digital'
    _description = 'Library Digital Repository'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'publication_date desc, id desc'

    # ------------------------------------------------------------------
    # Identification
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True,
        default='New', tracking=True, index=True,
        help='Unique sequence reference of the digital document.')
    code = fields.Char(
        string='Code', copy=False, tracking=True, index=True,
        help='Optional secondary code for manual lookups.')
    title = fields.Char(
        string='Title', required=True, tracking=True, translate=True,
        help='Title of the digital document.')

    # ------------------------------------------------------------------
    # Document type & authorship
    # ------------------------------------------------------------------
    document_type = fields.Selection([
        ('thesis', 'Thesis'),
        ('dissertation', 'Dissertation'),
        ('journal_article', 'Journal Article'),
        ('research_paper', 'Research Paper'),
        ('conference_paper', 'Conference Paper'),
        ('lecture_notes', 'Lecture Notes'),
        ('other', 'Other'),
    ], string='Document Type', default='other', required=True,
        tracking=True, index=True,
        help='Type of digital document.')
    author_ids = fields.Many2many(
        'uni.library.author', 'uni_library_digital_author_rel',
        'digital_id', 'author_id',
        string='Authors',
        help='Authors of the digital document.')
    student_name = fields.Char(
        string='Student Author Name', tracking=True, index=True,
        help='Name of the student who authored the document '
             '(free text — typically the thesis/dissertation author).')
    faculty_name = fields.Char(
        string='Faculty Author Name', tracking=True, index=True,
        help='Name of the faculty member who authored or supervised the '
             'document (free text).')
    department_id = fields.Many2one(
        'uni.department', string='Department',
        ondelete='restrict', index=True,
        help='Department the document belongs to.')

    # ------------------------------------------------------------------
    # Content & metadata
    # ------------------------------------------------------------------
    publication_date = fields.Date(
        string='Publication Date', tracking=True,
        help='Date the document was published or submitted.')
    abstract = fields.Text(
        string='Abstract', translate=True,
        help='Short abstract of the document.')
    keywords = fields.Char(
        string='Keywords',
        help='Comma-separated keywords for search and discovery.')
    file = fields.Binary(
        string='File', required=True, attachment=True,
        help='Digital file of the document (PDF, DOCX, etc.).')
    filename = fields.Char(
        string='Filename',
        help='Original filename of the attached document.')
    file_size = fields.Integer(
        string='File Size (bytes)', compute='_compute_file_size', store=True,
        help='Size of the attached file in bytes.')
    file_format = fields.Char(
        string='File Format',
        help='Format of the file (e.g. PDF, DOCX, EPUB).')
    download_count = fields.Integer(
        string='Downloads', default=0, tracking=True,
        help='Number of times the document was downloaded.')
    view_count = fields.Integer(
        string='Views', default=0, tracking=True,
        help='Number of times the document was viewed.')
    access_level = fields.Selection([
        ('public', 'Public'),
        ('university_only', 'University Only'),
        ('department_only', 'Department Only'),
        ('restricted', 'Restricted'),
    ], string='Access Level', default='university_only', required=True,
        tracking=True, index=True,
        help='Who can access this document.')
    doi = fields.Char(
        string='DOI', copy=False, tracking=True, index=True,
        help='Digital Object Identifier of the document (e.g. 10.xxxx/...).')
    url = fields.Char(
        string='External URL',
        help='External URL to access the document if hosted elsewhere.')

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------
    state = fields.Selection([
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ], string='State', default='draft', required=True,
        tracking=True, index=True, group_expand='_group_expand_states',
        help='Lifecycle state of the digital document.')
    active = fields.Boolean(default=True, tracking=True)

    _sql_constraints = [
        ('unique_digital_name', 'unique(name)',
         'Digital document reference must be unique!'),
    ]

    # ------------------------------------------------------------------
    # Create — auto sequence
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        """Auto-generate the sequence reference for each new document."""
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.library.digital') or 'New'
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends('file')
    def _compute_file_size(self):
        """Compute file size from base64-encoded content.

        Odoo stores binary fields as base64-encoded strings; the decoded
        byte size is roughly ``len(b64) * 3 / 4``.
        """
        for rec in self:
            if rec.file:
                rec.file_size = int(len(rec.file) * 0.75)
            else:
                rec.file_size = 0

    # ------------------------------------------------------------------
    # Group expand
    # ------------------------------------------------------------------
    @api.model
    def _group_expand_states(self, states, domain, order):
        """Return all known state keys for grouping."""
        return [key for key, _label in self._fields['state'].selection]

    # ------------------------------------------------------------------
    # Workflows
    # ------------------------------------------------------------------
    def action_publish(self):
        """Publish the document — make it available to users."""
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_(
                    "Document %(name)s can only be published from draft "
                    "state (current: %(state)s).") % {
                    'name': rec.name,
                    'state': rec.state,
                })
            if not rec.file:
                raise ValidationError(_(
                    "Document %(name)s must have a file before publishing."
                ) % {'name': rec.name})
            rec.state = 'published'
            rec.message_post(body=_("Document published."))

    def action_archive(self):
        """Archive the document — hide it from active listings."""
        for rec in self:
            rec.state = 'archived'
            rec.message_post(body=_("Document archived."))

    def action_draft(self):
        """Reset the document to draft state."""
        for rec in self:
            rec.state = 'draft'
            rec.message_post(body=_("Document reset to draft."))

    def action_download(self):
        """Increment download counter and trigger file download."""
        for rec in self:
            rec.download_count += 1
            rec.message_post(body=_("Document downloaded."))
        # Return a download action for the first record in the set
        self.ensure_one()
        if not self.file:
            raise UserError(_("No file available for download."))
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=uni.library.digital&id=%d&field=file'
                   '&filename_field=filename&download=true' % self.id,
            'target': 'self',
        }

    def action_view(self):
        """Increment view counter."""
        for rec in self:
            rec.view_count += 1

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('doi')
    def _check_doi_format(self):
        """DOI should start with '10.' if provided."""
        for rec in self:
            if rec.doi and not rec.doi.startswith('10.'):
                raise ValidationError(_(
                    "DOI %(doi)s for document %(name)s must start with "
                    "'10.'.") % {
                    'doi': rec.doi,
                    'name': rec.display_name,
                })

    @api.constrains('state', 'file')
    def _check_published_has_file(self):
        """Published documents must have a file."""
        for rec in self:
            if rec.state == 'published' and not rec.file:
                raise ValidationError(_(
                    "Published document %(name)s must have a file.") % {
                    'name': rec.display_name,
                })
