from pathlib import Path
import shutil


ROOT = Path.cwd()

MODELS = ROOT / "notifications" / "models.py"
TASKS = ROOT / "notifications" / "tasks.py"
RETURNS_TASKS = ROOT / "payments" / "returns_tasks.py"
DELIVERY_TASKS = ROOT / "delivery" / "tasks.py"
ORDER_SIGNALS = ROOT / "orders" / "signals.py"

TESTS = ROOT / "notifications" / "test_phase11b.py"


# ============================================================
# VALIDATION
# ============================================================

required = [
    MODELS,
    TASKS,
    RETURNS_TASKS,
    DELIVERY_TASKS,
    ORDER_SIGNALS,
]

for path in required:

    if not path.exists():

        raise RuntimeError(
            f"Missing required file: {path}"
        )


# ============================================================
# BACKUPS
# ============================================================

for path in required:

    backup = Path(
        str(path) + ".phase11bbackup"
    )

    if not backup.exists():

        shutil.copy2(
            path,
            backup,
        )


# ============================================================
# 1. NOTIFICATION MODEL
# ============================================================

text = MODELS.read_text(
    encoding="utf-8-sig"
)


if "event_key = models.CharField" not in text:

    marker = (
        "\tchannel = models.CharField"
        "(max_length=20, default=\"email\")\n"
    )

    replacement = marker + (
        "\tevent_key = models.CharField("
        "max_length=190, null=True, blank=True, "
        "unique=True, db_index=True)\n"
    )

    if marker not in text:

        marker = (
            '    channel = models.CharField('
            'max_length=20, default="email")\n'
        )

        replacement = marker + (
            "    event_key = models.CharField("
            "max_length=190, null=True, blank=True, "
            "unique=True, db_index=True)\n"
        )

    if marker not in text:

        raise RuntimeError(
            "Could not locate Notification.channel."
        )

    text = text.replace(
        marker,
        replacement,
        1,
    )


if "sms_message = models.TextField" not in text:

    marker = "\tmessage = models.TextField()\n"

    replacement = (
        marker
        + "\tsms_message = models.TextField(blank=True)\n"
    )

    if marker not in text:

        marker = "    message = models.TextField()\n"

        replacement = (
            marker
            + "    sms_message = models.TextField(blank=True)\n"
        )

    if marker not in text:

        raise RuntimeError(
            "Could not locate Notification.message."
        )

    text = text.replace(
        marker,
        replacement,
        1,
    )


MODELS.write_text(
    text,
    encoding="utf-8",
)

print(
    "Notification idempotency fields added."
)


# ============================================================
# 2. REBUILD NOTIFICATION TASK PIPELINE
# ============================================================

TASKS.write_text(
r'''
from celery import shared_task

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone


# ============================================================
# PROVIDERS
# ============================================================

def _get_sms_client():

    """
    Initialise Africa's Talking only inside the worker.
    """

    if (
        not settings.AFRICASTALKING_USERNAME
        or
        not settings.AFRICASTALKING_API_KEY
    ):

        raise RuntimeError(
            "Africa's Talking SMS credentials "
            "are not configured"
        )


    import africastalking


    africastalking.initialize(
        settings.AFRICASTALKING_USERNAME,
        settings.AFRICASTALKING_API_KEY,
    )


    return africastalking.SMS


def _normalise_phone(
    phone_number,
):

    phone_number = (
        phone_number
        .strip()
        .replace(" ", "")
    )


    if phone_number.startswith("0"):

        return (
            f"+254{phone_number[1:]}"
        )


    if phone_number.startswith("254"):

        return (
            f"+{phone_number}"
        )


    return phone_number


# ============================================================
# DELIVERY ENGINE
# ============================================================

def _deliver_notification_record(
    notification,
):

    """
    Deliver ONE existing Notification row.

    This function NEVER creates another Notification.

    That distinction is critical for retries.
    """

    from orders.models import Order


    order = None


    if notification.order_id:

        order = (
            Order.objects
            .select_related(
                "user"
            )
            .filter(
                pk=notification.order_id
            )
            .first()
        )


    if order is None:

        raise RuntimeError(
            "Notification is not linked to "
            "an existing order."
        )


    notification.status = "pending"
    notification.last_error = ""

    notification.save(
        update_fields=[
            "status",
            "last_error",
            "updated_at",
        ]
    )


    try:

        wants_sms = (
            notification.channel
            in {
                "sms",
                "email_and_sms",
            }
        )


        wants_email = (
            notification.channel
            in {
                "email",
                "email_and_sms",
            }
        )


        # ----------------------------------------------------
        # SMS
        # ----------------------------------------------------

        if (
            wants_sms
            and order.phone
            and order.user.sms_notifications
        ):

            sms_text = (
                notification.sms_message
                or notification.message
            )


            _get_sms_client().send(
                sms_text,
                [
                    _normalise_phone(
                        order.phone
                    )
                ],
            )


        # ----------------------------------------------------
        # EMAIL
        # ----------------------------------------------------

        if (
            wants_email
            and order.email
            and order.user.email_notifications
        ):

            send_mail(
                subject=notification.subject,
                message=notification.message,
                from_email=(
                    settings.DEFAULT_FROM_EMAIL
                ),
                recipient_list=[
                    order.email
                ],
                fail_silently=False,
            )


    except Exception as exc:

        notification.status = "failed"

        notification.attempts += 1

        notification.last_error = (
            str(exc)[:2000]
        )


        notification.save(
            update_fields=[
                "status",
                "attempts",
                "last_error",
                "updated_at",
            ]
        )


        raise


    notification.status = "sent"

    notification.attempts += 1

    notification.last_error = ""

    notification.sent_at = timezone.now()


    notification.save(
        update_fields=[
            "status",
            "attempts",
            "last_error",
            "sent_at",
            "updated_at",
        ]
    )


    return notification


# ============================================================
# CREATE OR REUSE EVENT
# ============================================================

def _send_order_notifications(
    order,
    sms_message,
    subject,
    email_message,
    *,
    event_key=None,
    channel="email_and_sms",
):

    """
    Create a notification for a business event, or reuse
    the existing row when the same event is delivered again.

    event_key=None preserves compatibility with older callers.
    """

    from .models import Notification


    defaults = {
        "user": order.user,
        "order_id": order.id,
        "channel": channel,
        "subject": (
            f"{subject} — "
            f"{order.order_number}"
        ),
        "message": email_message,
        "sms_message": sms_message,
    }


    if event_key:

        notification, created = (
            Notification.objects.get_or_create(
                event_key=event_key,
                defaults=defaults,
            )
        )


        # A completed event must not be resent simply because
        # Celery or an external callback executed twice.
        if (
            not created
            and notification.status == "sent"
        ):

            return notification


        # Failed or pending row: retry the SAME record.
        return _deliver_notification_record(
            notification
        )


    notification = (
        Notification.objects.create(
            **defaults
        )
    )


    return _deliver_notification_record(
        notification
    )


# ============================================================
# PAYMENT
# ============================================================

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={
        "max_retries": 3,
    },
)
def send_payment_confirmation(
    self,
    order_id,
):

    from orders.models import Order


    order = (
        Order.objects
        .select_related("user")
        .get(
            id=order_id
        )
    )


    _send_order_notifications(
        order,

        (
            f"Order {order.order_number}: "
            f"payment received "
            f"(KES {order.total_amount}). "
            f"Awaiting shipment."
        ),

        "Payment received",

        (
            f"Hi {order.full_name},\n\n"
            f"Payment received for order "
            f"{order.order_number} "
            f"(KES {order.total_amount}). "
            f"Your order is awaiting shipment."
        ),

        event_key=(
            f"payment:"
            f"{order.pk}:confirmed"
        ),
    )


# ============================================================
# LEGACY DELIVERY
# ============================================================

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={
        "max_retries": 3,
    },
)
def send_delivery_notification(
    self,
    order_id,
):

    from orders.models import Order


    order = (
        Order.objects
        .select_related("user")
        .get(
            id=order_id
        )
    )


    _send_order_notifications(
        order,

        (
            f"Order {order.order_number} "
            f"has been delivered. "
            f"Thank you for shopping with us."
        ),

        "Order delivered",

        (
            f"Hi {order.full_name},\n\n"
            f"Order {order.order_number} "
            f"has been delivered. "
            f"Thank you for shopping with us."
        ),

        event_key=(
            f"order:"
            f"{order.pk}:delivered"
        ),
    )


# ============================================================
# ORDER STATUS
# ============================================================

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={
        "max_retries": 3,
    },
)
def send_order_status_notification(
    self,
    order_id,
):

    from orders.models import Order


    order = (
        Order.objects
        .select_related("user")
        .get(
            id=order_id
        )
    )


    status_label = (
        order.get_status_display()
    )


    _send_order_notifications(
        order,

        (
            f"Order {order.order_number} "
            f"update: {status_label}."
        ),

        f"Order {status_label}",

        (
            f"Hi {order.full_name},\n\n"
            f"Your order "
            f"{order.order_number} "
            f"is now "
            f"{status_label.lower()}."
        ),

        event_key=(
            f"order:"
            f"{order.pk}:status:"
            f"{order.status}"
        ),
    )


# ============================================================
# CREDIT NOTE ISSUED
# ============================================================

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={
        "max_retries": 3,
    },
)
def send_credit_note_issued_notification(
    self,
    document_id,
):

    from orders.models import (
        CreditNoteDocument,
    )


    document = (
        CreditNoteDocument.objects
        .select_related(
            "order",
            "order__user",
            "refund_request",
        )
        .get(
            pk=document_id
        )
    )


    order = document.order

    refund = document.refund_request


    _send_order_notifications(
        order,

        (
            f"Order {order.order_number}: "
            f"refund of KES "
            f"{refund.amount:.2f} processed. "
            f"Credit note "
            f"{document.document_number} issued."
        ),

        "Refund credit note issued",

        (
            f"Hi {order.full_name},\n\n"
            f"Your refund for order "
            f"{order.order_number} "
            f"has been processed.\n\n"
            f"Refund amount: "
            f"KES {refund.amount:.2f}\n"
            f"Refund reference: "
            f"{refund.external_reference}\n"
            f"Credit note: "
            f"{document.document_number}\n\n"
            f"You can sign in to your account "
            f"to view the credit note."
        ),

        event_key=(
            f"credit-note:"
            f"{document.pk}:issued"
        ),
    )


# ============================================================
# MANUAL RETRY
# ============================================================

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={
        "max_retries": 3,
    },
)
def retry_notification(
    self,
    notification_id,
):

    from .models import Notification


    notification = (
        Notification.objects
        .select_related(
            "user"
        )
        .get(
            id=notification_id
        )
    )


    # Retry the same row.
    # NEVER call _send_order_notifications() here.
    return _deliver_notification_record(
        notification
    )
'''.strip() + "\n",
encoding="utf-8",
)

print(
    "Notification delivery pipeline hardened."
)


# ============================================================
# 3. RETURN + REFUND EVENT KEYS
# ============================================================

text = RETURNS_TASKS.read_text(
    encoding="utf-8-sig"
)


old = '''    _send_order_notifications(
        order,
        sms,
        (
            f"{obj.get_request_type_display()} "
            f"request update"
        ),
        email,
    )
'''


new = '''    _send_order_notifications(
        order,
        sms,
        (
            f"{obj.get_request_type_display()} "
            f"request update"
        ),
        email,
        event_key=(
            f"return:"
            f"{obj.pk}:"
            f"{obj.status}"
        ),
    )
'''


if old in text:

    text = text.replace(
        old,
        new,
        1,
    )

elif "f\"return:\"" not in text:

    raise RuntimeError(
        "Could not patch return notification."
    )


old = '''    _send_order_notifications(
        order,
        sms,
        "Refund request update",
        email,
    )
'''


new = '''    _send_order_notifications(
        order,
        sms,
        "Refund request update",
        email,
        event_key=(
            f"refund:"
            f"{obj.pk}:"
            f"{obj.status}"
        ),
    )
'''


if old in text:

    text = text.replace(
        old,
        new,
        1,
    )

elif "f\"refund:\"" not in text:

    raise RuntimeError(
        "Could not patch refund notification."
    )


RETURNS_TASKS.write_text(
    text,
    encoding="utf-8",
)

print(
    "Return/refund notifications made idempotent."
)


# ============================================================
# 4. DELIVERY EVENT KEYS
# ============================================================

text = DELIVERY_TASKS.read_text(
    encoding="utf-8-sig"
)


old = '''    _send_order_notifications(
        order,
        sms,
        f"Delivery update: {status_label}",
        email_message,
    )
'''


new = '''    _send_order_notifications(
        order,
        sms,
        f"Delivery update: {status_label}",
        email_message,
        event_key=(
            f"delivery:"
            f"{delivery.pk}:"
            f"{delivery.status}"
        ),
    )
'''


if old in text:

    text = text.replace(
        old,
        new,
        1,
    )

elif 'f"delivery:"' not in text:

    raise RuntimeError(
        "Could not patch delivery status notification."
    )


old = '''    _send_order_notifications(
        order,
        sms,
        "Your delivery quote is ready",
        email_message,
    )
'''


new = '''    _send_order_notifications(
        order,
        sms,
        "Your delivery quote is ready",
        email_message,
        event_key=(
            f"delivery-quote:"
            f"{order.pk}:"
            f"{order.shipping_cost}:"
            f"{order.total_amount}"
        ),
    )
'''


if old in text:

    text = text.replace(
        old,
        new,
        1,
    )

elif 'f"delivery-quote:"' not in text:

    raise RuntimeError(
        "Could not patch delivery quote notification."
    )


DELIVERY_TASKS.write_text(
    text,
    encoding="utf-8",
)

print(
    "Delivery notifications made idempotent."
)


# ============================================================
# 5. CREDIT NOTE ISSUANCE EVENT
# ============================================================

text = ORDER_SIGNALS.read_text(
    encoding="utf-8-sig"
)


if "from django.db import transaction" not in text:

    text = (
        "from django.db import transaction\n"
        + text
    )


old = '''    get_or_issue_credit_note(
        refund=instance,
        issued_by=instance.processed_by,
    )
'''


new = '''    from orders.models import (
        CreditNoteDocument,
    )


    existed_before = (
        CreditNoteDocument.objects
        .filter(
            refund_request=instance
        )
        .exists()
    )


    document = get_or_issue_credit_note(
        refund=instance,
        issued_by=instance.processed_by,
    )


    # Only the first successful issuance creates the
    # "credit note issued" notification event.
    if not existed_before:

        def queue_credit_note_notification():

            try:

                from notifications.tasks import (
                    send_credit_note_issued_notification,
                )


                send_credit_note_issued_notification.delay(
                    document.pk
                )

            except Exception:

                # Broker problems must never roll back or
                # invalidate an already processed refund.
                pass


        transaction.on_commit(
            queue_credit_note_notification,
            robust=True,
        )
'''


if old in text:

    text = text.replace(
        old,
        new,
        1,
    )

elif (
    "send_credit_note_issued_notification"
    not in text
):

    raise RuntimeError(
        "Could not patch credit-note signal."
    )


ORDER_SIGNALS.write_text(
    text,
    encoding="utf-8",
)

print(
    "Credit-note issuance notification added."
)


# ============================================================
# 6. TESTS
# ============================================================

TESTS.write_text(
r'''
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
'''.strip() + "\n",
encoding="utf-8",
)

print(
    "Phase 11B tests created."
)


print()
print("=" * 72)
print("PHASE 11B INSTALLED")
print("=" * 72)
print()
print("Added:")
print("  Event idempotency keys")
print("  Persistent SMS payload")
print("  Retry same notification row")
print("  Duplicate callback protection")
print("  Payment event notifications")
print("  Order-status event notifications")
print("  Delivery-status event notifications")
print("  Delivery-quote event notifications")
print("  Return event notifications")
print("  Refund event notifications")
print("  Credit-note-issued notification")
print()
print("Migration required.")
