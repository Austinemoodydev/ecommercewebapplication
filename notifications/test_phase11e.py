from unittest.mock import patch

from django.contrib.auth import (
    get_user_model,
)

from django.test import TestCase

from django.urls import reverse

from notifications.models import (
    Notification,
)

from notifications.tasks import (
    channel_retry_available,
    retry_notification_channel,
)


User = get_user_model()


class Phase11ENotificationOperationsTests(
    TestCase
):

    def setUp(self):

        self.customer = (
            User.objects.create_user(
                username="phase11ecustomer",
                password="pass12345",
                email="phase11e@example.com",
                role=User.CUSTOMER,
            )
        )


        self.staff = (
            User.objects.create_user(
                username="phase11estaff",
                password="pass12345",
                email="staff11e@example.com",
                role=User.ADMIN,
                is_staff=True,
            )
        )


        self.notification = (
            Notification.objects.create(
                user=self.customer,
                order_id=999,
                channel="email_and_sms",
                category="orders",
                event_key="phase11e:test",
                subject="Phase 11E",
                message="Email body",
                sms_message="SMS body",
                status="partial",
                email_status="sent",
                sms_status="failed",
                email_attempts=1,
                sms_attempts=1,
                attempts=2,
                sms_error="Temporary SMS failure",
            )
        )


    def test_staff_can_view_notification_detail(
        self,
    ):

        self.client.login(
            username="phase11estaff",
            password="pass12345",
        )


        response = self.client.get(
            reverse(
                "admin_notification_detail",
                args=[
                    self.notification.pk
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        self.assertContains(
            response,
            "Phase 11E",
        )


    def test_customer_cannot_view_admin_detail(
        self,
    ):

        self.client.login(
            username="phase11ecustomer",
            password="pass12345",
        )


        response = self.client.get(
            reverse(
                "admin_notification_detail",
                args=[
                    self.notification.pk
                ],
            )
        )


        self.assertIn(
            response.status_code,
            [
                302,
                403,
            ],
        )


    def test_retry_limit_blocks_channel(
        self,
    ):

        self.notification.sms_attempts = 3

        self.notification.save(
            update_fields=[
                "sms_attempts",
            ]
        )


        self.assertFalse(
            channel_retry_available(
                self.notification,
                "sms",
            )
        )


    def test_sent_channel_is_not_retryable(
        self,
    ):

        self.assertFalse(
            channel_retry_available(
                self.notification,
                "email",
            )
        )


    @patch(
        "notifications.views.retry_notification_channel.delay"
    )
    def test_admin_can_queue_sms_only_retry(
        self,
        mocked_delay,
    ):

        # View checks only metadata/order_id before queueing,
        # so a real order object is not required for this test.
        self.client.login(
            username="phase11estaff",
            password="pass12345",
        )


        response = self.client.post(
            reverse(
                "admin_retry_notification_channel",
                args=[
                    self.notification.pk,
                    "sms",
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            302,
        )


        mocked_delay.assert_called_once_with(
            self.notification.pk,
            "sms",
        )


    @patch(
        "notifications.views.retry_notification.delay"
    )
    def test_bulk_retry_queues_selected_failure(
        self,
        mocked_delay,
    ):

        self.client.login(
            username="phase11estaff",
            password="pass12345",
        )


        response = self.client.post(
            reverse(
                "admin_bulk_retry_notifications"
            ),
            {
                "notification_ids": [
                    str(
                        self.notification.pk
                    )
                ]
            },
        )


        self.assertEqual(
            response.status_code,
            302,
        )


        mocked_delay.assert_called_once_with(
            self.notification.pk
        )


    @patch(
        "notifications.views.retry_notification.delay"
    )
    def test_bulk_retry_skips_retry_limit(
        self,
        mocked_delay,
    ):

        self.notification.sms_attempts = 3

        self.notification.save(
            update_fields=[
                "sms_attempts",
            ]
        )


        self.client.login(
            username="phase11estaff",
            password="pass12345",
        )


        response = self.client.post(
            reverse(
                "admin_bulk_retry_notifications"
            ),
            {
                "notification_ids": [
                    str(
                        self.notification.pk
                    )
                ]
            },
        )


        self.assertEqual(
            response.status_code,
            302,
        )


        mocked_delay.assert_not_called()
