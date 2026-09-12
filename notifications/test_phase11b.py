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

from notifications.tasks import (
    retry_notification,
    send_payment_confirmation,
)

from orders.models import (
    Order,
    OrderItem,
)

from payments.models import (
    RefundRequest,
)

from payments.returns_tasks import (
    send_refund_status_notification,
)

from products.models import Product


User = get_user_model()


class Phase11BNotificationEventTests(
    TestCase
):

    def setUp(self):

        self.customer = (
            User.objects.create_user(
                username="phase11bcustomer",
                password="pass12345",
                email="phase11b@example.com",
                role=User.CUSTOMER,
            )
        )


        # Do not call external providers in these
        # event/idempotency tests.
        self.customer.email_notifications = False
        self.customer.sms_notifications = False

        self.customer.save(
            update_fields=[
                "email_notifications",
                "sms_notifications",
            ]
        )


        self.staff = (
            User.objects.create_user(
                username="phase11bstaff",
                password="pass12345",
                role=User.ADMIN,
                is_staff=True,
            )
        )


        self.category = (
            Category.objects.create(
                name="Phase 11B",
                slug="phase-11b",
            )
        )


        self.product = (
            Product.objects.create(
                category=self.category,
                name="Phase 11B Product",
                slug="phase-11b-product",
                sku="P11B-001",
                price=Decimal(
                    "10000.00"
                ),
                cost_price=Decimal(
                    "7000.00"
                ),
                stock=10,
                reserved_stock=0,
                is_active=True,
            )
        )


        self.order = (
            Order.objects.create(
                user=self.customer,
                order_number="PHASE11B-001",
                full_name="Phase 11B Customer",
                phone="0712345678",
                email="phase11b@example.com",
                county="Nairobi",
                city="Nairobi",
                estate="CBD",
                house_number="10",
                subtotal=Decimal(
                    "10000.00"
                ),
                shipping_cost=Decimal(
                    "500.00"
                ),
                discount=Decimal(
                    "0.00"
                ),
                total_amount=Decimal(
                    "10500.00"
                ),
                status="confirmed",
                payment_status="paid",
                inventory_status="consumed",
                payment_method="mpesa",
            )
        )


        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            product_name=(
                "Phase 11B Product"
            ),
            price=Decimal(
                "10000.00"
            ),
            unit_cost_at_sale=Decimal(
                "7000.00"
            ),
            cost_subtotal_at_sale=Decimal(
                "7000.00"
            ),
            quantity=1,
            subtotal=Decimal(
                "10000.00"
            ),
        )


    def test_payment_event_is_idempotent(
        self
    ):

        send_payment_confirmation.run(
            self.order.pk
        )

        send_payment_confirmation.run(
            self.order.pk
        )


        queryset = (
            Notification.objects
            .filter(
                event_key=(
                    f"payment:"
                    f"{self.order.pk}:confirmed"
                )
            )
        )


        self.assertEqual(
            queryset.count(),
            1,
        )


        notification = queryset.get()


        self.assertEqual(
            notification.status,
            "sent",
        )


        self.assertEqual(
            notification.attempts,
            1,
        )


    def test_different_events_get_different_rows(
        self
    ):

        send_payment_confirmation.run(
            self.order.pk
        )


        refund = (
            RefundRequest.objects.create(
                order=self.order,
                amount=Decimal(
                    "1000.00"
                ),
                reason="Phase 11B refund",
                status="approved",
                processed_by=self.staff,
            )
        )


        send_refund_status_notification.run(
            refund.pk
        )


        self.assertEqual(
            Notification.objects.count(),
            2,
        )


        self.assertTrue(
            Notification.objects.filter(
                event_key=(
                    f"payment:"
                    f"{self.order.pk}:confirmed"
                )
            ).exists()
        )


        self.assertTrue(
            Notification.objects.filter(
                event_key=(
                    f"refund:"
                    f"{refund.pk}:approved"
                )
            ).exists()
        )


    def test_refund_same_status_is_idempotent(
        self
    ):

        refund = (
            RefundRequest.objects.create(
                order=self.order,
                amount=Decimal(
                    "1000.00"
                ),
                reason="Duplicate event test",
                status="approved",
                processed_by=self.staff,
            )
        )


        send_refund_status_notification.run(
            refund.pk
        )

        send_refund_status_notification.run(
            refund.pk
        )


        self.assertEqual(
            Notification.objects.filter(
                event_key=(
                    f"refund:"
                    f"{refund.pk}:approved"
                )
            ).count(),
            1,
        )


    def test_manual_retry_reuses_same_row(
        self
    ):

        notification = (
            Notification.objects.create(
                user=self.customer,
                order_id=self.order.pk,
                channel="email_and_sms",
                event_key="test:manual-retry",
                subject=(
                    "Retry test — "
                    f"{self.order.order_number}"
                ),
                message="Retry email message",
                sms_message="Retry SMS",
                status="failed",
                attempts=1,
                last_error="Temporary failure",
            )
        )


        retry_notification.run(
            notification.pk
        )


        self.assertEqual(
            Notification.objects.filter(
                event_key="test:manual-retry"
            ).count(),
            1,
        )


        notification.refresh_from_db()


        self.assertEqual(
            notification.status,
            "sent",
        )


        self.assertEqual(
            notification.attempts,
            2,
        )


        self.assertEqual(
            notification.last_error,
            "",
        )


    @patch(
        "notifications.tasks.send_mail"
    )
    def test_provider_failure_marks_same_row_failed(
        self,
        mocked_send_mail,
    ):

        self.customer.email_notifications = True
        self.customer.sms_notifications = False

        self.customer.save(
            update_fields=[
                "email_notifications",
                "sms_notifications",
            ]
        )


        mocked_send_mail.side_effect = (
            RuntimeError(
                "SMTP unavailable"
            )
        )


        with self.assertRaises(
            RuntimeError
        ):

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
            notification.attempts,
            1,
        )


        self.assertIn(
            "SMTP unavailable",
            notification.last_error,
        )


    def test_null_event_key_keeps_legacy_compatibility(
        self
    ):

        first = (
            Notification.objects.create(
                user=self.customer,
                subject="Legacy one",
                message="One",
            )
        )

        second = (
            Notification.objects.create(
                user=self.customer,
                subject="Legacy two",
                message="Two",
            )
        )


        self.assertIsNone(
            first.event_key
        )

        self.assertIsNone(
            second.event_key
        )


        self.assertEqual(
            Notification.objects
            .filter(
                event_key__isnull=True
            )
            .count(),
            2,
        )
