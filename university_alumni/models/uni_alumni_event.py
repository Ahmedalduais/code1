# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniAlumniEvent(models.Model):
    """فعالية الخريجين — فعالية موجّهة لشبكة الخريجين.

    تشمل أنواع الفعاليات: لم الشمل، التواصل، معارف الوظائف، جمع
    التبرعات، الفعاليات الاجتماعية، المؤتمرات، الورش. لكل فعالية
    دورة حياة كاملة تبدأ بالمسودة ثم الإعلان ثم فتح التسجيل ثم
    الجلسة الجارية ثم الإكمال أو الإلغاء.
    """
    _name = 'uni.alumni.event'
    _description = 'Alumni Event'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_date desc'

    # ------------------------------------------------------------------
    # Identity & reference
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Reference', copy=False, readonly=True, index=True,
        default=lambda self: _('New'), tracking=True,
        help='Auto-generated event reference (AEV/...).')
    code = fields.Char(
        string='Code', copy=False, index=True, tracking=True,
        help='Optional manual code identifying the event.')

    event_type = fields.Selection([
        ('reunion', 'Reunion'),
        ('networking', 'Networking'),
        ('career_fair', 'Career Fair'),
        ('fundraising', 'Fundraising'),
        ('social', 'Social'),
        ('conference', 'Conference'),
        ('workshop', 'Workshop'),
        ('other', 'Other'),
    ], string='Event Type', default='networking', tracking=True, index=True)

    title = fields.Char(
        string='Title', required=True, tracking=True, index=True,
        help='Public-facing title of the event.')
    description = fields.Text(string='Description')

    # ------------------------------------------------------------------
    # Schedule & location
    # ------------------------------------------------------------------
    start_date = fields.Datetime(
        string='Start Date', required=True, tracking=True)
    end_date = fields.Datetime(
        string='End Date', required=True, tracking=True)
    location = fields.Char(string='Location', tracking=True)
    is_online = fields.Boolean(
        string='Online', default=False, tracking=True,
        help='Check if the event will be held online.')
    meeting_url = fields.Char(
        string='Meeting URL', tracking=True,
        help='URL of the online meeting (Zoom, Teams, Google Meet...).')

    # ------------------------------------------------------------------
    # Capacity & registration
    # ------------------------------------------------------------------
    max_attendees = fields.Integer(
        string='Max Attendees', default=0,
        help='Maximum number of attendees (0 = unlimited).')
    registered_count = fields.Integer(
        string='Registered', compute='_compute_registered', store=True,
        help='Number of alumni members registered for the event.')
    attended_count = fields.Integer(
        string='Attended', compute='_compute_attended', store=True,
        help='Number of alumni members considered to have attended '
             '(all registered members when the event is completed).')
    registration_deadline = fields.Datetime(
        string='Registration Deadline', tracking=True,
        help='After this date/time, no more registrations are accepted.')

    # ------------------------------------------------------------------
    # Fees
    # ------------------------------------------------------------------
    fee = fields.Monetary(
        string='Fee', currency_field='currency_id', default=0.0,
        tracking=True, help='Registration fee (0 = free event).')
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
        tracking=True)

    # ------------------------------------------------------------------
    # Organizer & members
    # ------------------------------------------------------------------
    organizer_id = fields.Many2one(
        'res.users', string='Organizer', tracking=True, index=True,
        default=lambda self: self.env.user,
        help='User responsible for organizing the event.')
    member_ids = fields.Many2many(
        'uni.alumni.member', 'uni_alumni_event_member_rel',
        'event_id', 'member_id', string='Registered Members')

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------
    state = fields.Selection([
        ('draft', 'Draft'),
        ('announced', 'Announced'),
        ('registration_open', 'Registration Open'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='State', default='draft', tracking=True, index=True,
        group_expand='_group_expand_states')

    # ------------------------------------------------------------------
    # Misc
    # ------------------------------------------------------------------
    image = fields.Image(string='Image', max_width=1024, max_height=1024)
    notes = fields.Text(string='Notes')
    active = fields.Boolean(string='Active', default=True, tracking=True)
    color = fields.Integer(string='Color Index')

    _sql_constraints = [
        ('unique_event_code', 'unique(code)',
         'Event code must be unique!'),
    ]

    # ------------------------------------------------------------------
    # Group expansion
    # ------------------------------------------------------------------
    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in self._fields['state'].selection]

    # ------------------------------------------------------------------
    # Computed
    # ------------------------------------------------------------------
    @api.depends('member_ids')
    def _compute_registered(self):
        """Count registered alumni members."""
        for rec in self:
            rec.registered_count = len(rec.member_ids)

    @api.depends('member_ids', 'state')
    def _compute_attended(self):
        """Compute attended count.

        When the event is marked as ``completed``, all registered members
        are considered to have attended. This default can be refined later
        by an attendance-tracking extension overriding this method.
        """
        for rec in self:
            rec.attended_count = (
                len(rec.member_ids) if rec.state == 'completed' else 0)

    # ------------------------------------------------------------------
    # Create — auto-sequence the event reference
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.alumni.event') or _('AEV-NEW')
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Onchange
    # ------------------------------------------------------------------
    @api.onchange('is_online')
    def _onchange_is_online(self):
        """Clear location when switching to online-only (and vice versa)."""
        if self.is_online and not self.meeting_url:
            self.location = False
        elif not self.is_online:
            self.meeting_url = False

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_announce(self):
        """Announce the event to alumni."""
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError(_(
                    "Only draft events can be announced "
                    "(current: %(s)s for %(n)s).") % {
                    's': rec.state, 'n': rec.display_name})
            rec.state = 'announced'
            rec.message_post(body=_("Event announced."))

    def action_open_registration(self):
        """Open the registration phase."""
        for rec in self:
            if rec.state != 'announced':
                raise ValidationError(_(
                    "Only announced events can open registration "
                    "(current: %(s)s for %(n)s).") % {
                    's': rec.state, 'n': rec.display_name})
            rec.state = 'registration_open'
            rec.message_post(body=_("Registration is now open."))

    def action_start(self):
        """Mark the event as ongoing (in session)."""
        for rec in self:
            if rec.state not in ('registration_open', 'announced'):
                raise ValidationError(_(
                    "Only announced or registration-open events can be "
                    "started (current: %(s)s for %(n)s).") % {
                    's': rec.state, 'n': rec.display_name})
            rec.state = 'ongoing'
            rec.message_post(body=_("Event is now ongoing."))

    def action_complete(self):
        """Mark the event as completed."""
        for rec in self:
            if rec.state != 'ongoing':
                raise ValidationError(_(
                    "Only ongoing events can be completed "
                    "(current: %(s)s for %(n)s).") % {
                    's': rec.state, 'n': rec.display_name})
            rec.state = 'completed'
            rec.message_post(body=_(
                "Event completed. Attendees: %(a)s / Registered: %(r)s.") % {
                'a': rec.attended_count, 'r': rec.registered_count,
            })

    def action_cancel(self):
        """Cancel the event."""
        for rec in self:
            if rec.state in ('completed',):
                raise ValidationError(_(
                    "Cannot cancel a completed event (%s).")
                    % rec.display_name)
            rec.state = 'cancelled'
            rec.message_post(body=_("Event cancelled."))

    def action_reset_to_draft(self):
        """Reset a cancelled event back to draft."""
        for rec in self:
            if rec.state != 'cancelled':
                raise ValidationError(_(
                    "Only cancelled events can be reset to draft "
                    "(current: %(s)s for %(n)s).") % {
                    's': rec.state, 'n': rec.display_name})
            rec.state = 'draft'
            rec.message_post(body=_("Event reset to draft."))

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        """End date must be after start date."""
        for rec in self:
            if rec.start_date and rec.end_date and rec.end_date <= rec.start_date:
                raise ValidationError(_(
                    "End date (%(e)s) must be later than start date "
                    "(%(s)s) for event %(n)s.") % {
                    'e': rec.end_date, 's': rec.start_date,
                    'n': rec.display_name})

    @api.constrains('is_online', 'meeting_url')
    def _check_online_has_url(self):
        """Online events must have a meeting URL."""
        for rec in self:
            if rec.is_online and not rec.meeting_url:
                raise ValidationError(_(
                    "An online event must have a meeting URL (%s).")
                    % rec.display_name)

    @api.constrains('max_attendees')
    def _check_max_attendees(self):
        """Max attendees cannot be negative."""
        for rec in self:
            if rec.max_attendees < 0:
                raise ValidationError(_(
                    "Max attendees cannot be negative (event %s).")
                    % rec.display_name)

    @api.constrains('max_attendees', 'member_ids')
    def _check_capacity(self):
        """Cannot register more members than capacity (if set)."""
        for rec in self:
            if rec.max_attendees > 0 and len(rec.member_ids) > rec.max_attendees:
                raise ValidationError(_(
                    "Event %(n)s has reached its capacity of %(m)s "
                    "attendees (currently registered: %(r)s).") % {
                    'n': rec.display_name,
                    'm': rec.max_attendees,
                    'r': len(rec.member_ids),
                })

    @api.constrains('registration_deadline', 'start_date')
    def _check_registration_deadline(self):
        """Registration deadline must be before event start."""
        for rec in self:
            if (rec.registration_deadline and rec.start_date
                    and rec.registration_deadline > rec.start_date):
                raise ValidationError(_(
                    "Registration deadline (%(d)s) must be on or before "
                    "the event start date (%(s)s) for event %(n)s.") % {
                    'd': rec.registration_deadline,
                    's': rec.start_date,
                    'n': rec.display_name,
                })
