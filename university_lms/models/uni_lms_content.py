# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniLmsContent(models.Model):
    """المحتوى التعليمي — أصغر وحدة محتوى داخل المقرر الإلكتروني.

    يدعم أنواعاً متعددة (فيديو/مستند/رابط/نص/صورة/صوت/عرض تقديمي).
    يمكن تنظيمه هرمياً عبر ``parent_id`` لإنشاء وحدات/أقسام.
    """
    _name = 'uni.lms.content'
    _description = 'LMS Content'
    _inherit = ['mail.thread', 'uni.mixin.archivable']
    _order = 'parent_id, sequence, id'
    _rec_name = 'title'

    name = fields.Char(string='Reference', copy=False, tracking=True, index=True,
                       help='Optional internal reference for the content item.')
    sequence = fields.Integer(string='Sequence', default=10)
    lms_course_id = fields.Many2one('uni.lms.course', string='LMS Course',
                                    required=True, ondelete='cascade', tracking=True, index=True)
    content_type = fields.Selection([
        ('video', 'Video'),
        ('document', 'Document'),
        ('presentation', 'Presentation'),
        ('link', 'External Link'),
        ('text', 'Text'),
        ('image', 'Image'),
        ('audio', 'Audio'),
        ('other', 'Other'),
    ], string='Content Type', default='document', required=True, tracking=True, index=True)
    title = fields.Char(string='Title', required=True, tracking=True, translate=True)
    description = fields.Text(string='Description')
    file = fields.Binary(string='File', attachment=True)
    filename = fields.Char(string='Filename')
    url = fields.Char(string='URL', tracking=True,
                      help='External link for content_type = link.')
    text_content = fields.Html(string='Text Content')
    duration = fields.Float(string='Duration (hours)', default=0.0,
                            help='Estimated duration in hours (displayed as HH:MM).')
    file_size = fields.Integer(compute='_compute_file_size', string='File Size (bytes)',
                               help='Computed from the attached binary file.')
    is_downloadable = fields.Boolean(string='Downloadable', default=True)
    is_required = fields.Boolean(string='Required', default=True,
                                 help='Required content counts toward completion.')
    sequence_number = fields.Integer(string='Sequence Number', default=1,
                                     help='Logical order number for display in course outline.')
    parent_id = fields.Many2one('uni.lms.content', string='Parent Section',
                                ondelete='restrict', index=True,
                                domain="[('lms_course_id', '=', lms_course_id), "
                                       "('content_type', '=', 'other')]",
                               help='Optional parent section/module for grouping.')
    child_ids = fields.One2many('uni.lms.content', 'parent_id', string='Child Items')
    view_count = fields.Integer(string='Views', default=0, copy=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ], string='Status', default='draft', tracking=True, group_expand='_group_expand_states')
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('check_duration_positive',
         'check(duration >= 0)',
         'Duration cannot be negative!'),
    ]

    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in states]

    @api.depends('file')
    def _compute_file_size(self):
        """حجم الملف المرفق بالبايت (يُحسب من طول البيانات الثنائية)."""
        for rec in self:
            if rec.file:
                # Base64-encoded: actual byte length ≈ len * 3/4 (minus padding)
                try:
                    rec.file_size = len(rec.file) * 3 // 4
                except Exception:
                    rec.file_size = 0
            else:
                rec.file_size = 0

    @api.constrains('content_type', 'file', 'url', 'text_content')
    def _check_content_payload(self):
        """لكل نوع محتوى يجب توفير البيانات المناسبة:
        - video/document/presentation/image/audio: ملف
        - link: رابط URL
        - text: محتوى نصي
        """
        for rec in self:
            if rec.content_type == 'link' and not rec.url:
                raise ValidationError(_(
                    'Content "%s" of type "Link" must have a URL.', rec.display_name))
            if rec.content_type == 'text' and not rec.text_content:
                raise ValidationError(_(
                    'Content "%s" of type "Text" must have text content.', rec.display_name))
            if rec.content_type in ('video', 'document', 'presentation',
                                    'image', 'audio') and not rec.file:
                raise ValidationError(_(
                    'Content "%s" of type "%s" must have an attached file.',
                    rec.display_name, rec.content_type))

    @api.constrains('parent_id')
    def _check_parent_not_self(self):
        """لا يمكن أن يكون المحتوى أبّاً لنفسه."""
        for rec in self:
            if rec.parent_id and rec.parent_id.id == rec.id:
                raise ValidationError(_(
                    'Content "%s" cannot be its own parent.', rec.display_name))

    @api.constrains('parent_id', 'lms_course_id')
    def _check_parent_same_course(self):
        """يجب أن ينتمي الأب إلى نفس المقرر الإلكتروني."""
        for rec in self:
            if rec.parent_id and rec.parent_id.lms_course_id.id != rec.lms_course_id.id:
                raise ValidationError(_(
                    'Parent content must belong to the same LMS course (%s).',
                    rec.display_name))

    def action_publish(self):
        """نشر المحتوى ليصبح متاحاً للطلاب."""
        for rec in self:
            rec.state = 'published'

    def action_archive(self):
        """أرشفة المحتوى مع تطبيق سلوك الأرشفة القياسي."""
        res = super().action_archive()
        for rec in self:
            rec.state = 'archived'
        return res

    def action_unarchive(self):
        """إلغاء أرشفة المحتوى."""
        res = super().action_unarchive()
        for rec in self:
            if rec.state == 'archived':
                rec.state = 'draft'
        return res

    def action_increment_view(self):
        """زيادة عداد المشاهدات بمقدار واحد (يستخدم عند عرض المحتوى)."""
        for rec in self:
            rec.view_count = (rec.view_count or 0) + 1
        return True
