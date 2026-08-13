# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniPortalNotification(models.Model):
    """الإشعارات — إشعارات موجهة لمستخدمي البوابة (طلاب/أعضاء تدريس/الكل).

    يدعم هذا النموذج إرسال إشعارات فردية (طالب واحد / عضو تدريس واحد) أو
    إشعارات جماعية (``recipient_type='all'`` تُرسل لكل حسابات البوابات
    النشطة). كل إشعار له نوع (معلومة/تحذير/نجاح/خطأ/إعلان/واجب/درجة/دفع/
    فعالية) وأولوية (منخفضة/عادية/عالية/عاجلة) ورابط إجراء اختياري يسمح
    بالانتقال إلى سجل معين عند النقر على الإشعار.
    """
    _name = 'uni.portal.notification'
    _description = 'Portal Notification'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'priority desc, send_date desc, id desc'

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Reference', compute='_compute_name', store=True, index=True,
        help='Auto-generated reference combining code and title.')
    code = fields.Char(
        string='Code', copy=False, index=True, tracking=True, readonly=True,
        help='Auto-generated unique code (sequence PNF/year/00001).')

    # ------------------------------------------------------------------
    # Recipients
    # ------------------------------------------------------------------
    recipient_type = fields.Selection([
        ('student', 'Student'),
        ('faculty', 'Faculty'),
        ('all', 'All Portal Users'),
    ], string='Recipient Type', default='student', required=True, index=True,
        tracking=True)
    student_id = fields.Many2one(
        'uni.student', string='Student', ondelete='cascade',
        help='Direct student recipient (optional — alternative to portal_student_id).')
    faculty_id = fields.Many2one(
        'uni.faculty', string='Faculty Member', ondelete='cascade',
        help='Direct faculty recipient (optional — alternative to portal_faculty_id).')
    portal_student_id = fields.Many2one(
        'uni.portal.student', string='Student Portal Account',
        ondelete='cascade', index=True,
        help='The student portal account this notification is addressed to.')
    portal_faculty_id = fields.Many2one(
        'uni.portal.faculty', string='Faculty Portal Account',
        ondelete='cascade', index=True,
        help='The faculty portal account this notification is addressed to.')
    user_id = fields.Many2one(
        'res.users', string='Recipient User', ondelete='cascade', index=True,
        tracking=True,
        help='The Odoo user that will see this notification in their portal.')

    # ------------------------------------------------------------------
    # Content
    # ------------------------------------------------------------------
    notification_type = fields.Selection([
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('success', 'Success'),
        ('error', 'Error'),
        ('announcement', 'Announcement'),
        ('assignment', 'Assignment'),
        ('grade', 'Grade'),
        ('payment', 'Payment'),
        ('event', 'Event'),
    ], string='Type', default='info', required=True, index=True, tracking=True)
    title = fields.Char(string='Title', required=True, translate=True, tracking=True)
    message = fields.Text(string='Message', required=True)
    priority = fields.Selection([
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ], string='Priority', default='normal', required=True, index=True,
        tracking=True)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    is_read = fields.Boolean(
        string='Read', default=False, copy=False, tracking=True, index=True)
    read_date = fields.Datetime(
        string='Read Date', readonly=True, copy=False)
    send_date = fields.Datetime(
        string='Send Date', default=fields.Datetime.now, required=True,
        index=True, tracking=True)
    expiry_date = fields.Datetime(
        string='Expiry Date', tracking=True,
        help='Notification will be hidden after this date.')

    # ------------------------------------------------------------------
    # Action link
    # ------------------------------------------------------------------
    action_url = fields.Char(
        string='Action URL', tracking=True,
        help='URL to navigate when the notification is clicked.')
    action_model = fields.Char(
        string='Action Model', tracking=True,
        help='Technical model name of the related record.')
    action_res_id = fields.Integer(
        string='Action Record ID', tracking=True,
        help='ID of the related record within the action model.')
    related_record = fields.Char(
        string='Related Record', compute='_compute_related_record',
        help='Human-readable label of the related record (model,id,display_name).')

    # ------------------------------------------------------------------
    # SQL constraints
    # ------------------------------------------------------------------
    _sql_constraints = [
        ('unique_code', 'unique(code)',
         'Notification code must be unique!'),
    ]

    # ------------------------------------------------------------------
    # Create — auto-generate code via ir.sequence
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('code'):
                vals['code'] = self.env['ir.sequence'].next_by_code(
                    'uni.portal.notification') or _('PNF-NEW')
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends('title', 'code')
    def _compute_name(self):
        for rec in self:
            if rec.code and rec.title:
                rec.name = '[%s] %s' % (rec.code, rec.title)
            elif rec.title:
                rec.name = rec.title
            elif rec.code:
                rec.name = rec.code
            else:
                rec.name = _('New Notification')

    @api.depends('action_model', 'action_res_id')
    def _compute_related_record(self):
        for rec in self:
            if not rec.action_model or not rec.action_res_id:
                rec.related_record = False
                continue
            try:
                Model = self.env[rec.action_model].sudo()
            except KeyError:
                rec.related_record = False
                continue
            record = Model.browse(rec.action_res_id).exists()
            if record:
                rec.related_record = '%s,%d — %s' % (
                    rec.action_model, rec.action_res_id, record.display_name)
            else:
                rec.related_record = '%s,%d — (deleted)' % (
                    rec.action_model, rec.action_res_id)

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_mark_read(self):
        """Mark the notification as read and store the read timestamp."""
        for rec in self:
            if not rec.is_read:
                rec.write({
                    'is_read': True,
                    'read_date': fields.Datetime.now(),
                })

    def action_mark_unread(self):
        """Mark the notification as unread."""
        for rec in self:
            if rec.is_read:
                rec.write({
                    'is_read': False,
                    'read_date': False,
                })

    # ------------------------------------------------------------------
    # Public API — class-style helper for sending notifications
    # ------------------------------------------------------------------
    @api.model
    def send_notification(self, recipient_type, title, message, **kwargs):
        """Create and dispatch portal notification(s).

        :param recipient_type: 'student' | 'faculty' | 'all'
        :param title: notification title (translatable)
        :param message: notification body text
        :param kwargs: extra field values (notification_type, priority,
                       student_id, faculty_id, portal_student_id,
                       portal_faculty_id, user_id, action_url,
                       action_model, action_res_id, expiry_date, send_date)
        :return: ``uni.portal.notification`` recordset
        """
        if recipient_type == 'all':
            notifications = self.env['uni.portal.notification']
            portal_students = self.env['uni.portal.student'].sudo().search([
                ('state', '=', 'active'),
            ])
            for portal_student in portal_students:
                user = portal_student.portal_user_id or portal_student.user_id
                if not user:
                    continue
                vals = {
                    'recipient_type': 'student',
                    'portal_student_id': portal_student.id,
                    'student_id': portal_student.student_id.id,
                    'user_id': user.id,
                    'title': title,
                    'message': message,
                }
                vals.update(kwargs)
                # Avoid forcing the same portal_faculty_id from kwargs on students
                vals.pop('portal_faculty_id', False)
                vals.pop('faculty_id', False)
                notifications |= self.create(vals)
            portal_faculties = self.env['uni.portal.faculty'].sudo().search([
                ('state', '=', 'active'),
            ])
            for portal_faculty in portal_faculties:
                user = portal_faculty.portal_user_id or portal_faculty.user_id
                if not user:
                    continue
                vals = {
                    'recipient_type': 'faculty',
                    'portal_faculty_id': portal_faculty.id,
                    'faculty_id': portal_faculty.faculty_id.id,
                    'user_id': user.id,
                    'title': title,
                    'message': message,
                }
                vals.update(kwargs)
                vals.pop('portal_student_id', False)
                vals.pop('student_id', False)
                notifications |= self.create(vals)
            return notifications

        vals = {
            'recipient_type': recipient_type,
            'title': title,
            'message': message,
        }
        vals.update(kwargs)
        return self.create(vals)

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('recipient_type', 'student_id', 'faculty_id')
    def _check_recipient_consistency(self):
        for rec in self:
            if rec.recipient_type == 'student' and rec.faculty_id:
                raise ValidationError(_(
                    "Notification %s is addressed to a student but has a "
                    "faculty recipient.") % rec.display_name)
            if rec.recipient_type == 'faculty' and rec.student_id:
                raise ValidationError(_(
                    "Notification %s is addressed to a faculty member but "
                    "has a student recipient.") % rec.display_name)

    @api.constrains('expiry_date', 'send_date')
    def _check_dates(self):
        for rec in self:
            if rec.expiry_date and rec.send_date and \
                    rec.expiry_date < rec.send_date:
                raise ValidationError(_(
                    "Expiry date cannot be earlier than send date "
                    "(notification %s).") % rec.display_name)

    @api.constrains('action_model')
    def _check_action_model(self):
        for rec in self:
            if not rec.action_model:
                continue
            try:
                self.env[rec.action_model]
            except KeyError:
                raise ValidationError(_(
                    "Action model %s does not exist in the registry.")
                    % rec.action_model)

    @api.constrains('action_model', 'action_res_id')
    def _check_action_record_exists(self):
        for rec in self:
            if not rec.action_model or not rec.action_res_id:
                continue
            try:
                Model = self.env[rec.action_model]
            except KeyError:
                # Already covered by _check_action_model — skip silently here
                continue
            record = Model.sudo().browse(rec.action_res_id).exists()
            if not record:
                raise ValidationError(_(
                    "Related record %s,%d does not exist.")
                    % (rec.action_model, rec.action_res_id))
