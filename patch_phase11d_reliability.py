from pathlib import Path
import shutil


ROOT = Path.cwd()

MODELS = ROOT / "notifications" / "models.py"
TASKS = ROOT / "notifications" / "tasks.py"
VIEWS = ROOT / "notifications" / "views.py"
ADMIN_TEMPLATE = (
    ROOT
    / "templates"
    / "notifications"
    / "admin_list.html"
)
TESTS = (
    ROOT
    / "notifications"
    / "test_phase11d.py"
)


required = [
    MODELS,
    TASKS,
    VIEWS,
    ADMIN_TEMPLATE,
]

for path in required:
    if not path.exists():
        raise RuntimeError(
            f"Missing required file: {path}"
        )


for path in required:

    backup = Path(
        str(path) + ".phase11dbackup"
    )

    if not backup.exists():
        shutil.copy2(
            path,
            backup,
        )


# ============================================================
# 1. MODEL
# ============================================================

text = MODELS.read_text(
    encoding="utf-8-sig"
)


# Add partial overall status
text = text.replace(
    '''        ("failed", "Failed"),
    ]
''',
    '''        ("failed", "Failed"),
        ("partial", "Partially Delivered"),
    ]

    CHANNEL_STATUS_CHOICES = [
        ("not_requested", "Not Requested"),
        ("pending", "Pending"),
        ("sent", "Sent"),
        ("failed", "Failed"),
        ("skipped", "Skipped"),
    ]
''',
    1,
)


if "email_status = models.CharField" not in text:

    marker = '''    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )
'''

    addition = marker + '''

    email_status = models.CharField(
        max_length=20,
        choices=CHANNEL_STATUS_CHOICES,
        default="not_requested",
        db_index=True,
    )

    sms_status = models.CharField(
        max_length=20,
        choices=CHANNEL_STATUS_CHOICES,
        default="not_requested",
        db_index=True,
    )

    email_attempts = models.PositiveIntegerField(
        default=0,
    )

    sms_attempts = models.PositiveIntegerField(
        default=0,
    )

    email_sent_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    sms_sent_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    email_error = models.TextField(
        blank=True,
    )

    sms_error = models.TextField(
        blank=True,
    )
'''

    if marker not in text:
        raise RuntimeError(
            "Could not locate Notification.status field."
        )

    text = text.replace(
        marker,
        addition,
        1,
    )


MODELS.write_text(
    text,
    encoding="utf-8",
)

print(
    "Per-channel notification delivery fields added."
)


# ============================================================
# 2. REBUILD TASK DELIVERY ENGINE
# ============================================================

TASKS.write_text(
r'''
from celery import shared_task

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from notifications.preference_service import (
    email_allowed,
    sms_allowed,
)


# ============================================================
# PROVIDERS
# ============================================================

def _get_sms_client():

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
# STATUS HELPERS
# ============================================================

def _requested_channels(
    notification,
):

    if notification.channel == "email":
        return {"email"}

    if notification.channel == "sms":
        return {"sms"}

    if notification.channel == "email_and_sms":
        return {
            "email",
            "sms",
        }

    return set()


def _calculate_overall_status(
    notification,
):

    statuses = []


    for channel in _requested_channels(
        notification
    ):

        value = getattr(
            notification,
            f"{channel}_status",
        )


        if value not in {
            "not_requested",
            "skipped",
        }:
            statuses.append(
                value
            )


    # Nothing externally deliverable.
    # In-app notification still exists successfully.
    if not statuses:
        return "sent"


    if all(
        status == "sent"
        for status in statuses
    ):
        return "sent"


    if any(
        status == "failed"
        for status in statuses
    ):

        if any(
            status == "sent"
            for status in statuses
        ):
            return "partial"

        return "failed"


    return "pending"


def _save_overall_status(
    notification,
):

    notification.status = (
        _calculate_overall_status(
            notification
        )
    )


    if notification.status == "sent":
        notification.sent_at = (
            notification.sent_at
            or timezone.now()
        )


    notification.last_error = (
        notification.email_error
        or notification.sms_error
        or ""
    )


    notification.save(
        update_fields=[
            "status",
            "sent_at",
            "last_error",
            "updated_at",
        ]
    )


# ============================================================
# CHANNEL DELIVERY
# ============================================================

def _deliver_email(
    notification,
    order,
):

    notification.email_attempts += 1
    notification.email_status = "pending"
    notification.email_error = ""

    notification.save(
        update_fields=[
            "email_attempts",
            "email_status",
            "email_error",
            "updated_at",
        ]
    )


    try:

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

        notification.email_status = "failed"

        notification.email_error = (
            str(exc)[:2000]
        )

        notification.save(
            update_fields=[
                "email_status",
                "email_error",
                "updated_at",
            ]
        )

        return False


    notification.email_status = "sent"
    notification.email_error = ""
    notification.email_sent_at = (
        timezone.now()
    )

    notification.save(
        update_fields=[
            "email_status",
            "email_error",
            "email_sent_at",
            "updated_at",
        ]
    )

    return True


def _deliver_sms(
    notification,
    order,
):

    notification.sms_attempts += 1
    notification.sms_status = "pending"
    notification.sms_error = ""

    notification.save(
        update_fields=[
            "sms_attempts",
            "sms_status",
            "sms_error",
            "updated_at",
        ]
    )


    try:

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


    except Exception as exc:

        notification.sms_status = "failed"

        notification.sms_error = (
            str(exc)[:2000]
        )

        notification.save(
            update_fields=[
                "sms_status",
                "sms_error",
                "updated_at",
            ]
        )

        return False


    notification.sms_status = "sent"
    notification.sms_error = ""
    notification.sms_sent_at = (
        timezone.now()
    )

    notification.save(
        update_fields=[
            "sms_status",
            "sms_error",
            "sms_sent_at",
            "updated_at",
        ]
    )

    return True


# ============================================================
# DELIVERY ENGINE
# ============================================================

def _deliver_notification_record(
    notification,
    channels=None,
):

    from orders.models import Order


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
            "Notification is not linked "
            "to an existing order."
        )


    requested = (
        set(channels)
        if channels is not None
        else _requested_channels(
            notification
        )
    )


    # --------------------------------------------------------
    # EMAIL
    # --------------------------------------------------------

    if "email" in requested:

        if not order.email:

            notification.email_status = (
                "skipped"
            )

            notification.email_error = (
                "Order has no email address."
            )

            notification.save(
                update_fields=[
                    "email_status",
                    "email_error",
                    "updated_at",
                ]
            )


        elif not email_allowed(
            order.user,
            notification.category,
        ):

            notification.email_status = (
                "skipped"
            )

            notification.email_error = ""

            notification.save(
                update_fields=[
                    "email_status",
                    "email_error",
                    "updated_at",
                ]
            )


        elif (
            notification.email_status
            != "sent"
        ):

            _deliver_email(
                notification,
                order,
            )


    # --------------------------------------------------------
    # SMS
    # --------------------------------------------------------

    if "sms" in requested:

        if not order.phone:

            notification.sms_status = (
                "skipped"
            )

            notification.sms_error = (
                "Order has no phone number."
            )

            notification.save(
                update_fields=[
                    "sms_status",
                    "sms_error",
                    "updated_at",
                ]
            )


        elif not sms_allowed(
            order.user,
            notification.category,
        ):

            notification.sms_status = (
                "skipped"
            )

            notification.sms_error = ""

            notification.save(
                update_fields=[
                    "sms_status",
                    "sms_error",
                    "updated_at",
                ]
            )


        elif (
            notification.sms_status
            != "sent"
        ):

            _deliver_sms(
                notification,
                order,
            )


    notification.attempts = (
        notification.email_attempts
        + notification.sms_attempts
    )

    notification.save(
        update_fields=[
            "attempts",
            "updated_at",
        ]
    )


    _save_overall_status(
        notification
    )


    notification.refresh_from_db()

    return notification


# ============================================================
# CREATE / REUSE BUSINESS EVENT
# ============================================================

def _send_order_notifications(
    order,
    sms_message,
    subject,
    email_message,
    *,
    event_key=None,
    channel="email_and_sms",
    category="general",
):

    from .models import Notification


    defaults = {
        "user":
            order.user,

        "order_id":
            order.id,

        "channel":
            channel,

        "category":
            category,

        "subject":
            (
                f"{subject} — "
                f"{order.order_number}"
            ),

        "message":
            email_message,

        "sms_message":
            sms_message,
    }


    if event_key:

        notification, created = (
            Notification.objects
            .get_or_create(
                event_key=event_key,
                defaults=defaults,
            )
        )


        if (
            not created
            and notification.status == "sent"
        ):
            return notification


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

@shared_task
def send_payment_confirmation(
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


    return _send_order_notifications(
        order,

        (
            f"Order {order.order_number}: "
            f"payment received "
            f"(KES {order.total_amount})."
        ),

        "Payment received",

        (
            f"Hi {order.full_name},\n\n"
            f"Payment received for "
            f"{order.order_number}.\n"
            f"Amount: KES "
            f"{order.total_amount}."
        ),

        event_key=(
            f"payment:"
            f"{order.pk}:confirmed"
        ),

        category="payments",
    )


# ============================================================
# DELIVERY COMPLETE
# ============================================================

@shared_task
def send_delivery_notification(
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


    return _send_order_notifications(
        order,

        (
            f"Order {order.order_number} "
            f"has been delivered."
        ),

        "Order delivered",

        (
            f"Hi {order.full_name},\n\n"
            f"Order {order.order_number} "
            f"has been delivered."
        ),

        event_key=(
            f"order:"
            f"{order.pk}:delivered"
        ),

        category="delivery",
    )


# ============================================================
# ORDER STATUS
# ============================================================

@shared_task
def send_order_status_notification(
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


    return _send_order_notifications(
        order,

        (
            f"Order {order.order_number}: "
            f"{status_label}."
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

        category="orders",
    )


# ============================================================
# CREDIT NOTE
# ============================================================

@shared_task
def send_credit_note_issued_notification(
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


    return _send_order_notifications(
        order,

        (
            f"Refund of KES "
            f"{refund.amount:.2f} "
            f"processed for "
            f"{order.order_number}."
        ),

        "Refund credit note issued",

        (
            f"Hi {order.full_name},\n\n"
            f"Your refund has been processed.\n\n"
            f"Refund amount: "
            f"KES {refund.amount:.2f}\n"
            f"Reference: "
            f"{refund.external_reference}\n"
            f"Credit note: "
            f"{document.document_number}"
        ),

        event_key=(
            f"credit-note:"
            f"{document.pk}:issued"
        ),

        category="returns",
    )


# ============================================================
# MANUAL RETRY
# ============================================================

@shared_task
def retry_notification(
    notification_id,
):

    from .models import Notification


    notification = (
        Notification.objects
        .get(
            id=notification_id
        )
    )


    failed_channels = set()


    if notification.email_status == "failed":
        failed_channels.add(
            "email"
        )


    if notification.sms_status == "failed":
        failed_channels.add(
            "sms"
        )


    # Compatibility with notifications created before
    # Phase 11D.
    if (
        not failed_channels
        and notification.status
        in {
            "failed",
            "partial",
        }
    ):

        failed_channels = (
            _requested_channels(
                notification
            )
        )


    if not failed_channels:
        return notification


    return _deliver_notification_record(
        notification,
        channels=failed_channels,
    )
'''.strip() + "\n",
encoding="utf-8",
)

print(
    "Per-channel delivery engine installed."
)


# ============================================================
# 3. ADMIN RETRY VIEW
# ============================================================

text = VIEWS.read_text(
    encoding="utf-8-sig"
)


text = text.replace(
    '''        status="failed",
''',
    '''        status__in=[
            "failed",
            "partial",
        ],
''',
    1,
)


text = text.replace(
    '''        "failed":
            Notification.objects.filter(
                status="failed"
            ).count(),
''',
    '''        "failed":
            Notification.objects.filter(
                status="failed"
            ).count(),

        "partial":
            Notification.objects.filter(
                status="partial"
            ).count(),
''',
    1,
)


text = text.replace(
    '''        "failed",
    }:
''',
    '''        "failed",
        "partial",
    }:
''',
    1,
)


VIEWS.write_text(
    text,
    encoding="utf-8",
)

print(
    "Admin retry supports partial delivery."
)


# ============================================================
# 4. ADMIN TEMPLATE
# ============================================================

text = ADMIN_TEMPLATE.read_text(
    encoding="utf-8-sig"
)


text = text.replace(
    '''                        <th>
                            Status
                        </th>
''',
    '''                        <th>
                            Overall
                        </th>

                        <th>
                            Email
                        </th>

                        <th>
                            SMS
                        </th>
''',
    1,
)


text = text.replace(
    '''                            <td>
                                {{ notification.attempts }}
                            </td>
''',
    '''                            <td>
                                {% if notification.email_status == "sent" %}
                                    <span class="badge bg-success">Sent</span>
                                {% elif notification.email_status == "failed" %}
                                    <span class="badge bg-danger">Failed</span>
                                {% elif notification.email_status == "skipped" %}
                                    <span class="badge bg-secondary">Skipped</span>
                                {% else %}
                                    <span class="badge bg-light text-dark">
                                        {{ notification.email_status }}
                                    </span>
                                {% endif %}

                                {% if notification.email_error %}
                                    <div class="small text-danger mt-1">
                                        {{ notification.email_error|truncatechars:70 }}
                                    </div>
                                {% endif %}
                            </td>

                            <td>
                                {% if notification.sms_status == "sent" %}
                                    <span class="badge bg-success">Sent</span>
                                {% elif notification.sms_status == "failed" %}
                                    <span class="badge bg-danger">Failed</span>
                                {% elif notification.sms_status == "skipped" %}
                                    <span class="badge bg-secondary">Skipped</span>
                                {% else %}
                                    <span class="badge bg-light text-dark">
                                        {{ notification.sms_status }}
                                    </span>
                                {% endif %}

                                {% if notification.sms_error %}
                                    <div class="small text-danger mt-1">
                                        {{ notification.sms_error|truncatechars:70 }}
                                    </div>
                                {% endif %}
                            </td>

                            <td>
                                {{ notification.attempts }}
                            </td>
''',
    1,
)


text = text.replace(
    '''                                {% if notification.status == "failed" %}
''',
    '''                                {% if notification.status == "failed" or notification.status == "partial" %}
''',
)


# Fix table empty colspan after adding 2 columns.
text = text.replace(
    'colspan="7"',
    'colspan="9"',
)


ADMIN_TEMPLATE.write_text(
    text,
    encoding="utf-8",
)

print(
    "Admin notification channel visibility added."
)


# ============================================================
# 5. TESTS
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
'''.strip() + "\n",
encoding="utf-8",
)


print(
    "Phase 11D tests created."
)


print()
print("=" * 72)
print("PHASE 11D INSTALLED")
print("=" * 72)
print()
print("Added:")
print("  Independent email delivery state")
print("  Independent SMS delivery state")
print("  Per-channel attempt counters")
print("  Per-channel error messages")
print("  Per-channel sent timestamps")
print("  Partial delivery state")
print("  Retry failed channel only")
print("  No duplicate successful email on SMS retry")
print("  Admin channel visibility")
print()
print("Migration required.")
