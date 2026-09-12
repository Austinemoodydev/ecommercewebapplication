from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import (
    get_user_model,
)

from django.test import TestCase

from django.urls import reverse

from categories.models import Category

from notifications.models import (
    Notification,
    NotificationPreference,
)

from notifications.preference_service import (
    email_allowed,
    get_notification_preferences,
    sms_allowed,
)

from notifications.tasks import (
    send_payment_confirmation,
)

from orders.models import (
    Order,
)

from products.models import Product


User = get_user_model()


class Phase11CPreferenceTests(
    TestCase
):

    def setUp(self):

        self.customer = (
            User.objects.create_user(
                username="phase11ccustomer",
                password="pass12345",
                email="phase11c@example.com",
                role=User.CUSTOMER,
                email_notifications=True,
                sms_notifications=True,
            )
        )


        self.category = (
            Category.objects.create(
                name="Phase 11C",
                slug="phase-11c",
            )
        )


        self.product = (
            Product.objects.create(
                category=self.category,
                name="Phase 11C Product",
                slug="phase-11c-product",
                sku="P11C-001",
                price=Decimal("5000.00"),
                stock=5,
                reserved_stock=0,
                is_active=True,
            )
        )


        self.order = (
            Order.objects.create(
                user=self.customer,
                order_number="PHASE11C-001",
                full_name="Preference Customer",
                phone="0712345678",
                email="phase11c@example.com",
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


    def test_preferences_created_from_legacy_user_flags(
        self,
    ):

        preferences = (
            get_notification_preferences(
                self.customer
            )
        )


        self.assertTrue(
            preferences.email_enabled
        )

        self.assertTrue(
            preferences.sms_enabled
        )


    def test_customer_can_update_preferences(
        self,
    ):

        self.client.login(
            username="phase11ccustomer",
            password="pass12345",
        )


        response = self.client.post(
            reverse(
                "notification_preferences"
            ),
            {
                "email_enabled": "on",
                "order_updates": "on",
                "delivery_updates": "on",
            },
        )


        self.assertEqual(
            response.status_code,
            302,
        )


        preferences = (
            NotificationPreference.objects.get(
                user=self.customer
            )
        )


        self.assertTrue(
            preferences.email_enabled
        )

        self.assertFalse(
            preferences.sms_enabled
        )

        self.assertFalse(
            preferences.payment_updates
        )

        self.assertFalse(
            preferences.return_refund_updates
        )


    def test_payment_category_can_be_disabled(
        self,
    ):

        preferences = (
            get_notification_preferences(
                self.customer
            )
        )

        preferences.payment_updates = False
        preferences.save()


        self.assertFalse(
            email_allowed(
                self.customer,
                "payments",
            )
        )

        self.assertFalse(
            sms_allowed(
                self.customer,
                "payments",
            )
        )


    def test_marketing_is_opt_in(
        self,
    ):

        preferences = (
            get_notification_preferences(
                self.customer
            )
        )


        self.assertFalse(
            email_allowed(
                self.customer,
                "marketing",
            )
        )

        self.assertFalse(
            sms_allowed(
                self.customer,
                "marketing",
            )
        )


    @patch(
        "notifications.tasks.send_mail"
    )
    def test_disabled_external_channels_still_create_in_app_notification(
        self,
        mocked_send_mail,
    ):

        preferences = (
            get_notification_preferences(
                self.customer
            )
        )

        preferences.email_enabled = False
        preferences.sms_enabled = False
        preferences.save()


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
            notification.category,
            "payments",
        )

        self.assertEqual(
            notification.status,
            "sent",
        )

        mocked_send_mail.assert_not_called()


    @patch(
        "notifications.tasks.send_mail"
    )
    def test_enabled_payment_email_is_sent(
        self,
        mocked_send_mail,
    ):

        preferences = (
            get_notification_preferences(
                self.customer
            )
        )

        preferences.email_enabled = True
        preferences.sms_enabled = False
        preferences.payment_updates = True

        preferences.save()


        send_payment_confirmation.run(
            self.order.pk
        )


        mocked_send_mail.assert_called_once()


        notification = (
            Notification.objects.get(
                event_key=(
                    f"payment:"
                    f"{self.order.pk}:confirmed"
                )
            )
        )


        self.assertEqual(
            notification.category,
            "payments",
        )
