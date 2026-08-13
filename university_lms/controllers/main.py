# -*- coding: utf-8 -*-
from odoo import _, fields, http
from odoo.http import request
from odoo.exceptions import AccessError, ValidationError


class UniversityLmsController(http.Controller):
    """HTTP controllers for the University LMS public website.

    Routes serve:
    - Course catalog (list of published LMS courses)
    - Course detail page (with content outline, assignments, quizzes)
    - Enrollment endpoint (creates a ``uni.lms.progress`` record)
    - Content view page (increments view counter)
    - Student progress dashboard (lists all the user's progress records)

    NOTE: This module depends ONLY on ``university_curriculum`` + ``website``.
    If ``university_student`` is also installed, the controllers below will
    auto-fill ``student_name`` / ``student_code`` from the logged-in user's
    linked ``uni.student`` record. Otherwise, the user is identified solely
    by ``res.users`` (``user_id``) and the student_name/code fields are
    filled from the user's display name and email.
    """

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _student_model_available():
        """Return True if the ``uni.student`` model is loaded in the env."""
        return 'uni.student' in request.env

    @classmethod
    def _get_student_for_user(cls, user):
        """Return the ``uni.student`` record linked to the current user.

        Returns an empty recordset if ``university_student`` is not
        installed or the user has no linked student record.
        """
        if not user or not user.id:
            return request.env['uni.student'].sudo()
        if not cls._student_model_available():
            return request.env['uni.student'].sudo()
        partner = user.partner_id
        if not partner:
            return request.env['uni.student'].sudo()
        # uni.student uses _inherits uni.person -> partner_id
        return request.env['uni.student'].sudo().search([
            ('partner_id', '=', partner.id),
        ], limit=1)

    @classmethod
    def _get_or_create_student_identity(cls, user):
        """Return ``(student_name, student_code, user_id)`` for the current user.

        - If ``university_student`` is installed and the user has a linked
          ``uni.student``, return the student's name + student code.
        - Otherwise, fall back to the user's display name (or partner name)
          and the user's login/email as the ``student_code``.

        This guarantees the LMS works with or without ``university_student``.
        """
        if not user or not user.id:
            return ('', '', False)
        student = cls._get_student_for_user(user)
        if student:
            code = student.code or student.student_code or ''
            name = student.display_name or user.display_name or ''
            return (name, code, user.id)
        # Fallback: use the user's partner / login data
        name = (user.partner_id.display_name
                or user.display_name
                or user.login
                or '')
        code = user.login or ''
        return (name, code, user.id)

    @staticmethod
    def _published_courses_domain():
        """Domain for published, active LMS courses shown in the catalog."""
        return [
            ('state', '=', 'published'),
            ('active', '=', True),
        ]

    # ------------------------------------------------------------------
    # Course catalog
    # ------------------------------------------------------------------
    @http.route('/university/lms/courses', type='http', auth='public', website=True)
    def lms_course_list(self, **kwargs):
        """Render the public course catalog page."""
        LmsCourse = request.env['uni.lms.course'].sudo()
        courses = LmsCourse.search(
            self._published_courses_domain(),
            order='academic_term_id desc, code, id',
        )
        values = {
            'courses': courses,
            'page_title': _('Course Catalog'),
        }
        return request.render('university_lms.lms_course_list_page', values)

    # ------------------------------------------------------------------
    # Course detail
    # ------------------------------------------------------------------
    @http.route('/university/lms/course/<int:course_id>', type='http',
                auth='public', website=True)
    def lms_course_detail(self, course_id, **kwargs):
        """Render the course detail page with content outline and metadata."""
        course = request.env['uni.lms.course'].sudo().browse(course_id).exists()
        if not course:
            return request.not_found()
        # Only show published courses to non-authenticated users
        if course.state != 'published' and not request.env.user.has_group(
                'university_core.group_university_user'):
            return request.not_found()
        user = request.env.user
        progress = request.env['uni.lms.progress'].sudo()
        if user and user.id:
            # Lookup by user_id (always available) — this is the canonical
            # way to identify the current user's progress record, since the
            # LMS does not depend on university_student.
            progress = request.env['uni.lms.progress'].sudo().search([
                ('lms_course_id', '=', course.id),
                ('user_id', '=', user.id),
            ], limit=1)
        # First published content item (for the "Start Learning" CTA)
        first_content = course.content_ids.filtered(
            lambda c: c.state == 'published')[:1]
        values = {
            'course': course,
            'progress': progress,
            'is_enrolled': bool(progress),
            'student_name': progress.student_name or '',
            'first_content': first_content,
            'page_title': course.display_name,
        }
        return request.render('university_lms.lms_course_detail_page', values)

    # ------------------------------------------------------------------
    # Enrollment
    # ------------------------------------------------------------------
    @http.route('/university/lms/course/<int:course_id>/enroll', type='http',
                auth='user', website=True)
    def lms_course_enroll(self, course_id, **kwargs):
        """Enroll the current user in the given LMS course.

        - Requires an authenticated Odoo user.
        - If ``university_student`` is installed and the user is linked to
          a student record, the student_name/code are auto-filled from it.
        - Otherwise, the student_name/code are derived from the user's
          display name and login.
        - Verifies enrollment is open and the course is not full.
        - Creates (or reactivates) a ``uni.lms.progress`` record.
        """
        user = request.env.user
        if not user or not user.id:
            return request.redirect('/web/login')

        student_name, student_code, user_id = self._get_or_create_student_identity(user)
        if not student_name:
            # We have no usable identity — show the "no student account" page
            return request.render('university_lms.lms_no_student_account', {
                'page_title': _('No student account'),
            })

        course = request.env['uni.lms.course'].sudo().browse(course_id).exists()
        if not course:
            return request.not_found()
        if course.state != 'published':
            return request.redirect('/university/lms/courses')
        if not course.enrollment_open:
            return request.render('university_lms.lms_enrollment_closed', {
                'course': course,
                'page_title': _('Enrollment closed'),
            })
        if course.max_students > 0 and course.enrolled_count >= course.max_students:
            return request.render('university_lms.lms_enrollment_full', {
                'course': course,
                'page_title': _('Course is full'),
            })

        Progress = request.env['uni.lms.progress'].sudo()
        # Lookup by user_id (canonical) — falls back to student_code if needed
        progress = Progress.search([
            ('lms_course_id', '=', course.id),
            ('user_id', '=', user_id),
        ], limit=1)
        try:
            if progress:
                if progress.state == 'dropped':
                    progress.action_enroll()
                elif progress.state == 'completed':
                    # Allow re-enrollment in completed courses (audit mode)
                    progress.action_reactivate()
                # Keep student_name/code up to date in case they changed
                progress.write({
                    'student_name': student_name,
                    'student_code': student_code,
                })
            else:
                progress = Progress.create({
                    'lms_course_id': course.id,
                    'user_id': user_id,
                    'student_name': student_name,
                    'student_code': student_code,
                    'state': 'enrolled',
                })
        except ValidationError as exc:
            return request.render('university_lms.lms_enrollment_error', {
                'course': course,
                'error_message': str(exc),
                'page_title': _('Enrollment error'),
            })

        return request.redirect(
            '/university/lms/course/%s' % course.id)

    # ------------------------------------------------------------------
    # Content view
    # ------------------------------------------------------------------
    @http.route('/university/lms/course/<int:course_id>/content/<int:content_id>',
                type='http', auth='user', website=True)
    def lms_content_view(self, course_id, content_id, **kwargs):
        """Render a single content item within an LMS course.

        Requires authentication. The user must be enrolled in the course
        (or be a University User) to view the content.
        Increments the content view counter and updates progress last access.
        """
        user = request.env.user
        course = request.env['uni.lms.course'].sudo().browse(course_id).exists()
        content = request.env['uni.lms.content'].sudo().browse(content_id).exists()
        if not course or not content or content.lms_course_id.id != course.id:
            return request.not_found()
        if content.state != 'published':
            return request.not_found()

        progress = request.env['uni.lms.progress'].sudo()
        if user and user.id:
            progress = request.env['uni.lms.progress'].sudo().search([
                ('lms_course_id', '=', course.id),
                ('user_id', '=', user.id),
            ], limit=1)
            # Enforce enrollment (unless user is a University Manager)
            if not progress and not user.has_group(
                    'university_core.group_university_manager'):
                return request.redirect(
                    '/university/lms/course/%s' % course.id)
            # Increment view counter and update progress last access
            content.sudo().action_increment_view()
            if progress:
                progress.sudo().write({
                    'last_access': fields.Datetime.now(),
                    'last_activity': fields.Datetime.now(),
                })
        elif not user.has_group('university_core.group_university_user'):
            return request.redirect('/web/login')

        values = {
            'course': course,
            'content': content,
            'progress': progress,
            'student_name': progress.student_name or '',
            'page_title': content.display_name,
        }
        return request.render('university_lms.lms_content_view_page', values)

    # ------------------------------------------------------------------
    # Student progress dashboard
    # ------------------------------------------------------------------
    @http.route('/university/lms/my/progress', type='http', auth='user', website=True)
    def lms_my_progress(self, **kwargs):
        """Render the user's personal progress dashboard."""
        user = request.env.user
        if not user or not user.id:
            return request.redirect('/web/login')
        # Lookup by user_id (canonical) — works with or without university_student
        progresses = request.env['uni.lms.progress'].sudo().search([
            ('user_id', '=', user.id),
            ('state', '!=', 'dropped'),
        ], order='lms_course_id, id')
        # Aggregate stats
        total_enrolled = len(progresses)
        total_completed = len(progresses.filtered(lambda p: p.state == 'completed'))
        avg_completion = 0.0
        if progresses:
            avg_completion = sum(p.completion_percentage for p in progresses) / len(progresses)
        student_name = ''
        if progresses:
            student_name = progresses[0].student_name or ''
        else:
            student_name, _code, _uid = self._get_or_create_student_identity(user)
        values = {
            'student_name': student_name,
            'progresses': progresses,
            'total_enrolled': total_enrolled,
            'total_completed': total_completed,
            'avg_completion': avg_completion,
            'page_title': _('My Progress'),
        }
        return request.render('university_lms.lms_my_progress_page', values)
