# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UniAccreditationStandard(models.Model):
    """معيار الاعتماد — يمثل معياراً تصدره جهة اعتماد لتقييم البرامج.

    يدعم الهيكل الهرمي عبر parent_id / child_ids بحيث يمكن تنظيم
    المعايير في فئات وأقسام فرعية. لكل معيار وزن ودرجة دنيا لاعتباره
    مستوفى، وعلم is_mandatory لتمييز المعايير الإلزامية.
    """
    _name = 'uni.accreditation.standard'
    _description = 'Accreditation Standard'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'uni.mixin.archivable']
    _order = 'accreditation_body_id, parent_id, sequence, id'
    _parent_store = True

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Name', required=True, tracking=True, translate=True, index=True,
        help='Name of the accreditation standard.')
    code = fields.Char(
        string='Code', tracking=True, copy=False, index=True,
        help='Short code identifying the standard (e.g. SR-1, SR-2.1).')
    sequence = fields.Integer(
        string='Sequence', default=10, index=True,
        help='Order in which the standard appears within its parent / body.')

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------
    accreditation_body_id = fields.Many2one(
        'uni.accreditation.body', string='Accreditation Body',
        required=True, ondelete='restrict', tracking=True, index=True,
        help='The accreditation body that issued this standard.')
    standard_type = fields.Selection([
        ('institutional', 'Institutional'),
        ('programmatic', 'Programmatic'),
        ('faculty', 'Faculty'),
        ('student', 'Student'),
        ('resources', 'Resources'),
        ('governance', 'Governance'),
    ], string='Standard Type', default='programmatic',
        tracking=True, index=True,
        help='Category of the standard.')

    # ------------------------------------------------------------------
    # Hierarchy
    # ------------------------------------------------------------------
    parent_id = fields.Many2one(
        'uni.accreditation.standard', string='Parent Standard',
        ondelete='restrict', tracking=True, index=True,
        help='Optional parent standard for hierarchical structuring.')
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many(
        'uni.accreditation.standard', 'parent_id', string='Child Standards')

    # ------------------------------------------------------------------
    # Assessment configuration
    # ------------------------------------------------------------------
    description = fields.Text(string='Description')
    weight = fields.Float(
        string='Weight', default=1.0, digits=(5, 2), tracking=True,
        help='Weight of this standard in the overall assessment '
             '(used to compute the program overall score).')
    is_mandatory = fields.Boolean(
        string='Mandatory', default=True, tracking=True,
        help='If checked, this standard must be met for accreditation.')
    minimum_score = fields.Float(
        string='Minimum Score', default=60.0, digits=(5, 2), tracking=True,
        help='Minimum score (0-100) required to consider this standard met.')

    # ------------------------------------------------------------------
    # Reverse relations / counts
    # ------------------------------------------------------------------
    program_standard_ids = fields.One2many(
        'uni.accreditation.program.standard', 'standard_id',
        string='Program Assessments')
    program_standard_count = fields.Integer(
        compute='_compute_program_standard_count', string='Assessments')

    # ------------------------------------------------------------------
    # SQL constraints
    # ------------------------------------------------------------------
    _sql_constraints = [
        ('unique_code_per_body',
         'unique(code, accreditation_body_id)',
         'The standard code must be unique per accreditation body!'),
        ('check_weight_positive',
         'CHECK(weight >= 0)',
         'The standard weight must be positive or zero!'),
        ('check_minimum_score_range',
         'CHECK(minimum_score >= 0 AND minimum_score <= 100)',
         'The minimum score must be between 0 and 100!'),
    ]

    # ------------------------------------------------------------------
    # Computed counts
    # ------------------------------------------------------------------
    @api.depends('program_standard_ids')
    def _compute_program_standard_count(self):
        for rec in self:
            rec.program_standard_count = len(rec.program_standard_ids)

    # ------------------------------------------------------------------
    # Validations
    # ------------------------------------------------------------------
    @api.constrains('parent_id')
    def _check_parent_hierarchy(self):
        """Prevent cycles in the standard hierarchy."""
        for rec in self:
            if rec.parent_id:
                # Cycle detection by walking up the parent chain
                current = rec.parent_id
                while current:
                    if current.id == rec.id:
                        raise ValidationError(_(
                            "Cannot set parent: this would create a cycle "
                            "in the accreditation standard hierarchy "
                            "(standard %s).") % rec.display_name)
                    current = current.parent_id
                # Ensure parent belongs to same accreditation body
                if rec.parent_id.accreditation_body_id != rec.accreditation_body_id:
                    raise ValidationError(_(
                        "Parent standard must belong to the same "
                        "accreditation body as the child (standard %s).")
                        % rec.display_name)

    # ------------------------------------------------------------------
    # Hierarchy helper
    # ------------------------------------------------------------------
    def get_child_standards(self):
        """Return all direct and indirect child standards of the current set.

        Uses the parent_path field to fetch descendants in one query.
        The result excludes the standards themselves (only descendants).
        """
        self.ensure_one()
        if not self.parent_path:
            return self.env['uni.accreditation.standard']
        # parent_path format: "1/2/3/" — descendants share the prefix
        prefix = self.parent_path
        return self.env['uni.accreditation.standard'].search([
            ('parent_path', 'like', prefix + '%'),
            ('id', '!=', self.id),
        ])

    # ------------------------------------------------------------------
    # Smart button
    # ------------------------------------------------------------------
    def action_view_program_assessments(self):
        self.ensure_one()
        return {
            'name': _('Program Assessments'),
            'type': 'ir.actions.act_window',
            'res_model': 'uni.accreditation.program.standard',
            'view_mode': 'list,form',
            'domain': [('standard_id', '=', self.id)],
            'context': {'default_standard_id': self.id},
        }
