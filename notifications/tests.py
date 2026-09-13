from unittest.mock import patch

from django.test import TestCase

from accounts.models import CustomUser

from notifications.models import Notification

from notifications.tasks import (
    send_order_status_notification,
)

from orders.models import Order


class NotificationTests(TestCase):

    @patch(
        "notifications.tasks._get_sms_client"
    )
    @patch(
        "notifications.tasks.send_mail"
    )
    def test_failed_delivery_is_recorded(
        self,
        mocked_send_mail,
        mocked_sms_client,
    ):

        user = (
            CustomUser.objects.create_user(
                username="notify-user",
                email="notify@example.com",
            )
        )


        order = (
            Order.objects.create(
                user=user,
                order_number="ORDER-NOTIFY",
                full_name="Notify User",
                email="notify@example.com",
                phone="0712345678",
                county="Nairobi",
                city="Nairobi",
                estate="Estate",
                house_number="1",
                subtotal=10,
                total_amount=10,
                status="shipped",
            )
        )


        mocked_send_mail.side_effect = (
            RuntimeError(
                "SMTP unavailable"
            )
        )


        mocked_sms_client.return_value.send.side_effect = (
            RuntimeError(
                "SMS unavailable"
            )
        )


        # Phase 11D records provider errors rather
        # than propagating them to the business event.
        send_order_status_notification.run(
            order.id
        )


        notification = (
            Notification.objects.get(
                order_id=order.id
            )
        )


        self.assertEqual(
            notification.status,
            "failed",
        )


        self.assertEqual(
            notification.email_status,
            "failed",
        )


        self.assertEqual(
            notification.sms_status,
            "failed",
        )


        self.assertEqual(
            notification.email_attempts,
            1,
        )


        self.assertEqual(
            notification.sms_attempts,
            1,
        )


        self.assertEqual(
            notification.attempts,
            2,
        )


        self.assertIn(
            "SMTP unavailable",
            notification.email_error,
        )


        self.assertIn(
            "SMS unavailable",
            notification.sms_error,
        )
