# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class UniCourseDelivery(models.Model):
    """Course Delivery Mode — defines how a course is delivered
    (on-campus, online synchronous/asynchronous, hybrid, blended, distance).
    """
    _name = 'uni.course.delivery'
    _description = 'Course Delivery Mode'
    _order = 'sequence, name'

    name = fields.Char(string='Delivery Name', required=True, translate=True)
    code = fields.Char(string='Code', required=True, copy=False, index=True)
    sequence = fields.Integer(string='Sequence', default=10)

    delivery_method = fields.Selection([
        ('on_campus', 'On-Campus'),
        ('online_sync', 'Online (Synchronous)'),
        ('online_async', 'Online (Asynchronous)'),
        ('hybrid', 'Hybrid'),
        ('blended', 'Blended Learning'),
        ('distance', 'Distance Learning'),
        ('correspondence', 'Correspondence'),
    ], string='Delivery Method', required=True, tracking=True)

    has_physical_classroom = fields.Boolean(string='Requires Physical Classroom',
                                             default=True)
    has_virtual_classroom = fields.Boolean(string='Requires Virtual Classroom',
                                            default=False)
    has_livestream = fields.Boolean(string='Has Livestream', default=False)
    has_recording = fields.Boolean(string='Has Recording', default=False)

    default_max_enrollment = fields.Integer(string='Default Max Enrollment', default=30)
    default_session_duration = fields.Float(string='Default Session Duration (hours)',
                                             default=1.5)
    sessions_per_week = fields.Integer(string='Sessions per Week', default=2)

    requires_proctoring = fields.Boolean(string='Requires Online Proctoring',
                                          default=False)
    requires_special_software = fields.Boolean(string='Requires Special Software',
                                                default=False)
    software_requirements = fields.Text(string='Software Requirements')

    description = fields.Text(string='Description')
    color = fields.Integer(string='Color Index', default=0)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_course_delivery_code', 'unique(code)',
         'Course delivery code must be unique!'),
    ]

    @api.onchange('delivery_method')
    def _onchange_delivery_method(self):
        """Set sensible defaults based on the chosen delivery method."""
        if self.delivery_method == 'on_campus':
            self.has_physical_classroom = True
            self.has_virtual_classroom = False
            self.has_livestream = False
            self.has_recording = False
        elif self.delivery_method in ('online_sync', 'hybrid', 'blended'):
            self.has_virtual_classroom = True
            self.has_livestream = True
            if self.delivery_method == 'on_campus':
                self.has_physical_classroom = True
            elif self.delivery_method == 'hybrid':
                self.has_physical_classroom = True
            else:
                self.has_physical_classroom = False
        elif self.delivery_method in ('online_async', 'distance'):
            self.has_virtual_classroom = True
            self.has_physical_classroom = False
            self.has_livestream = False
            self.has_recording = True
