# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class UniInternshipStudent(models.Model):
    """Internship Student Record — uses delegation inheritance from
    ``uni.student`` (``_inherits``) so that all student identity, contact,
    and academic data is exposed directly on this record.

    Because ``uni.internship`` inherits ``uni.course`` via prototype
    inheritance (and ``uni.course`` has no ``student_id`` inverse field),
    a direct One2many from this record to ``uni.internship`` is not
    possible. Instead, internship statistics are computed by traversing
    the team-member relationship: a student's internships are inferred
    from the teams they belong to.
    """
    _name = 'uni.internship.student'
    _inherits = {'uni.student': 'student_id'}
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Internship Student Record'
    _order = 'student_id'

    student_id = fields.Many2one(
        'uni.student', string='Student', required=True,
        ondelete='restrict', auto_join=True, index=True)

    # ------------------------------------------------------------------
    # Computed internship statistics (inferred from team memberships)
    # ------------------------------------------------------------------
    # NOTE: A direct One2many to uni.internship (inverse 'student_id') is
    # not possible because uni.internship inherits uni.course, which does
    # not declare a student_id field. We therefore compute the stats by
    # traversing the team-member relationship.
    total_internships = fields.Integer(
        compute='_compute_stats', string='Total Internships')
    completed_internships = fields.Integer(
        compute='_compute_stats', string='Completed')
    total_hours_completed = fields.Float(
        compute='_compute_stats', string='Total Hours', store=True)
    average_grade = fields.Float(
        compute='_compute_stats', string='Average Grade', store=True)

    internship_record_ids = fields.Many2many(
        'uni.internship', string='Internship Records',
        compute='_compute_internship_records')

    notes = fields.Text(string='Notes')
    # NOTE: 'active' is NOT redeclared here — it is delegated from
    # uni.student (which in turn delegates it from uni.person via the
    # archivable mixin). Redeclaring it would raise a conflict with the
    # delegated field at registry-build time.

    @api.depends('student_id')
    def _compute_stats(self):
        """Compute internship stats by traversing team memberships."""
        TeamMember = self.env['uni.internship.team.member']
        for rec in self:
            if not rec.student_id:
                rec.total_internships = 0
                rec.completed_internships = 0
                rec.total_hours_completed = 0.0
                rec.average_grade = 0.0
                continue
            members = TeamMember.search([
                ('student_id', '=', rec.student_id.id),
            ])
            internships = members.mapped('team_id.internship_id')
            rec.total_internships = len(internships)
            rec.completed_internships = len(
                internships.filtered(
                    lambda i: i.internship_state == 'completed'))
            rec.total_hours_completed = sum(
                i.hours_completed for i in internships)
            grades = internships.filtered(
                lambda i: i.final_grade > 0).mapped('final_grade')
            rec.average_grade = (
                sum(grades) / len(grades) if grades else 0.0
            )

    def _compute_internship_records(self):
        """Compute the set of internships this student has participated in."""
        TeamMember = self.env['uni.internship.team.member']
        for rec in self:
            if not rec.student_id:
                rec.internship_record_ids = [(6, 0, [])]
                continue
            members = TeamMember.search([
                ('student_id', '=', rec.student_id.id),
            ])
            internships = members.mapped('team_id.internship_id')
            rec.internship_record_ids = [(6, 0, internships.ids)]

    def action_view_internships(self):
        """Smart-button action: open the internships of this student."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Internships'),
            'res_model': 'uni.internship',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.internship_record_ids.ids)],
        }
