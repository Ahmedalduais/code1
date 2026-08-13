# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniResearchJournal(models.Model):
    """المجلة العلمية — يخزّن بيانات المجلات التي تُنشر فيها المنشورات.

    يشمل بيانات الفهرسة (ISSN/eISSN)، معامل التأثير، قواعد البيانات
    المفهرسة (Scopus, ISI, PubMed...), وتيرة الإصدار، ودعم الوصول المفتوح.
    """
    _name = 'uni.research.journal'
    _description = 'Scientific Journal'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'name'

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Journal Name', required=True, translate=True, tracking=True, index=True,
        help='Full name of the scientific journal.')
    code = fields.Char(
        string='Code', copy=False, index=True, tracking=True,
        help='Optional short code identifying the journal (e.g. JCS-001).')

    # ------------------------------------------------------------------
    # Publisher / location
    # ------------------------------------------------------------------
    publisher = fields.Char(string='Publisher', tracking=True)
    country_id = fields.Many2one(
        'res.country', string='Country', ondelete='restrict', tracking=True)
    website = fields.Char(string='Website', tracking=True,
                          help='Official journal URL.')

    # ------------------------------------------------------------------
    # Identifiers & metrics
    # ------------------------------------------------------------------
    issn = fields.Char(
        string='ISSN', tracking=True,
        help='Print ISSN (8 digits, format XXXX-XXXX).')
    e_issn = fields.Char(
        string='e-ISSN', tracking=True,
        help='Electronic ISSN (8 digits, format XXXX-XXXX).')
    impact_factor = fields.Float(
        string='Impact Factor', digits=(6, 3), tracking=True,
        help='Latest known Journal Impact Factor (JIF).')

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------
    is_indexed = fields.Boolean(
        string='Indexed', default=False, tracking=True,
        help='True if the journal is indexed in recognised databases.')
    indexing_databases = fields.Char(
        string='Indexing Databases', tracking=True,
        help='Comma-separated list (e.g. Scopus, ISI, PubMed, DOAJ).')

    # ------------------------------------------------------------------
    # Scope & frequency
    # ------------------------------------------------------------------
    scope = fields.Text(string='Scope', translate=True,
                        help='Aims and scope of the journal.')
    publication_frequency = fields.Selection([
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('bi_annual', 'Bi-Annual'),
        ('annual', 'Annual'),
    ], string='Publication Frequency', tracking=True)
    open_access = fields.Boolean(
        string='Open Access', default=False, tracking=True,
        help='True if the journal provides open access to its content.')

    # ------------------------------------------------------------------
    # Relations
    # ------------------------------------------------------------------
    publication_ids = fields.One2many(
        'uni.research.publication', 'journal_id', string='Publications')
    publication_count = fields.Integer(
        compute='_compute_publication_count', string='Publications')

    _sql_constraints = [
        ('unique_journal_issn', 'unique(issn)',
         'ISSN must be unique across journals!'),
        ('unique_journal_e_issn', 'unique(e_issn)',
         'e-ISSN must be unique across journals!'),
        ('unique_journal_code', 'unique(code)',
         'Journal code must be unique!'),
    ]

    # ------------------------------------------------------------------
    # Computed
    # ------------------------------------------------------------------
    @api.depends('publication_ids')
    def _compute_publication_count(self):
        for rec in self:
            rec.publication_count = len(rec.publication_ids)

    # ------------------------------------------------------------------
    # Smart button
    # ------------------------------------------------------------------
    def action_view_publications(self):
        """Open the publications linked to this journal."""
        self.ensure_one()
        return {
            'name': _('Publications'),
            'type': 'ir.actions.act_window',
            'res_model': 'uni.research.publication',
            'view_mode': 'list,form',
            'domain': [('journal_id', '=', self.id)],
            'context': {'default_journal_id': self.id},
        }

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('impact_factor')
    def _check_impact_factor(self):
        for rec in self:
            if rec.impact_factor < 0:
                raise ValidationError(_(
                    "Impact factor cannot be negative for journal '%s'.")
                    % rec.display_name)

    @api.constrains('issn', 'e_issn')
    def _check_issn_format(self):
        """Validate ISSN format (XXXXXXXX or XXXX-XXXX)."""
        import re
        pattern = re.compile(r'^\d{4}-?\d{3}[\dXx]$')
        for rec in self:
            for value, label in ((rec.issn, 'ISSN'), (rec.e_issn, 'e-ISSN')):
                if value and not pattern.match(value):
                    raise ValidationError(_(
                        "%s '%s' for journal '%s' is not a valid ISSN "
                        "(expected format XXXX-XXXX or XXXXXXXX).")
                        % (label, value, rec.display_name))
