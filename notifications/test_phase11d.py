from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import (
    get_user_model,
)

from django.test import TestCase

from categories.models import Category

from notifications.models import (
    Notification,
)

from notifications.preference_service import (
    get_notification_preferences,
)

from notifications.tasks import (
    retry_notification,
    send_payment_confirmation,
)

from orders.models import Order

from products.models import Product


User = get_user_model()


class Phase11DDeliveryReliabilityTests(
    TestCase
):

    def setUp(self):

        self.customer = (
            User.objects.create_user(
                username="phase11dcustomer",
                password="pass12345",
                email="phase11d@example.com",
                phone="0712345678",
                role=User.CUSTOMER,
            )
        )


        preferences = (
            get_notification_preferences(
                self.customer
            )
        )

        preferences.email_enabled = True
        preferences.sms_enabled = True
        preferences.payment_updates = True

        preferences.save()


        self.category = (
            Category.objects.create(
                name="Phase 11D",
                slug="phase-11d",
            )
        )


        self.product = (
            Product.objects.create(
                category=self.category,
                name="Phase 11D Product",
                slug="phase-11d-product",
                sku="P11D-001",
                price=Decimal("5000.00"),
                stock=5,
                reserved_stock=0,
                is_active=True,
            )
        )


        self.order = (
            Order.objects.create(
                user=self.customer,
                order_number="PHASE11D-001",
                full_name="Phase 11D Customer",
                phone="0712345678",
                email="phase11d@example.com",
                county="Nairobi",
                city="Nairobi",
                estate="CBD",
                house_number="10",
                subtotal=Decimal("5000.00"),
                shipping_cost=Decimal("500.00"),
                discount=Decimal("0.00"),
                total_amount=Decimal("5500.00"),
                status="confirmed",
                payment_status="paid",
                inventory_status="consumed",
                payment_method="mpesa",
            )
        )


    @patch(
        "notifications.tasks._get_sms_client"
    )
    @patch(
        "notifications.tasks.send_mail"
    )
    def test_both_channels_success(
        self,
        mocked_email,
        mocked_sms_client,
    ):

        mocked_sms_client.return_value.send.return_value = {
            "SMSMessageData": {}
        }


        send_payment_confirmation.run(
            self.order.pk
        )


        notification = (
            Notification.objects.get(
                event_key=(
                    f"payment:"
                    f"{self.order.pk}:confirmed"
                )
            )
        )


        self.assertEqual(
            notification.email_status,
            "sent",
        )

        self.assertEqual(
            notification.sms_status,
            "sent",
        )

        self.assertEqual(
            notification.status,
            "sent",
        )


    @patch(
        "notifications.tasks._get_sms_client"
    )
    @patch(
        "notifications.tasks.send_mail"
    )
    def test_email_success_sms_failure_is_partial(
        self,
        mocked_email,
        mocked_sms_client,
    ):

        mocked_sms_client.return_value.send.side_effect = (
            RuntimeError(
                "SMS provider unavailable"
            )
        )


        send_payment_confirmation.run(
            self.order.pk
        )


        notification = (
            Notification.objects.get(
                event_key=(
                    f"payment:"
                    f"{self.order.pk}:confirmed"
                )
            )
        )


        self.assertEqual(
            notification.email_status,
            "sent",
        )

        self.assertEqual(
            notification.sms_status,
            "failed",
        )

        self.assertEqual(
            notification.status,
            "partial",
        )


    @patch(
        "notifications.tasks._get_sms_client"
    )
    @patch(
        "notifications.tasks.send_mail"
    )
    def test_retry_only_failed_sms_channel(
        self,
        mocked_email,
        mocked_sms_client,
    ):

        mocked_sms_client.return_value.send.side_effect = (
            RuntimeError("SMS down")
        )


        send_payment_confirmation.run(
            self.order.pk
        )


        notification = (
            Notification.objects.get(
                event_key=(
                    f"payment:"
                    f"{self.order.pk}:confirmed"
                )
            )
        )


        self.assertEqual(
            notification.status,
            "partial",
        )


        mocked_email.reset_mock()

        mocked_sms_client.return_value.send.side_effect = None

        mocked_sms_client.return_value.send.return_value = {
            "SMSMessageData": {}
        }


        retry_notification.run(
            notification.pk
        )


        notification.refresh_from_db()


        mocked_email.assert_not_called()


        self.assertEqual(
            notification.email_status,
            "sent",
        )

        self.assertEqual(
            notification.sms_status,
            "sent",
        )

        self.assertEqual(
            notification.status,
            "sent",
        )


    @patch(
        "notifications.tasks._get_sms_client"
    )
    @patch(
        "notifications.tasks.send_mail"
    )
    def test_email_failure_sms_success_is_partial(
        self,
        mocked_email,
        mocked_sms_client,
    ):

        mocked_email.side_effect = (
            RuntimeError(
                "SMTP unavailable"
            )
        )

        mocked_sms_client.return_value.send.return_value = {
            "SMSMessageData": {}
        }


        send_payment_confirmation.run(
            self.order.pk
        )


        notification = (
            Notification.objects.get(
                event_key=(
                    f"payment:"
                    f"{self.order.pk}:confirmed"
                )
            )
        )


        self.assertEqual(
            notification.email_status,
            "failed",
        )

        self.assertEqual(
            notification.sms_status,
            "sent",
        )

        self.assertEqual(
            notification.status,
            "partial",
        )


    @patch(
        "notifications.tasks._get_sms_client"
    )
    @patch(
        "notifications.tasks.send_mail"
    )
    def test_both_fail_overall_failed(
        self,
        mocked_email,
        mocked_sms_client,
    ):

        mocked_email.side_effect = (
            RuntimeError("SMTP down")
        )

        mocked_sms_client.return_value.send.side_effect = (
            RuntimeError("SMS down")
        )


        send_payment_confirmation.run(
            self.order.pk
        )


        notification = (
            Notification.objects.get(
                event_key=(
                    f"payment:"
                    f"{self.order.pk}:confirmed"
                )
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


    @patch(
        "notifications.tasks._get_sms_client"
    )
    @patch(
        "notifications.tasks.send_mail"
    )
    def test_channel_attempt_counts_are_independent(
        self,
        mocked_email,
        mocked_sms_client,
    ):

        mocked_sms_client.return_value.send.side_effect = (
            RuntimeError("SMS down")
        )


        send_payment_confirmation.run(
            self.order.pk
        )


        notification = (
            Notification.objects.get(
                event_key=(
                    f"payment:"
                    f"{self.order.pk}:confirmed"
                )
            )
        )


        self.assertEqual(
            notification.email_attempts,
            1,
        )

        self.assertEqual(
            notification.sms_attempts,
            1,
        )


        mocked_sms_client.return_value.send.side_effect = None

        mocked_sms_client.return_value.send.return_value = {}


        retry_notification.run(
            notification.pk
        )


        notification.refresh_from_db()


        self.assertEqual(
            notification.email_attempts,
            1,
        )

        self.assertEqual(
            notification.sms_attempts,
            2,
        )
