# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniResearchPublication(models.Model):
    """المنشور العلمي — يمثّل ورقة/كتاب/براءة اختراع ناتجة عن البحث.

    يدعم تصنيفاً واسعاً للمنشورات (مقال مجلة، ورقة مؤتمر، كتاب، فصل،
    رسالة، تقرير، براءة اختراع) مع تتبّع معرّفات DOI/ISBN/ISSN،
    معامل التأثير، عدد الاستشهادات، الفهرسة في قواعد البيانات العلمية،
    وملف PDF المرفق.

    سير العمل:
        ``draft`` → ``submitted`` → ``accepted`` → ``published``
                                       ↘ ``rejected``
    """
    _name = 'uni.research.publication'
    _description = 'Research Publication'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'publication_date desc, name'

    # ------------------------------------------------------------------
    # Identity & sequence
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True, index=True,
        default=lambda self: _('New'), tracking=True)
    code = fields.Char(
        string='Code', copy=False, index=True, tracking=True,
        help='Optional publication code (e.g. PUB-2024-001).')
    title = fields.Char(
        string='Title', required=True, translate=True, tracking=True,
        help='Full title of the publication.')

    # ------------------------------------------------------------------
    # Relations
    # ------------------------------------------------------------------
    project_id = fields.Many2one(
        'uni.research.project', string='Research Project',
        ondelete='restrict', tracking=True, index=True,
        help='Research project this publication originated from (optional).')
    faculty_id = fields.Many2one(
        'uni.faculty', string='Lead Author (Faculty)', required=True,
        ondelete='restrict', tracking=True, index=True)
    university_id = fields.Many2one(
        related='faculty_id.university_id', store=True, readonly=True,
        string='University', index=True)

    co_authors = fields.Text(
        string='Co-Authors',
        help='One co-author per line, or comma-separated list '
             '(names outside the faculty records).')

    # ------------------------------------------------------------------
    # Publication type
    # ------------------------------------------------------------------
    publication_type = fields.Selection([
        ('journal_article', 'Journal Article'),
        ('conference_paper', 'Conference Paper'),
        ('book', 'Book'),
        ('book_chapter', 'Book Chapter'),
        ('thesis', 'Thesis'),
        ('report', 'Technical Report'),
        ('patent', 'Patent'),
    ], string='Publication Type', default='journal_article', tracking=True, index=True)

    # ------------------------------------------------------------------
    # Venue (journal / conference)
    # ------------------------------------------------------------------
    journal_id = fields.Many2one(
        'uni.research.journal', string='Journal',
        ondelete='restrict', tracking=True, index=True)
    conference_id = fields.Many2one(
        'uni.research.conference', string='Conference',
        ondelete='restrict', tracking=True, index=True)

    # ------------------------------------------------------------------
    # Dates & publisher
    # ------------------------------------------------------------------
    publication_date = fields.Date(string='Publication Date', tracking=True)
    publisher = fields.Char(string='Publisher', tracking=True)

    # ------------------------------------------------------------------
    # Identifiers
    # ------------------------------------------------------------------
    doi = fields.Char(
        string='DOI', tracking=True,
        help='Digital Object Identifier (e.g. 10.1000/xyz123).')
    isbn = fields.Char(
        string='ISBN', tracking=True,
        help='International Standard Book Number.')
    issn = fields.Char(
        string='ISSN', tracking=True,
        help='ISSN of the publishing journal (if applicable).')

    # ------------------------------------------------------------------
    # Bibliographic details
    # ------------------------------------------------------------------
    volume = fields.Char(string='Volume', tracking=True)
    issue = fields.Char(string='Issue', tracking=True)
    pages = fields.Char(string='Pages', tracking=True,
                        help='Page range, e.g. 12-37.')
    abstract = fields.Text(string='Abstract', translate=True)
    keywords = fields.Char(string='Keywords', tracking=True,
                           help='Comma-separated keywords.')

    # ------------------------------------------------------------------
    # Metrics & indexing
    # ------------------------------------------------------------------
    citation_count = fields.Integer(
        string='Citation Count', default=0, tracking=True,
        help='Number of citations received so far.')
    is_peer_reviewed = fields.Boolean(
        string='Peer Reviewed', default=True, tracking=True)
    is_indexed = fields.Boolean(
        string='Indexed', default=False, tracking=True,
        help='True if the publication is indexed in recognised databases.')
    indexing_databases = fields.Char(
        string='Indexing Databases', tracking=True,
        help='Comma-separated list (e.g. Scopus, ISI, PubMed).')
    impact_factor = fields.Float(
        string='Impact Factor', digits=(6, 3), tracking=True,
        help='Journal impact factor at time of publication.')

    # ------------------------------------------------------------------
    # Attachment & URL
    # ------------------------------------------------------------------
    file = fields.Binary(string='File', attachment=True)
    filename = fields.Char(string='Filename')
    url = fields.Char(string='URL', tracking=True,
                      help='Public URL of the publication (if open access).')

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('accepted', 'Accepted'),
        ('published', 'Published'),
        ('rejected', 'Rejected'),
    ], string='State', default='draft', tracking=True, index=True,
        group_expand='_group_expand_states')
    notes = fields.Text(string='Notes')

    # ------------------------------------------------------------------
    # Computed helpers
    # ------------------------------------------------------------------
    publication_year = fields.Integer(
        compute='_compute_publication_year', string='Year', store=True,
        help='Year of publication, extracted from the publication date.')

    _sql_constraints = [
        ('unique_publication_name', 'unique(name)',
         'Publication reference must be unique!'),
        ('check_citation_count_positive', 'check(citation_count >= 0)',
         'Citation count cannot be negative!'),
    ]

    # ------------------------------------------------------------------
    # Group expand helper
    # ------------------------------------------------------------------
    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in self._fields['state'].selection]

    # ------------------------------------------------------------------
    # Sequence on create
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.research.publication') or _('RPB-NEW')
            # Pre-fill impact factor from the journal when not provided.
            if not vals.get('impact_factor') and vals.get('journal_id'):
                journal = self.env['uni.research.journal'].browse(vals['journal_id'])
                if journal.impact_factor:
                    vals['impact_factor'] = journal.impact_factor
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Onchange — fill impact factor & issn from journal
    # ------------------------------------------------------------------
    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        if self.journal_id:
            if not self.issn and self.journal_id.issn:
                self.issn = self.journal_id.issn
            if not self.impact_factor and self.journal_id.impact_factor:
                self.impact_factor = self.journal_id.impact_factor
            if not self.publisher and self.journal_id.publisher:
                self.publisher = self.journal_id.publisher

    @api.onchange('publication_type')
    def _onchange_publication_type(self):
        """Clear irrelevant venue fields based on publication type.

        - journal_article keeps journal_id and clears conference_id
        - conference_paper keeps conference_id and clears journal_id
        - any other type clears both venues
        """
        ptype = self.publication_type
        if ptype == 'journal_article':
            self.conference_id = False
        elif ptype == 'conference_paper':
            self.journal_id = False
        else:
            self.journal_id = False
            self.conference_id = False

    # ------------------------------------------------------------------
    # Computed
    # ------------------------------------------------------------------
    @api.depends('publication_date')
    def _compute_publication_year(self):
        for rec in self:
            rec.publication_year = rec.publication_date.year if rec.publication_date else 0

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_submit(self):
        """Submit the publication to a journal / conference."""
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError(_(
                    "Only draft publications can be submitted (current: %(state)s).")
                    % {'state': rec.state})
            if rec.publication_type == 'journal_article' and not rec.journal_id:
                raise ValidationError(_(
                    "Journal article '%s' must reference a journal before submission.")
                    % rec.display_name)
            if rec.publication_type == 'conference_paper' and not rec.conference_id:
                raise ValidationError(_(
                    "Conference paper '%s' must reference a conference before submission.")
                    % rec.display_name)
            rec.state = 'submitted'
            rec.message_post(body=_('Publication submitted.'))

    def action_accept(self):
        """Mark the submitted publication as accepted."""
        for rec in self:
            if rec.state != 'submitted':
                raise ValidationError(_(
                    "Only submitted publications can be accepted (current: %(state)s).")
                    % {'state': rec.state})
            rec.state = 'accepted'
            rec.message_post(body=_('Publication accepted.'))

    def action_publish(self):
        """Mark the accepted publication as published."""
        for rec in self:
            if rec.state != 'accepted':
                raise ValidationError(_(
                    "Only accepted publications can be published (current: %(state)s).")
                    % {'state': rec.state})
            if not rec.publication_date:
                rec.publication_date = fields.Date.context_today(rec)
            rec.state = 'published'
            rec.message_post(body=_('Publication published on %s.') % rec.publication_date)

    def action_reject(self):
        """Reject the submitted publication."""
        for rec in self:
            if rec.state != 'submitted':
                raise ValidationError(_(
                    "Only submitted publications can be rejected (current: %(state)s).")
                    % {'state': rec.state})
            rec.state = 'rejected'
            rec.message_post(body=_('Publication rejected.'))

    def action_draft(self):
        """Reset a rejected publication back to draft."""
        for rec in self:
            if rec.state != 'rejected':
                raise ValidationError(_(
                    "Only rejected publications can be reset to draft (current: %(state)s).")
                    % {'state': rec.state})
            rec.state = 'draft'
            rec.message_post(body=_('Publication reset to draft.'))

    # ------------------------------------------------------------------
    # Smart button — download attached file
    # ------------------------------------------------------------------
    def action_download_file(self):
        """Download the attached publication file (PDF, etc.)."""
        self.ensure_one()
        if not self.file:
            return False
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=uni.research.publication&id=%s&field=file'
                   '&filename_field=filename&download=true' % self.id,
            'target': 'self',
        }

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('citation_count')
    def _check_citation_count(self):
        for rec in self:
            if rec.citation_count < 0:
                raise ValidationError(_(
                    "Citation count cannot be negative for publication '%s'.")
                    % rec.display_name)

    @api.constrains('impact_factor')
    def _check_impact_factor(self):
        for rec in self:
            if rec.impact_factor < 0:
                raise ValidationError(_(
                    "Impact factor cannot be negative for publication '%s'.")
                    % rec.display_name)

    @api.constrains('publication_type', 'doi')
    def _check_doi_format(self):
        """If a DOI is set, validate its structural prefix."""
        for rec in self:
            if rec.doi and not rec.doi.startswith('10.'):
                raise ValidationError(_(
                    "DOI for publication '%s' must start with '10.' "
                    "(e.g. 10.1000/xyz123).") % rec.display_name)

    @api.constrains('publication_type', 'journal_id', 'conference_id')
    def _check_venue_consistency(self):
        """Validate that the venue matches the publication type."""
        for rec in self:
            if rec.publication_type == 'journal_article' and \
                    rec.conference_id and not rec.journal_id:
                raise ValidationError(_(
                    "Journal article '%s' should reference a journal, "
                    "not a conference.") % rec.display_name)
            if rec.publication_type == 'conference_paper' and \
                    rec.journal_id and not rec.conference_id:
                raise ValidationError(_(
                    "Conference paper '%s' should reference a conference, "
                    "not a journal.") % rec.display_name)
