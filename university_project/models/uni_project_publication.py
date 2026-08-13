# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class UniProjectPublication(models.Model):
    """Project Publication — a research publication produced as part of a
    graduation project.

    Uses Odoo *class inheritance with a new model name*:
        ``_name = 'uni.project.publication'``
        ``_inherit = 'uni.research.publication'``

    All fields/methods from ``uni.research.publication`` (title, code,
    faculty_id, co_authors, publication_type, journal_id, conference_id,
    publication_date, publisher, doi, isbn, issn, volume, issue, pages,
    abstract, keywords, citation_count, is_peer_reviewed, is_indexed,
    indexing_databases, impact_factor, file, filename, url, state, notes,
    active, …) are inherited. The ``project_id`` field is overridden to
    reference ``uni.project`` instead of ``uni.research.project``, and
    project-specific fields (publication_role, is_published,
    publication_venue, team_id) are added.

    The ``create`` method is overridden to use the ``uni.project.publication``
    sequence (prefix ``PPB/%(year)s/``) instead of the inherited
    ``uni.research.publication`` sequence.
    """
    _name = 'uni.project.publication'
    _inherit = 'uni.research.publication'
    _description = 'Project Publication'

    # Inherited fields from uni.research.publication:
    # - title, faculty_id, co_authors, publication_type, journal_id,
    #   conference_id, publication_date, publisher, doi, isbn, issn,
    #   volume, issue, pages, abstract, keywords, citation_count,
    #   is_peer_reviewed, is_indexed, indexing_databases, impact_factor,
    #   file, filename, url, state, notes, active

    # Project-specific fields
    project_id = fields.Many2one(
        'uni.project', string='Source Project', required=True,
        ondelete='cascade', tracking=True, index=True)

    publication_role = fields.Selection([
        ('main_output', 'Main Project Output'),
        ('derivative', 'Derivative Work'),
        ('related', 'Related Publication'),
        ('preliminary', 'Preliminary Results'),
    ], string='Publication Role', default='main_output',
        required=True, tracking=True)

    is_published = fields.Boolean(
        string='Officially Published', default=False, tracking=True)
    publication_venue = fields.Char(
        string='Publication Venue', tracking=True,
        help='Journal name, conference, or repository where published.')

    team_id = fields.Many2one(
        'uni.project.team', string='Authoring Team',
        ondelete='set null', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.project.publication') or _('New')
        return super().create(vals_list)
