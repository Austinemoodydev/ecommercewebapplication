from celery import shared_task

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from notifications.preference_service import (
    email_allowed,
    sms_allowed,
)


# Maximum total provider attempts for one notification/channel.
# Initial delivery counts as one attempt.
MAX_CHANNEL_DELIVERY_ATTEMPTS = 3


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
# MANUAL RETRY / OPERATIONS
# ============================================================

def _channel_attempts(
    notification,
    channel,
):

    if channel == "email":
        return notification.email_attempts

    if channel == "sms":
        return notification.sms_attempts

    raise ValueError(
        f"Unsupported notification channel: {channel}"
    )


def _channel_status(
    notification,
    channel,
):

    if channel == "email":
        return notification.email_status

    if channel == "sms":
        return notification.sms_status

    raise ValueError(
        f"Unsupported notification channel: {channel}"
    )


def channel_retry_available(
    notification,
    channel,
):

    """
    A channel can be retried only when:

    - it previously failed
    - it has not reached the operational retry cap
    """

    return (
        _channel_status(
            notification,
            channel,
        )
        == "failed"
        and
        _channel_attempts(
            notification,
            channel,
        )
        < MAX_CHANNEL_DELIVERY_ATTEMPTS
    )


def retryable_failed_channels(
    notification,
):

    channels = set()


    # --------------------------------------------------------
    # MODERN PHASE 11D / 11E RECORDS
    # --------------------------------------------------------

    if channel_retry_available(
        notification,
        "email",
    ):
        channels.add(
            "email"
        )


    if channel_retry_available(
        notification,
        "sms",
    ):
        channels.add(
            "sms"
        )


    if channels:
        return channels


    # --------------------------------------------------------
    # LEGACY COMPATIBILITY
    # --------------------------------------------------------
    #
    # Notifications created before Phase 11D only had the
    # overall `status` field.
    #
    # Example:
    #
    #   status="failed"
    #   email_status="not_requested"
    #   sms_status="not_requested"
    #
    # These rows must remain retryable after upgrading to
    # per-channel delivery tracking.
    #
    # We intentionally enable this fallback only when both
    # per-channel states are still "not_requested". This avoids
    # accidentally retrying modern skipped/successful channels.

    legacy_record = (
        notification.status
        in {
            "failed",
            "partial",
        }
        and
        notification.email_status
        == "not_requested"
        and
        notification.sms_status
        == "not_requested"
    )


    if not legacy_record:
        return channels


    requested = (
        _requested_channels(
            notification
        )
    )


    if (
        "email" in requested
        and
        notification.email_attempts
        < MAX_CHANNEL_DELIVERY_ATTEMPTS
    ):
        channels.add(
            "email"
        )


    if (
        "sms" in requested
        and
        notification.sms_attempts
        < MAX_CHANNEL_DELIVERY_ATTEMPTS
    ):
        channels.add(
            "sms"
        )


    return channels



@shared_task
def retry_notification_channel(
    notification_id,
    channel,
):

    """
    Retry exactly one failed channel.

    A successful email can therefore never be resent merely
    because SMS failed, and vice versa.
    """

    from .models import Notification


    if channel not in {
        "email",
        "sms",
    }:
        raise ValueError(
            "Channel must be email or sms."
        )


    notification = (
        Notification.objects
        .get(
            id=notification_id
        )
    )


    if not channel_retry_available(
        notification,
        channel,
    ):
        return notification


    return _deliver_notification_record(
        notification,
        channels={
            channel
        },
    )


@shared_task
def retry_notification(
    notification_id,
):

    """
    Retry all failed channels that remain below the retry cap.
    """

    from .models import Notification


    notification = (
        Notification.objects
        .get(
            id=notification_id
        )
    )


    failed_channels = (
        retryable_failed_channels(
            notification
        )
    )


    if not failed_channels:
        return notification


    return _deliver_notification_record(
        notification,
        channels=failed_channels,
    )

