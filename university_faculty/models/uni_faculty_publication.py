# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniFacultyPublication(models.Model):
    """المنشور العلمي لعضو هيئة التدريس.

    يدعم تصنيف المنشورات حسب النوع (مجلة، مؤتمر، كتاب، فصل في كتاب)،
    مع تتبع معرّفات DOI/ISBN، عدد الاستشهادات، ومراجعة الأقران.
    """
    _name = 'uni.faculty.publication'
    _description = 'Faculty Publication'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'publication_date desc, title'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True,
                      default=lambda self: _('New'), index=True)
    faculty_id = fields.Many2one(
        'uni.faculty', string='Faculty', required=True,
        ondelete='cascade', tracking=True, index=True)
    university_id = fields.Many2one(
        related='faculty_id.university_id', store=True, string='University', index=True)
    title = fields.Char(string='Title', required=True, tracking=True, translate=True)
    publication_type = fields.Selection([
        ('journal', 'Journal Article'),
        ('conference', 'Conference Paper'),
        ('book', 'Book'),
        ('book_chapter', 'Book Chapter'),
    ], string='Publication Type', default='journal', tracking=True, index=True)
    publisher = fields.Char(string='Publisher', tracking=True)
    publication_date = fields.Date(string='Publication Date', tracking=True)
    doi = fields.Char(string='DOI', help='Digital Object Identifier (e.g. 10.1000/xyz123).')
    isbn = fields.Char(string='ISBN', help='International Standard Book Number.')
    abstract = fields.Text(string='Abstract')
    co_authors = fields.Text(string='Co-Authors',
                             help='One co-author per line, or comma-separated list.')
    attachment = fields.Binary(string='Attachment File', attachment=True)
    attachment_filename = fields.Char(string='Attachment Filename')
    is_peer_reviewed = fields.Boolean(string='Peer Reviewed', default=False, tracking=True)
    citation_count = fields.Integer(string='Citation Count', default=0, tracking=True)

    _sql_constraints = [
        ('unique_publication_ref', 'unique(name)',
         'Publication reference must be unique!'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.faculty.publication') or _('PUB-NEW')
        return super().create(vals_list)

    @api.constrains('citation_count')
    def _check_citation_count(self):
        for rec in self:
            if rec.citation_count < 0:
                raise ValidationError(_(
                    "Citation count cannot be negative for publication %s.")
                    % rec.display_name)

    @api.constrains('publication_type', 'doi')
    def _check_doi_for_article(self):
        """Journal articles and conference papers should carry a DOI when set."""
        for rec in self:
            if rec.publication_type in ('journal', 'conference') and rec.doi:
                # Basic structural check on DOI prefix (10.xxxx/...)
                if not rec.doi.startswith('10.'):
                    raise ValidationError(_(
                        "DOI for publication %s must start with '10.' (e.g. 10.1000/xyz123).")
                        % rec.display_name)

    def action_view_attachment(self):
        """Download the attachment file if present."""
        self.ensure_one()
        if not self.attachment:
            return False
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=uni.faculty.publication&id=%s&field=attachment'
                   '&filename_field=attachment_filename&download=true' % self.id,
            'target': 'self',
        }
