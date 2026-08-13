# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class UniMixinArchivable(models.AbstractModel):
    """ميكسن للأرشفة والتفعيل — يضيف حالة نشط وتاريخ الأرشفة."""
    _name = 'uni.mixin.archivable'
    _description = 'University Archivable Mixin'

    active = fields.Boolean(default=True, tracking=True)
    archived_date = fields.Datetime(string='Archived Date', readonly=True, copy=False)
    archived_by = fields.Many2one('res.users', string='Archived By', readonly=True, copy=False)

    def action_archive(self):
        for record in self:
            record.write({
                'active': False,
                'archived_date': fields.Datetime.now(),
                'archived_by': self.env.uid,
            })

    def action_unarchive(self):
        for record in self:
            record.write({
                'active': True,
                'archived_date': False,
                'archived_by': False,
            })


class UniMixinSequence(models.AbstractModel):
    """ميكسن للتكويد التلقائي — يستخدم ir.sequence."""
    _name = 'uni.mixin.sequence'
    _description = 'University Sequence Mixin'

    code = fields.Char(string='Reference', required=True, copy=False, readonly=True,
                       default=lambda self: _('New'), index=True)
    sequence_id = fields.Many2one('ir.sequence', string='Sequence',
                                  help='Sequence used for auto-coding', copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('code') or vals.get('code') == _('New'):
                seq_code = self._get_sequence_code()
                if seq_code:
                    vals['code'] = self.env['ir.sequence'].next_by_code(seq_code) or _('New')
        return super().create(vals_list)

    def _get_sequence_code(self):
        """تُعاد بواسطة النموذج الوريث — كود التسلسل الخاص بالنموذج."""
        self.ensure_one()
        return False


class UniMixinMultiCompany(models.AbstractModel):
    """ميكسن لتعدد الشركات — يضيف حقل company_id."""
    _name = 'uni.mixin.multi.company'
    _description = 'University Multi-Company Mixin'

    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company,
        index=True, tracking=True,
    )


class UniPersonMixin(models.AbstractModel):
    """ميكسن مشترك للأشخاص — يضيف بيانات الهوية والاتصال الأساسية."""
    _name = 'uni.person.mixin'
    _description = 'University Person Mixin'

    partner_id = fields.Many2one('res.partner', string='Related Partner',
                                 ondelete='restrict', tracking=True, index=True)
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ], string='Gender', tracking=True)
    birth_date = fields.Date(string='Date of Birth', tracking=True)
    nationality_id = fields.Many2one('res.country', string='Nationality')
    national_id = fields.Char(string='National ID', tracking=True, index=True)
    passport_no = fields.Char(string='Passport Number', tracking=True)
    religion = fields.Char(string='Religion')
    marital_status = fields.Selection([
        ('single', 'Single'),
        ('married', 'Married'),
        ('divorced', 'Divorced'),
        ('widowed', 'Widowed'),
    ], string='Marital Status', default='single', tracking=True)
    blood_group = fields.Selection([
        ('a+', 'A+'), ('a-', 'A-'),
        ('b+', 'B+'), ('b-', 'B-'),
        ('ab+', 'AB+'), ('ab-', 'AB-'),
        ('o+', 'O+'), ('o-', 'O-'),
    ], string='Blood Group')
    age = fields.Integer(compute='_compute_age', string='Age')

    @api.depends('birth_date')
    def _compute_age(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.birth_date:
                rec.age = today.year - rec.birth_date.year - (
                    (today.month, today.day) < (rec.birth_date.month, rec.birth_date.day)
                )
            else:
                rec.age = 0
