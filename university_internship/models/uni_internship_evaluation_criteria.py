from odoo import api, fields, models, _


class UniInternshipEvaluationCriteria(models.Model):
    _name = 'uni.internship.evaluation.criteria'
    _description = 'Evaluation Criteria'
    _order = 'sequence, name'

    name = fields.Char(string='Criteria Name', required=True, translate=True, index=True)
    code = fields.Char(string='Code', required=True, copy=False, index=True)
    description = fields.Text(string='Description')

    max_score = fields.Float(string='Max Score', digits=(5, 2), default=10.0, required=True, tracking=True)
    weight = fields.Float(string='Weight (%)', digits=(5, 2), default=10.0, required=True, tracking=True,
                           help='Weight in the final evaluation (should sum to 100%).')

    category = fields.Selection([
        ('performance', 'Performance'),
        ('behavior', 'Behavior'),
        ('skills', 'Skills'),
        ('deliverables', 'Deliverables'),
        ('other', 'Other'),
    ], string='Category', default='performance', tracking=True)

    is_active = fields.Boolean(string='Active', default=True, tracking=True)
    sequence = fields.Integer(string='Sequence', default=10)
    color = fields.Integer(string='Color Index', default=0)

    _sql_constraints = [
        ('unique_criteria_code', 'unique(code)', 'Criteria code must be unique!'),
        ('check_max_score_positive', 'check(max_score > 0)', 'Max score must be positive!'),
        ('check_weight_range', 'check(weight >= 0 AND weight <= 100)', 'Weight must be 0-100!'),
    ]
