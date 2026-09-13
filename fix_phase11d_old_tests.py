from pathlib import Path
import shutil


ROOT = Path.cwd()

PHASE11B = (
    ROOT
    / "notifications"
    / "test_phase11b.py"
)

LEGACY = (
    ROOT
    / "notifications"
    / "tests.py"
)


for path in [
    PHASE11B,
    LEGACY,
]:

    if not path.exists():
        raise RuntimeError(
            f"Missing file: {path}"
        )

    backup = Path(
        str(path)
        + ".phase11d-test-backup"
    )

    if not backup.exists():
        shutil.copy2(
            path,
            backup,
        )


# ============================================================
# 1. UPDATE PHASE 11B TESTS
# ============================================================

text = PHASE11B.read_text(
    encoding="utf-8-sig"
)


# ------------------------------------------------------------
# Idempotent event:
# external channels are disabled in setUp(), therefore
# Phase 11D correctly performs zero provider attempts.
# ------------------------------------------------------------

old = '''        self.assertEqual(
            notification.attempts,
            1,
        )
'''

new = '''        # External delivery is disabled for this test user.
        # The in-app notification is successful without making
        # an email/SMS provider attempt.
        self.assertEqual(
            notification.attempts,
            0,
        )

        self.assertEqual(
            notification.email_status,
            "skipped",
        )

        self.assertEqual(
            notification.sms_status,
            "skipped",
        )
'''

if old not in text:
    raise RuntimeError(
        "Could not locate Phase 11B "
        "idempotency attempts assertion."
    )

text = text.replace(
    old,
    new,
    1,
)


# ------------------------------------------------------------
# Replace old manual retry test.
#
# Phase 11D needs the actual failed channel to be recorded.
# ------------------------------------------------------------

start = text.find(
    "    def test_manual_retry_reuses_same_row("
)

end = text.find(
    "\n\n    @patch(\n"
    '        "notifications.tasks.send_mail"',
    start,
)


if start == -1 or end == -1:
    raise RuntimeError(
        "Could not locate manual retry test."
    )


replacement = r'''    @patch(
        "notifications.tasks.send_mail"
    )
    def test_manual_retry_reuses_same_row(
        self,
        mocked_send_mail,
    ):

        # Phase 11D retries specific failed channels.
        # Enable email for this test and disable SMS.
        self.customer.email_notifications = True
        self.customer.sms_notifications = False

        self.customer.save(
            update_fields=[
                "email_notifications",
                "sms_notifications",
            ]
        )


        from notifications.preference_service import (
            get_notification_preferences,
        )


        preferences = (
            get_notification_preferences(
                self.customer
            )
        )

        preferences.email_enabled = True
        preferences.sms_enabled = False

        preferences.save(
            update_fields=[
                "email_enabled",
                "sms_enabled",
                "updated_at",
            ]
        )


        notification = (
            Notification.objects.create(
                user=self.customer,
                order_id=self.order.pk,
                channel="email",
                event_key="test:manual-retry",
                subject=(
                    "Retry test — "
                    f"{self.order.order_number}"
                ),
                message="Retry email message",
                sms_message="Retry SMS",
                status="failed",
                email_status="failed",
                sms_status="not_requested",
                email_attempts=1,
                sms_attempts=0,
                attempts=1,
                email_error="Temporary failure",
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
            notification.email_status,
            "sent",
        )


        self.assertEqual(
            notification.sms_status,
            "not_requested",
        )


        self.assertEqual(
            notification.email_attempts,
            2,
        )


        self.assertEqual(
            notification.sms_attempts,
            0,
        )


        self.assertEqual(
            notification.attempts,
            2,
        )


        self.assertEqual(
            notification.last_error,
            "",
        )


        mocked_send_mail.assert_called_once()
'''


text = (
    text[:start]
    + replacement
    + text[end:]
)


# ------------------------------------------------------------
# Provider failure:
# Phase 11D RECORDS the failure instead of raising it.
# ------------------------------------------------------------

old = '''        with self.assertRaises(
            RuntimeError
        ):

            send_payment_confirmation.run(
                self.order.pk
            )
'''


new = '''        send_payment_confirmation.run(
            self.order.pk
        )
'''


if old not in text:
    raise RuntimeError(
        "Could not locate old provider "
        "exception assertion."
    )


text = text.replace(
    old,
    new,
    1,
)


# Add channel-level assertions to provider failure.
marker = '''        self.assertEqual(
            notification.status,
            "failed",
        )


        self.assertEqual(
            notification.attempts,
            1,
        )
'''


replacement = '''        self.assertEqual(
            notification.status,
            "failed",
        )


        self.assertEqual(
            notification.email_status,
            "failed",
        )


        self.assertEqual(
            notification.sms_status,
            "skipped",
        )


        self.assertEqual(
            notification.email_attempts,
            1,
        )


        self.assertEqual(
            notification.sms_attempts,
            0,
        )


        self.assertEqual(
            notification.attempts,
            1,
        )
'''


if marker not in text:
    raise RuntimeError(
        "Could not locate provider "
        "failure assertions."
    )


text = text.replace(
    marker,
    replacement,
    1,
)


PHASE11B.write_text(
    text,
    encoding="utf-8",
)

print(
    "Phase 11B tests updated for Phase 11D semantics."
)


# ============================================================
# 2. REWRITE LEGACY NOTIFICATION TEST
# ============================================================

LEGACY.write_text(
r'''from unittest.mock import patch

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
'''.strip() + "\n",
encoding="utf-8",
)


print(
    "Legacy notification test updated."
)


print()
print("=" * 72)
print("PHASE 11D TEST COMPATIBILITY REPAIR COMPLETE")
print("=" * 72)
print()
print("No model changes.")
print("No migration required.")
print()
print("Updated old tests to verify:")
print("  skipped channels do not count as attempts")
print("  provider failures are recorded, not raised")
print("  retry targets the failed channel")
print("  retry reuses the same Notification row")
print("  email/SMS attempt counters remain independent")
