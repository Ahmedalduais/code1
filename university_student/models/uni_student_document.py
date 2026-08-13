# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniStudentDocument(models.Model):
    """وثائق الطالب — بطاقات الهوية، الشهادات، كشوف الدرجات، الصور، إلخ.

    يدعم التحقق من الوثيقة (``verified``) من قِبل مستخدم مصرّح له مع تاريخ
    التحقق والمُحقّق، كما يدعم تاريخ انتهاء صلاحية الوثيقة (مثل جواز السفر).
    """
    _name = 'uni.student.document'
    _description = 'Student Document'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'student_id, document_type, id desc'

    name = fields.Char(
        string='Document Name', required=True, tracking=True,
        help='Title or description of the document.')
    student_id = fields.Many2one(
        'uni.student', string='Student',
        required=True, ondelete='cascade', tracking=True, index=True)
    university_id = fields.Many2one(
        'uni.university', string='University',
        related='student_id.university_id', store=True, index=True)

    document_type = fields.Selection([
        ('id_card', 'National ID Card'),
        ('passport', 'Passport'),
        ('certificate', 'Certificate'),
        ('transcript', 'Transcript'),
        ('photo', 'Photo'),
        ('medical', 'Medical Record'),
        ('other', 'Other'),
    ], string='Document Type', default='other', required=True, tracking=True, index=True)

    issue_date = fields.Date(string='Issue Date', tracking=True)
    expiry_date = fields.Date(string='Expiry Date', tracking=True,
                              help='Date the document expires (e.g. passport expiry).')
    issued_by = fields.Char(string='Issued By', tracking=True,
                            help='Authority that issued the document.')

    file = fields.Binary(string='File', attachment=True, required=True,
                         help='The document file (PDF, image, etc.).')
    filename = fields.Char(string='Filename', tracking=True)
    file_size = fields.Integer(
        string='File Size (bytes)', compute='_compute_file_size', store=False)

    verified = fields.Boolean(string='Verified', default=False, tracking=True,
                              copy=False)
    verified_by = fields.Many2one(
        'res.users', string='Verified By', readonly=True, copy=False, tracking=True)
    verified_date = fields.Datetime(
        string='Verified Date', readonly=True, copy=False, tracking=True)

    notes = fields.Text(string='Notes', tracking=True)
    color = fields.Integer(string='Color Index', default=0)

    # ------------------------------------------------------------------
    # Computed
    # ------------------------------------------------------------------
    @api.depends('file')
    def _compute_file_size(self):
        for rec in self:
            if rec.file:
                # Odoo stores base64-encoded binary; length × 3/4 ≈ byte size
                rec.file_size = int(len(rec.file) * 0.75)
            else:
                rec.file_size = 0

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def action_verify(self):
        """Mark the document as verified by the current user."""
        for rec in self:
            if rec.verified:
                raise ValidationError(_(
                    "Document %s is already verified.") % rec.display_name)
            rec.write({
                'verified': True,
                'verified_by': self.env.uid,
                'verified_date': fields.Datetime.now(),
            })

    def action_unverify(self):
        """Revoke the verification (manager action)."""
        for rec in self:
            if not rec.verified:
                raise ValidationError(_(
                    "Document %s is not verified yet.") % rec.display_name)
            rec.write({
                'verified': False,
                'verified_by': False,
                'verified_date': False,
            })

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('issue_date', 'expiry_date')
    def _check_dates(self):
        for rec in self:
            if rec.issue_date and rec.expiry_date and rec.expiry_date < rec.issue_date:
                raise ValidationError(_(
                    "Document expiry date cannot be earlier than issue date (%s).")
                    % rec.display_name)

    @api.constrains('verified', 'file')
    def _check_verified_has_file(self):
        for rec in self:
            if rec.verified and not rec.file:
                raise ValidationError(_(
                    "Cannot verify a document without an attached file (%s).")
                    % rec.display_name)
