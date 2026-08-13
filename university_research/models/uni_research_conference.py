# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniResearchConference(models.Model):
    """المؤتمر العلمي — يخزّن بيانات المؤتمرات التي قد تُنشر فيها الأوراق.

    يشمل الموضوع، التواريخ المهمة (نداء الأوراق، التقديم، القبول)، الموقع،
    المنظّم، حالة الفهرسة، ودورة الحياة (announced/ongoing/completed/cancelled).
    """
    _name = 'uni.research.conference'
    _description = 'Scientific Conference'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'start_date desc, name'

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Conference Name', required=True, translate=True, tracking=True, index=True,
        help='Full name of the scientific conference.')
    code = fields.Char(
        string='Code', copy=False, index=True, tracking=True,
        help='Short identifier (e.g. IEEE-CONF-2024).')
    acronym = fields.Char(
        string='Acronym', tracking=True,
        help='Short acronym (e.g. ICML, CVPR, KDD).')
    theme = fields.Char(string='Theme', tracking=True, translate=True,
                        help='Main theme or topic of the conference edition.')

    # ------------------------------------------------------------------
    # Dates
    # ------------------------------------------------------------------
    start_date = fields.Date(string='Start Date', tracking=True)
    end_date = fields.Date(string='End Date', tracking=True)
    call_for_papers_deadline = fields.Date(
        string='Call for Papers Deadline', tracking=True)
    submission_deadline = fields.Date(
        string='Submission Deadline', tracking=True)
    acceptance_notification_date = fields.Date(
        string='Acceptance Notification Date', tracking=True)

    # ------------------------------------------------------------------
    # Location & organizer
    # ------------------------------------------------------------------
    location = fields.Char(string='Location', tracking=True,
                           help='City, venue, or hybrid/online.')
    country_id = fields.Many2one(
        'res.country', string='Country', ondelete='restrict', tracking=True)
    organizer = fields.Char(string='Organizer', tracking=True,
                            help='Organizing institution or society.')
    website = fields.Char(string='Website', tracking=True,
                          help='Official conference URL.')

    # ------------------------------------------------------------------
    # Indexing & description
    # ------------------------------------------------------------------
    is_indexed = fields.Boolean(
        string='Indexed', default=False, tracking=True,
        help='True if proceedings are indexed (e.g. in DBLP, Scopus).')
    indexing_databases = fields.Char(
        string='Indexing Databases', tracking=True,
        help='Comma-separated list (e.g. DBLP, Scopus, IEEE Xplore).')
    description = fields.Text(string='Description', translate=True)

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------
    state = fields.Selection([
        ('announced', 'Announced'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='State', default='announced', tracking=True, index=True,
        group_expand='_group_expand_states')

    # ------------------------------------------------------------------
    # Relations
    # ------------------------------------------------------------------
    publication_ids = fields.One2many(
        'uni.research.publication', 'conference_id', string='Publications')
    publication_count = fields.Integer(
        compute='_compute_publication_count', string='Publications')

    # ------------------------------------------------------------------
    # Group expand helper
    # ------------------------------------------------------------------
    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in self._fields['state'].selection]

    # ------------------------------------------------------------------
    # Computed
    # ------------------------------------------------------------------
    @api.depends('publication_ids')
    def _compute_publication_count(self):
        for rec in self:
            rec.publication_count = len(rec.publication_ids)

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_start(self):
        """Mark the conference as ongoing."""
        for rec in self:
            if rec.state != 'announced':
                raise ValidationError(_(
                    "Only announced conferences can be started (current: %(state)s).")
                    % {'state': rec.state})
            rec.state = 'ongoing'
            rec.message_post(body=_('Conference marked as ongoing.'))

    def action_complete(self):
        """Mark the conference as completed."""
        for rec in self:
            if rec.state != 'ongoing':
                raise ValidationError(_(
                    "Only ongoing conferences can be completed (current: %(state)s).")
                    % {'state': rec.state})
            rec.state = 'completed'
            rec.message_post(body=_('Conference marked as completed.'))

    def action_cancel(self):
        """Cancel the conference."""
        for rec in self:
            if rec.state == 'completed':
                raise ValidationError(_(
                    "Cannot cancel a completed conference ('%s').") % rec.display_name)
            rec.state = 'cancelled'
            rec.message_post(body=_('Conference cancelled.'))

    def action_reopen(self):
        """Reopen a cancelled conference back to announced."""
        for rec in self:
            if rec.state != 'cancelled':
                raise ValidationError(_(
                    "Only cancelled conferences can be reopened (current: %(state)s).")
                    % {'state': rec.state})
            rec.state = 'announced'
            rec.message_post(body=_('Conference reopened as announced.'))

    # ------------------------------------------------------------------
    # Smart button
    # ------------------------------------------------------------------
    def action_view_publications(self):
        """Open the publications linked to this conference."""
        self.ensure_one()
        return {
            'name': _('Publications'),
            'type': 'ir.actions.act_window',
            'res_model': 'uni.research.publication',
            'view_mode': 'list,form',
            'domain': [('conference_id', '=', self.id)],
            'context': {'default_conference_id': self.id},
        }

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for rec in self:
            if rec.start_date and rec.end_date and rec.end_date < rec.start_date:
                raise ValidationError(_(
                    "End date cannot be earlier than start date for conference '%s'.")
                    % rec.display_name)

    @api.constrains('submission_deadline', 'call_for_papers_deadline',
                    'acceptance_notification_date', 'start_date')
    def _check_milestone_dates(self):
        """Logical ordering: call for papers → submission → notification → start."""
        for rec in self:
            milestones = [
                ('Call for papers', rec.call_for_papers_deadline),
                ('Submission', rec.submission_deadline),
                ('Acceptance notification', rec.acceptance_notification_date),
                ('Conference start', rec.start_date),
            ]
            previous = None
            for label, value in milestones:
                if value and previous and previous[1] and value < previous[1]:
                    raise ValidationError(_(
                        "%(cur)s date (%(cur_d)s) cannot be earlier than "
                        "%(prev)s date (%(prev_d)s) for conference '%(conf)s'.")
                        % {'cur': label, 'cur_d': value,
                           'prev': previous[0], 'prev_d': previous[1],
                           'conf': rec.display_name})
                if value:
                    previous = (label, value)
