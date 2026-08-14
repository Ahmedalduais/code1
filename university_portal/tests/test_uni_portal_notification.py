# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError
from datetime import timedelta
from odoo.fields import Datetime


@tagged('post_install', '-at_install')
class TestUniPortalNotification(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.env.ref('base.user_admin')
        cls.notification = cls.env['uni.portal.notification'].create({
            'recipient_type': 'all',
            'notification_type': 'info',
            'title': 'Test Notification',
            'message': 'This is a test notification.',
            'priority': 'normal',
            'user_id': cls.user.id,
        })

    def test_create_notification(self):
        self.assertTrue(self.notification)
        self.assertTrue(self.notification.code)
        self.assertTrue(self.notification.name)
        self.assertIn('Test Notification', self.notification.name)

    def test_mark_read(self):
        self.assertFalse(self.notification.is_read)
        self.notification.action_mark_read()
        self.assertTrue(self.notification.is_read)
        self.assertTrue(self.notification.read_date)

    def test_mark_unread(self):
        self.notification.action_mark_read()
        self.notification.action_mark_unread()
        self.assertFalse(self.notification.is_read)
        self.assertFalse(self.notification.read_date)

    def test_notification_type_selection(self):
        for ntype in ('info', 'warning', 'success', 'error', 'announcement',
                       'assignment', 'grade', 'payment', 'event'):
            self.notification.notification_type = ntype
            self.assertEqual(self.notification.notification_type, ntype)

    def test_priority_selection(self):
        for priority in ('low', 'normal', 'high', 'urgent'):
            self.notification.priority = priority
            self.assertEqual(self.notification.priority, priority)

    def test_expiry_date_before_send_date(self):
        with self.assertRaises(ValidationError):
            self.notification.write({
                'send_date': Datetime.now(),
                'expiry_date': Datetime.now() - timedelta(days=1),
            })

    def test_send_notification_student(self):
        notif = self.env['uni.portal.notification'].send_notification(
            'student', 'Hello', 'Test message')
        self.assertTrue(notif)
        self.assertEqual(notif.recipient_type, 'student')
