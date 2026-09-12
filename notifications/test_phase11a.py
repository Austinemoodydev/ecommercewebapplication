from unittest.mock import patch

from django.contrib.auth import (
    get_user_model,
)

from django.test import TestCase

from django.urls import reverse

from notifications.models import (
    Notification,
)


User = get_user_model()


class Phase11ANotificationCenterTests(
    TestCase
):

    def setUp(self):

        self.customer = (
            User.objects.create_user(
                username="phase11customer",
                password="pass12345",
                email="phase11@example.com",
                role=User.CUSTOMER,
            )
        )


        self.other = (
            User.objects.create_user(
                username="phase11other",
                password="pass12345",
                role=User.CUSTOMER,
            )
        )


        self.staff = (
            User.objects.create_user(
                username="phase11staff",
                password="pass12345",
                role=User.ADMIN,
                is_staff=True,
            )
        )


        self.notification = (
            Notification.objects.create(
                user=self.customer,
                order_id=101,
                channel="email",
                subject="Order shipped",
                message=(
                    "Your order has been shipped."
                ),
                status="sent",
            )
        )


    def test_customer_sees_own_notification(
        self
    ):

        self.client.login(
            username="phase11customer",
            password="pass12345",
        )


        response = self.client.get(
            reverse(
                "customer_notifications"
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        self.assertContains(
            response,
            "Order shipped",
        )


    def test_customer_does_not_see_another_users_notification(
        self
    ):

        Notification.objects.create(
            user=self.other,
            subject="Private notification",
            message="Other customer only.",
            status="sent",
        )


        self.client.login(
            username="phase11customer",
            password="pass12345",
        )


        response = self.client.get(
            reverse(
                "customer_notifications"
            )
        )


        self.assertNotContains(
            response,
            "Private notification",
        )


    def test_customer_can_mark_notification_read(
        self
    ):

        self.client.login(
            username="phase11customer",
            password="pass12345",
        )


        response = self.client.post(
            reverse(
                "customer_notification_mark_read",
                args=[
                    self.notification.pk
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            302,
        )


        self.notification.refresh_from_db()


        self.assertIsNotNone(
            self.notification.read_at
        )


    def test_customer_cannot_mark_other_notification_read(
        self
    ):

        other_notification = (
            Notification.objects.create(
                user=self.other,
                subject="Other",
                message="Other",
                status="sent",
            )
        )


        self.client.login(
            username="phase11customer",
            password="pass12345",
        )


        response = self.client.post(
            reverse(
                "customer_notification_mark_read",
                args=[
                    other_notification.pk
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            404,
        )


    def test_staff_can_view_admin_notification_center(
        self
    ):

        self.client.login(
            username="phase11staff",
            password="pass12345",
        )


        response = self.client.get(
            reverse(
                "admin_notifications"
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        self.assertContains(
            response,
            "Order shipped",
        )


    @patch(
        "notifications.views.retry_notification.delay"
    )
    def test_staff_can_queue_failed_notification_retry(
        self,
        mocked_delay,
    ):

        failed = (
            Notification.objects.create(
                user=self.customer,
                order_id=200,
                subject="Payment received",
                message="Payment notification.",
                status="failed",
                last_error="SMTP unavailable",
            )
        )


        self.client.login(
            username="phase11staff",
            password="pass12345",
        )


        response = self.client.post(
            reverse(
                "admin_retry_notification",
                args=[
                    failed.pk
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            302,
        )


        mocked_delay.assert_called_once_with(
            failed.pk
        )
