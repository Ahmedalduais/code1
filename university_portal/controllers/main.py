# -*- coding: utf-8 -*-
from odoo import _, fields, http
from odoo.http import request
from odoo.exceptions import AccessError


class UniversityPortalController(http.Controller):
    """HTTP controllers for the University Portal frontend.

    All routes require ``auth='user'`` and ``website=True`` so they integrate
    with the Odoo website module and reuse the logged-in portal user.
    """

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _get_portal_student(user):
        """Return the ``uni.portal.student`` record linked to ``user`` (if any)."""
        if not user or not user.id:
            return request.env['uni.portal.student']
        return request.env['uni.portal.student'].sudo().search([
            '|', ('portal_user_id', '=', user.id),
            ('user_id', '=', user.id),
        ], limit=1)

    @staticmethod
    def _get_portal_faculty(user):
        """Return the ``uni.portal.faculty`` record linked to ``user`` (if any)."""
        if not user or not user.id:
            return request.env['uni.portal.faculty']
        return request.env['uni.portal.faculty'].sudo().search([
            '|', ('portal_user_id', '=', user.id),
            ('user_id', '=', user.id),
        ], limit=1)

    @staticmethod
    def _get_user_notifications(user, limit=None):
        """Return the notifications visible to ``user``, newest first."""
        if not user or not user.id:
            return request.env['uni.portal.notification']
        domain = [('user_id', '=', user.id)]
        notifications = request.env['uni.portal.notification'].sudo().search(
            domain, order='send_date desc, id desc',
            limit=limit if limit else None,
        )
        return notifications

    @staticmethod
    def _require_portal_account(portal_student=None, portal_faculty=None):
        """Render a friendly "no portal account" page if none is linked."""
        if portal_student or portal_faculty:
            return None
        return request.render('university_portal.portal_no_account', {
            'no_account': True,
        })

    # ------------------------------------------------------------------
    # Student portal
    # ------------------------------------------------------------------
    @http.route('/university/portal/student', type='http', auth='user',
                website=True)
    def portal_student_dashboard(self, **kwargs):
        """Render the student portal dashboard page."""
        user = request.env.user
        portal_student = self._get_portal_student(user)
        no_account_page = self._require_portal_account(
            portal_student=portal_student)
        if no_account_page:
            return no_account_page

        # Update last_login / last_ip for the portal account
        portal_student.sudo().write({
            'last_login': fields.Datetime.now(),
            'last_ip': request.httprequest.remote_addr or False,
        })
        # Increment dashboard access counter
        dashboard = request.env['uni.portal.dashboard'].sudo().get_or_create_for_user(
            user, dashboard_type='student')
        dashboard.action_mark_accessed()

        notifications = self._get_user_notifications(user, limit=10)
        student = portal_student.student_id
        values = {
            'portal_student': portal_student,
            'student': student,
            'notifications': notifications,
            'unread_count': len(notifications.filtered(lambda n: not n.is_read)),
            'dashboard': dashboard,
            'dashboard_data': dashboard.get_dashboard_data(),
            'is_student': True,
            'is_faculty': False,
        }
        return request.render(
            'university_portal.portal_student_dashboard_page', values)

    # ------------------------------------------------------------------
    # Faculty portal
    # ------------------------------------------------------------------
    @http.route('/university/portal/faculty', type='http', auth='user',
                website=True)
    def portal_faculty_dashboard(self, **kwargs):
        """Render the faculty portal dashboard page."""
        user = request.env.user
        portal_faculty = self._get_portal_faculty(user)
        no_account_page = self._require_portal_account(
            portal_faculty=portal_faculty)
        if no_account_page:
            return no_account_page

        # Update last_login / last_ip for the portal account
        portal_faculty.sudo().write({
            'last_login': fields.Datetime.now(),
            'last_ip': request.httprequest.remote_addr or False,
        })
        dashboard = request.env['uni.portal.dashboard'].sudo().get_or_create_for_user(
            user, dashboard_type='faculty')
        dashboard.action_mark_accessed()

        notifications = self._get_user_notifications(user, limit=10)
        faculty = portal_faculty.faculty_id
        values = {
            'portal_faculty': portal_faculty,
            'faculty': faculty,
            'notifications': notifications,
            'unread_count': len(notifications.filtered(lambda n: not n.is_read)),
            'dashboard': dashboard,
            'dashboard_data': dashboard.get_dashboard_data(),
            'is_student': False,
            'is_faculty': True,
        }
        return request.render(
            'university_portal.portal_faculty_dashboard_page', values)

    # ------------------------------------------------------------------
    # Notifications list
    # ------------------------------------------------------------------
    @http.route('/university/portal/notifications', type='http', auth='user',
                website=True)
    def portal_notifications(self, filter='all', **kwargs):
        """Render the notifications page (optionally filtered by read state)."""
        user = request.env.user
        notifications = self._get_user_notifications(user)
        if filter == 'unread':
            notifications = notifications.filtered(lambda n: not n.is_read)
        elif filter == 'read':
            notifications = notifications.filtered(lambda n: n.is_read)
        portal_student = self._get_portal_student(user)
        portal_faculty = self._get_portal_faculty(user)
        values = {
            'notifications': notifications,
            'filter': filter,
            'unread_count': len(self._get_user_notifications(user).filtered(
                lambda n: not n.is_read)),
            'portal_student': portal_student,
            'portal_faculty': portal_faculty,
            'is_student': bool(portal_student),
            'is_faculty': bool(portal_faculty),
        }
        return request.render(
            'university_portal.portal_notifications_page', values)

    # ------------------------------------------------------------------
    # Mark notification as read
    # ------------------------------------------------------------------
    @http.route('/university/portal/notifications/<int:notification_id>/read',
                type='http', auth='user', website=True)
    def portal_notification_mark_read(self, notification_id, **kwargs):
        """Mark a single notification as read and redirect to the action URL."""
        user = request.env.user
        notification = request.env['uni.portal.notification'].sudo().browse(
            notification_id).exists()
        if not notification:
            return request.not_found()
        # Security: only the recipient may mark their own notification as read
        if notification.user_id.id != user.id:
            raise AccessError(_(
                "You are not allowed to access notification %s.")
                % notification_id)
        notification.action_mark_read()
        # Redirect to the action URL if provided, else back to notifications list
        return request.redirect(
            notification.action_url or '/university/portal/notifications')

    # ------------------------------------------------------------------
    # Mark notification as read (JSON endpoint, optional convenience)
    # ------------------------------------------------------------------
    @http.route('/university/portal/notifications/mark_read',
                type='json', auth='user', website=True)
    def portal_notification_mark_read_json(self, notification_id, **kwargs):
        """JSON-RPC variant: mark a notification as read and return its state."""
        user = request.env.user
        notification = request.env['uni.portal.notification'].sudo().browse(
            int(notification_id)).exists()
        if not notification:
            return {'ok': False, 'error': 'not_found'}
        if notification.user_id.id != user.id:
            return {'ok': False, 'error': 'access_denied'}
        notification.action_mark_read()
        return {
            'ok': True,
            'id': notification.id,
            'is_read': notification.is_read,
            'read_date': notification.read_date.isoformat()
            if notification.read_date else False,
        }

    # ------------------------------------------------------------------
    # Dashboard data JSON endpoint
    # ------------------------------------------------------------------
    @http.route('/university/portal/dashboard/data', type='json',
                auth='user', website=True)
    def portal_dashboard_data(self, dashboard_type=None, **kwargs):
        """Return dashboard data for the current user as a JSON dictionary.

        ``dashboard_type`` is optional; if omitted it is inferred from the
        portal account the user is linked to (faculty takes precedence).
        """
        user = request.env.user
        portal_student = self._get_portal_student(user)
        portal_faculty = self._get_portal_faculty(user)
        if not dashboard_type:
            if portal_faculty:
                dashboard_type = 'faculty'
            elif portal_student:
                dashboard_type = 'student'
            elif user.has_group('university_core.group_university_manager'):
                dashboard_type = 'admin'
            else:
                return {'ok': False, 'error': 'no_portal_account'}
        dashboard = request.env['uni.portal.dashboard'].sudo().get_or_create_for_user(
            user, dashboard_type=dashboard_type)
        dashboard.action_mark_accessed()
        return {
            'ok': True,
            'dashboard': dashboard.get_dashboard_data(),
            'portal_student_id': portal_student.id if portal_student else False,
            'portal_faculty_id': portal_faculty.id if portal_faculty else False,
        }
