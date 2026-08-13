# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniLmsForum(models.Model):
    """منتدى نقاش داخل المقرر الإلكتروني — يدعم الإعلانات والمشاركات."""
    _name = 'uni.lms.forum'
    _description = 'LMS Forum'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'lms_course_id, sequence, id'

    name = fields.Char(string='Name', required=True, translate=True, tracking=True, index=True)
    code = fields.Char(string='Code', copy=False, tracking=True, index=True)
    lms_course_id = fields.Many2one('uni.lms.course', string='LMS Course',
                                    required=True, ondelete='cascade', tracking=True, index=True)
    description = fields.Text(string='Description')
    moderator_name = fields.Char(
        string='Moderator Name', copy=False, tracking=True, index=True,
        help='Free-text moderator name (the LMS module does not depend on '
             'university_faculty, so the moderator is recorded as a string).')
    is_announcements_only = fields.Boolean(string='Announcements Only', default=False,
                                           help='When enabled, only moderators can post.')
    allow_student_posts = fields.Boolean(string='Allow Student Posts', default=True, tracking=True)
    sequence = fields.Integer(string='Sequence', default=10)
    post_ids = fields.One2many('uni.lms.forum.post', 'forum_id', string='Posts')
    post_count = fields.Integer(compute='_compute_post_count', string='Posts')
    pinned_post_count = fields.Integer(compute='_compute_pinned_post_count', string='Pinned Posts')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('closed', 'Closed'),
    ], string='Status', default='draft', tracking=True, group_expand='_group_expand_states')
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('unique_forum_code', 'unique(code)', 'Forum code must be unique!'),
    ]

    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in states]

    @api.depends('post_ids')
    def _compute_post_count(self):
        for rec in self:
            rec.post_count = len(rec.post_ids)

    @api.depends('post_ids.is_pinned')
    def _compute_pinned_post_count(self):
        for rec in self:
            rec.pinned_post_count = len(rec.post_ids.filtered(lambda p: p.is_pinned))

    @api.constrains('is_announcements_only', 'allow_student_posts')
    def _check_announcements_consistency(self):
        """منتدى الإعلانات فقط لا يسمح بمشاركات الطلاب."""
        for rec in self:
            if rec.is_announcements_only and rec.allow_student_posts:
                raise ValidationError(_(
                    'Announcements-only forum "%s" cannot allow student posts.',
                    rec.display_name))

    def action_activate(self):
        """تفعيل المنتدى ليصبح متاحاً للنشر."""
        for rec in self:
            rec.state = 'active'

    def action_close(self):
        """إغلاق المنتدى ومنع المشاركات الإضافية."""
        for rec in self:
            rec.state = 'closed'

    def action_draft(self):
        """إعادة المنتدى إلى حالة المسودة."""
        for rec in self:
            rec.state = 'draft'

    def action_view_posts(self):
        """فتح سجل مشاركات المنتدى."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Forum Posts'),
            'res_model': 'uni.lms.forum.post',
            'view_mode': 'list,form',
            'domain': [('forum_id', '=', self.id)],
            'context': {'default_forum_id': self.id},
        }


class UniLmsForumPost(models.Model):
    """مشاركة في منتدى المقرر — موضوع أو رد على موضوع."""
    _name = 'uni.lms.forum.post'
    _description = 'LMS Forum Post'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'forum_id, is_pinned desc, create_date desc, id'
    _rec_name = 'title'

    forum_id = fields.Many2one('uni.lms.forum', string='Forum',
                               required=True, ondelete='cascade', tracking=True, index=True)
    author_id = fields.Many2one('res.users', string='Author',
                                required=True, ondelete='restrict',
                                default=lambda self: self.env.user, tracking=True, index=True)
    title = fields.Char(string='Title', translate=True, tracking=True)
    content = fields.Html(string='Content', required=True)
    parent_id = fields.Many2one('uni.lms.forum.post', string='Parent Post',
                                ondelete='restrict', index=True,
                                domain="[('forum_id', '=', forum_id)]")
    child_ids = fields.One2many('uni.lms.forum.post', 'parent_id', string='Replies')
    is_pinned = fields.Boolean(string='Pinned', default=False, tracking=True,
                               help='Pinned posts appear at the top of the forum.')
    is_locked = fields.Boolean(string='Locked', default=False, tracking=True,
                               help='Locked posts cannot receive new replies.')
    view_count = fields.Integer(string='Views', default=0, copy=False)
    reply_count = fields.Integer(compute='_compute_reply_count', string='Replies')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('hidden', 'Hidden'),
    ], string='Status', default='published', tracking=True, group_expand='_group_expand_states')
    create_date = fields.Datetime(string='Created On', readonly=True, index=True)
    write_date = fields.Datetime(string='Last Updated', readonly=True)

    def _group_expand_states(self, states, domain, order):
        return [key for key, _ in states]

    @api.depends('child_ids')
    def _compute_reply_count(self):
        for rec in self:
            rec.reply_count = len(rec.child_ids)

    @api.constrains('parent_id')
    def _check_parent_not_self(self):
        """لا يمكن أن يكون الرد أبّاً لنفسه أو لسلفه."""
        for rec in self:
            if rec.parent_id and rec.parent_id.id == rec.id:
                raise ValidationError(_(
                    'A post cannot be its own parent.'))
            # Detect cycles up to 5 levels deep
            current = rec.parent_id
            depth = 0
            while current and depth < 5:
                if current.id == rec.id:
                    raise ValidationError(_(
                        'Circular reply chain detected for post "%s".', rec.display_name))
                current = current.parent_id
                depth += 1

    @api.constrains('parent_id', 'forum_id')
    def _check_parent_same_forum(self):
        """الرد يجب أن ينتمي لنفس المنتدى."""
        for rec in self:
            if rec.parent_id and rec.parent_id.forum_id.id != rec.forum_id.id:
                raise ValidationError(_(
                    'Reply parent must belong to the same forum.'))

    @api.constrains('forum_id', 'is_locked')
    def _check_locked_post_no_replies(self):
        """عند إنشاء رد على مشاركة مقفلة، يجب رفضه."""
        for rec in self:
            if rec.parent_id and rec.parent_id.is_locked:
                raise ValidationError(_(
                    'Cannot reply to a locked post "%s".',
                    rec.parent_id.display_name))

    def action_publish(self):
        """نشر المشاركة."""
        for rec in self:
            rec.state = 'published'

    def action_hide(self):
        """إخفاء المشاركة عن الطلاب."""
        for rec in self:
            rec.state = 'hidden'

    def action_pin(self):
        """تثبيت المشاركة أعلى المنتدى."""
        for rec in self:
            rec.is_pinned = True

    def action_unpin(self):
        """إلغاء تثبيت المشاركة."""
        for rec in self:
            rec.is_pinned = False

    def action_lock(self):
        """قفل المشاركة لمنع الردود."""
        for rec in self:
            rec.is_locked = True

    def action_unlock(self):
        """فتح قفل المشاركة."""
        for rec in self:
            rec.is_locked = False

    def action_increment_view(self):
        """زيادة عداد المشاهدات بمقدار واحد."""
        for rec in self:
            rec.view_count = (rec.view_count or 0) + 1
        return True
