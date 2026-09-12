from pathlib import Path
import shutil


ROOT = Path.cwd()

MODELS = ROOT / "notifications" / "models.py"
TASKS = ROOT / "notifications" / "tasks.py"
VIEWS = ROOT / "notifications" / "views.py"
URLS = ROOT / "notifications" / "urls.py"

RETURNS_TASKS = ROOT / "payments" / "returns_tasks.py"
DELIVERY_TASKS = ROOT / "delivery" / "tasks.py"

CUSTOMER_LIST = (
    ROOT
    / "templates"
    / "notifications"
    / "customer_list.html"
)

PREFERENCES_TEMPLATE = (
    ROOT
    / "templates"
    / "notifications"
    / "preferences.html"
)

SERVICES = (
    ROOT
    / "notifications"
    / "preference_service.py"
)

TESTS = (
    ROOT
    / "notifications"
    / "test_phase11c.py"
)


required = [
    MODELS,
    TASKS,
    VIEWS,
    URLS,
    RETURNS_TASKS,
    DELIVERY_TASKS,
    CUSTOMER_LIST,
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
        str(path)
        + ".phase11cbackup"
    )

    if not backup.exists():
        shutil.copy2(
            path,
            backup,
        )


# ============================================================
# 1. NOTIFICATION CATEGORY
# ============================================================

text = MODELS.read_text(
    encoding="utf-8-sig"
)


if "CATEGORY_CHOICES" not in text:

    marker = (
        "class Notification(models.Model):\n"
    )

    replacement = '''class Notification(models.Model):

    CATEGORY_CHOICES = [
        ("general", "General"),
        ("orders", "Order Updates"),
        ("payments", "Payment Updates"),
        ("delivery", "Delivery Updates"),
        ("returns", "Returns & Refunds"),
        ("marketing", "Marketing"),
    ]
'''

    if marker not in text:
        raise RuntimeError(
            "Notification model not found."
        )

    text = text.replace(
        marker,
        replacement,
        1,
    )


if "category = models.CharField" not in text:

    marker = (
        '    channel = models.CharField('
        'max_length=20, default="email")\n'
    )

    if marker not in text:
        marker = (
            '\tchannel = models.CharField('
            'max_length=20, default="email")\n'
        )


    if marker not in text:
        raise RuntimeError(
            "Could not locate Notification.channel."
        )


    indentation = (
        "\t"
        if marker.startswith("\t")
        else "    "
    )


    addition = (
        marker
        + indentation
        + 'category = models.CharField('
        + 'max_length=20, choices=CATEGORY_CHOICES, '
        + 'default="general", db_index=True)\n'
    )


    text = text.replace(
        marker,
        addition,
        1,
    )


# ============================================================
# 2. NOTIFICATION PREFERENCE MODEL
# ============================================================

if "class NotificationPreference(" not in text:

    text += r'''


class NotificationPreference(models.Model):

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preferences",
    )

    # --------------------------------------------------------
    # MASTER CHANNEL SWITCHES
    # --------------------------------------------------------

    email_enabled = models.BooleanField(
        default=True,
    )

    sms_enabled = models.BooleanField(
        default=True,
    )


    # --------------------------------------------------------
    # TRANSACTIONAL CATEGORIES
    # --------------------------------------------------------

    order_updates = models.BooleanField(
        default=True,
    )

    payment_updates = models.BooleanField(
        default=True,
    )

    delivery_updates = models.BooleanField(
        default=True,
    )

    return_refund_updates = models.BooleanField(
        default=True,
    )


    # --------------------------------------------------------
    # OPTIONAL / MARKETING
    # --------------------------------------------------------

    marketing_email = models.BooleanField(
        default=False,
    )

    marketing_sms = models.BooleanField(
        default=False,
    )


    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )


    def __str__(self):

        return (
            f"Notification preferences - "
            f"{self.user}"
        )
'''


MODELS.write_text(
    text,
    encoding="utf-8",
)

print(
    "Notification category and preference model added."
)


# ============================================================
# 3. PREFERENCE SERVICE
# ============================================================

SERVICES.write_text(
r'''
from notifications.models import (
    NotificationPreference,
)


TRANSACTIONAL_CATEGORIES = {
    "general",
    "orders",
    "payments",
    "delivery",
    "returns",
}


def get_notification_preferences(
    user,
):

    """
    Lazily migrate the legacy CustomUser notification
    switches into the richer preference model.
    """

    preferences, _ = (
        NotificationPreference.objects
        .get_or_create(
            user=user,
            defaults={
                "email_enabled":
                    getattr(
                        user,
                        "email_notifications",
                        True,
                    ),

                "sms_enabled":
                    getattr(
                        user,
                        "sms_notifications",
                        True,
                    ),
            },
        )
    )


    return preferences


def category_enabled(
    preferences,
    category,
):

    if category == "orders":
        return preferences.order_updates

    if category == "payments":
        return preferences.payment_updates

    if category == "delivery":
        return preferences.delivery_updates

    if category == "returns":
        return preferences.return_refund_updates

    if category == "marketing":
        return True

    return True


def email_allowed(
    user,
    category,
):

    preferences = (
        get_notification_preferences(
            user
        )
    )


    if category == "marketing":

        return (
            preferences.email_enabled
            and
            preferences.marketing_email
        )


    return (
        preferences.email_enabled
        and
        category_enabled(
            preferences,
            category,
        )
    )


def sms_allowed(
    user,
    category,
):

    preferences = (
        get_notification_preferences(
            user
        )
    )


    if category == "marketing":

        return (
            preferences.sms_enabled
            and
            preferences.marketing_sms
        )


    return (
        preferences.sms_enabled
        and
        category_enabled(
            preferences,
            category,
        )
    )
'''.strip() + "\n",
encoding="utf-8",
)

print(
    "Notification preference service created."
)


# ============================================================
# 4. PATCH TASK DELIVERY ENGINE
# ============================================================

text = TASKS.read_text(
    encoding="utf-8-sig"
)


# ------------------------------------------------------------
# Import preference checks
# ------------------------------------------------------------

if "from notifications.preference_service import" not in text:

    marker = (
        "from django.utils import timezone\n"
    )

    addition = marker + '''

from notifications.preference_service import (
    email_allowed,
    sms_allowed,
)
'''

    if marker not in text:
        raise RuntimeError(
            "Could not locate timezone import "
            "in notifications/tasks.py"
        )

    text = text.replace(
        marker,
        addition,
        1,
    )


# ------------------------------------------------------------
# Replace old legacy email preference check
# ------------------------------------------------------------

text = text.replace(
    '''            and order.user.sms_notifications
''',
    '''            and sms_allowed(
                order.user,
                notification.category,
            )
''',
)


text = text.replace(
    '''            and order.user.email_notifications
''',
    '''            and email_allowed(
                order.user,
                notification.category,
            )
''',
)


# ------------------------------------------------------------
# _send_order_notifications gets category argument
# ------------------------------------------------------------

old = '''    *,
    event_key=None,
    channel="email_and_sms",
):
'''

new = '''    *,
    event_key=None,
    channel="email_and_sms",
    category="general",
):
'''


if old in text:

    text = text.replace(
        old,
        new,
        1,
    )

elif 'category="general"' not in text:

    raise RuntimeError(
        "Could not patch _send_order_notifications signature."
    )


# ------------------------------------------------------------
# Save category to Notification row
# ------------------------------------------------------------

old = '''        "channel": channel,
        "subject": (
'''

new = '''        "channel": channel,
        "category": category,
        "subject": (
'''


if old in text:

    text = text.replace(
        old,
        new,
        1,
    )


# ============================================================
# 5. ASSIGN EVENT CATEGORIES
# ============================================================

# Payment
old = '''        event_key=(
            f"payment:"
            f"{order.pk}:confirmed"
        ),
    )
'''

new = '''        event_key=(
            f"payment:"
            f"{order.pk}:confirmed"
        ),
        category="payments",
    )
'''

if old in text:
    text = text.replace(old, new, 1)


# Legacy delivery
old = '''        event_key=(
            f"order:"
            f"{order.pk}:delivered"
        ),
    )
'''

new = '''        event_key=(
            f"order:"
            f"{order.pk}:delivered"
        ),
        category="delivery",
    )
'''

if old in text:
    text = text.replace(old, new, 1)


# Order status
old = '''        event_key=(
            f"order:"
            f"{order.pk}:status:"
            f"{order.status}"
        ),
    )
'''

new = '''        event_key=(
            f"order:"
            f"{order.pk}:status:"
            f"{order.status}"
        ),
        category="orders",
    )
'''

if old in text:
    text = text.replace(old, new, 1)


# Credit note
old = '''        event_key=(
            f"credit-note:"
            f"{document.pk}:issued"
        ),
    )
'''

new = '''        event_key=(
            f"credit-note:"
            f"{document.pk}:issued"
        ),
        category="returns",
    )
'''

if old in text:
    text = text.replace(old, new, 1)


TASKS.write_text(
    text,
    encoding="utf-8",
)

print(
    "Notification delivery now respects preferences."
)


# ============================================================
# 6. RETURN / REFUND CATEGORY
# ============================================================

text = RETURNS_TASKS.read_text(
    encoding="utf-8-sig"
)


old = '''        event_key=(
            f"return:"
            f"{obj.pk}:"
            f"{obj.status}"
        ),
    )
'''

new = '''        event_key=(
            f"return:"
            f"{obj.pk}:"
            f"{obj.status}"
        ),
        category="returns",
    )
'''

if old in text:
    text = text.replace(old, new, 1)


old = '''        event_key=(
            f"refund:"
            f"{obj.pk}:"
            f"{obj.status}"
        ),
    )
'''

new = '''        event_key=(
            f"refund:"
            f"{obj.pk}:"
            f"{obj.status}"
        ),
        category="returns",
    )
'''

if old in text:
    text = text.replace(old, new, 1)


RETURNS_TASKS.write_text(
    text,
    encoding="utf-8",
)

print(
    "Return/refund categories assigned."
)


# ============================================================
# 7. DELIVERY CATEGORY
# ============================================================

text = DELIVERY_TASKS.read_text(
    encoding="utf-8-sig"
)


old = '''        event_key=(
            f"delivery:"
            f"{delivery.pk}:"
            f"{delivery.status}"
        ),
    )
'''

new = '''        event_key=(
            f"delivery:"
            f"{delivery.pk}:"
            f"{delivery.status}"
        ),
        category="delivery",
    )
'''

if old in text:
    text = text.replace(old, new, 1)


old = '''        event_key=(
            f"delivery-quote:"
            f"{order.pk}:"
            f"{order.shipping_cost}:"
            f"{order.total_amount}"
        ),
    )
'''

new = '''        event_key=(
            f"delivery-quote:"
            f"{order.pk}:"
            f"{order.shipping_cost}:"
            f"{order.total_amount}"
        ),
        category="delivery",
    )
'''

if old in text:
    text = text.replace(old, new, 1)


DELIVERY_TASKS.write_text(
    text,
    encoding="utf-8",
)

print(
    "Delivery categories assigned."
)


# ============================================================
# 8. PREFERENCES VIEW
# ============================================================

text = VIEWS.read_text(
    encoding="utf-8-sig"
)


if "def notification_preferences(" not in text:

    text += r'''


# ============================================================
# CUSTOMER NOTIFICATION PREFERENCES
# ============================================================

@login_required
def notification_preferences(
    request,
):

    from notifications.preference_service import (
        get_notification_preferences,
    )


    preferences = (
        get_notification_preferences(
            request.user
        )
    )


    if request.method == "POST":

        preferences.email_enabled = (
            request.POST.get(
                "email_enabled"
            )
            == "on"
        )

        preferences.sms_enabled = (
            request.POST.get(
                "sms_enabled"
            )
            == "on"
        )

        preferences.order_updates = (
            request.POST.get(
                "order_updates"
            )
            == "on"
        )

        preferences.payment_updates = (
            request.POST.get(
                "payment_updates"
            )
            == "on"
        )

        preferences.delivery_updates = (
            request.POST.get(
                "delivery_updates"
            )
            == "on"
        )

        preferences.return_refund_updates = (
            request.POST.get(
                "return_refund_updates"
            )
            == "on"
        )

        preferences.marketing_email = (
            request.POST.get(
                "marketing_email"
            )
            == "on"
        )

        preferences.marketing_sms = (
            request.POST.get(
                "marketing_sms"
            )
            == "on"
        )


        preferences.save()


        # Keep old fields in sync so older project code
        # remains compatible during migration.
        request.user.email_notifications = (
            preferences.email_enabled
        )

        request.user.sms_notifications = (
            preferences.sms_enabled
        )

        request.user.save(
            update_fields=[
                "email_notifications",
                "sms_notifications",
            ]
        )


        messages.success(
            request,
            "Notification preferences updated.",
        )


        return redirect(
            "notification_preferences"
        )


    return render(
        request,
        "notifications/preferences.html",
        {
            "preferences":
                preferences,
        },
    )
'''


VIEWS.write_text(
    text,
    encoding="utf-8",
)

print(
    "Notification preference view added."
)


# ============================================================
# 9. URL
# ============================================================

text = URLS.read_text(
    encoding="utf-8-sig"
)


if 'name="notification_preferences"' not in text:

    marker = '''    path(
        "mark-all-read/",
        views.customer_notifications_mark_all_read,
        name="customer_notifications_mark_all_read",
    ),
'''


    addition = marker + '''

    path(
        "preferences/",
        views.notification_preferences,
        name="notification_preferences",
    ),
'''


    if marker not in text:
        raise RuntimeError(
            "Could not locate notification "
            "mark-all-read route."
        )


    text = text.replace(
        marker,
        addition,
        1,
    )


URLS.write_text(
    text,
    encoding="utf-8",
)

print(
    "Notification preferences route added."
)


# ============================================================
# 10. CUSTOMER LIST PREFERENCES BUTTON
# ============================================================

text = CUSTOMER_LIST.read_text(
    encoding="utf-8-sig"
)


if "notification_preferences" not in text:

    marker = '''        {% if unread_count %}
'''


    button = '''        <a
            href="{% url 'notification_preferences' %}"
            class="btn btn-outline-secondary"
        >
            Notification Preferences
        </a>

'''


    if marker not in text:
        raise RuntimeError(
            "Could not locate customer "
            "notification header."
        )


    text = text.replace(
        marker,
        button + marker,
        1,
    )


CUSTOMER_LIST.write_text(
    text,
    encoding="utf-8",
)

print(
    "Preferences button added."
)


# ============================================================
# 11. PREFERENCES TEMPLATE
# ============================================================

PREFERENCES_TEMPLATE.write_text(
r'''
{% extends "base.html" %}


{% block content %}

<div class="py-4">

    <div class="row justify-content-center">

        <div class="col-lg-8">

            <div class="mb-4">

                <a
                    href="{% url 'customer_notifications' %}"
                    class="text-decoration-none"
                >
                    ← Back to Notifications
                </a>

                <h2 class="mt-3 mb-1">
                    Notification Preferences
                </h2>

                <p class="text-muted">
                    Choose how you receive store updates.
                    Important events will still appear inside
                    your account notification center.
                </p>

            </div>


            <form method="post">

                {% csrf_token %}


                <!-- CHANNELS -->

                <div class="card border-0 shadow-sm mb-4">

                    <div class="card-body">

                        <h5 class="mb-3">
                            Delivery Channels
                        </h5>


                        <div class="form-check form-switch mb-3">

                            <input
                                class="form-check-input"
                                type="checkbox"
                                id="email_enabled"
                                name="email_enabled"
                                {% if preferences.email_enabled %}
                                    checked
                                {% endif %}
                            >

                            <label
                                class="form-check-label"
                                for="email_enabled"
                            >
                                Email notifications
                            </label>

                        </div>


                        <div class="form-check form-switch">

                            <input
                                class="form-check-input"
                                type="checkbox"
                                id="sms_enabled"
                                name="sms_enabled"
                                {% if preferences.sms_enabled %}
                                    checked
                                {% endif %}
                            >

                            <label
                                class="form-check-label"
                                for="sms_enabled"
                            >
                                SMS notifications
                            </label>

                        </div>

                    </div>

                </div>


                <!-- TRANSACTIONAL -->

                <div class="card border-0 shadow-sm mb-4">

                    <div class="card-body">

                        <h5 class="mb-1">
                            Transactional Updates
                        </h5>

                        <p class="text-muted small mb-4">
                            These relate directly to purchases,
                            payments and fulfilment.
                        </p>


                        <div class="form-check form-switch mb-3">

                            <input
                                class="form-check-input"
                                type="checkbox"
                                id="order_updates"
                                name="order_updates"
                                {% if preferences.order_updates %}
                                    checked
                                {% endif %}
                            >

                            <label
                                class="form-check-label"
                                for="order_updates"
                            >
                                Order status updates
                            </label>

                        </div>


                        <div class="form-check form-switch mb-3">

                            <input
                                class="form-check-input"
                                type="checkbox"
                                id="payment_updates"
                                name="payment_updates"
                                {% if preferences.payment_updates %}
                                    checked
                                {% endif %}
                            >

                            <label
                                class="form-check-label"
                                for="payment_updates"
                            >
                                Payment confirmations
                            </label>

                        </div>


                        <div class="form-check form-switch mb-3">

                            <input
                                class="form-check-input"
                                type="checkbox"
                                id="delivery_updates"
                                name="delivery_updates"
                                {% if preferences.delivery_updates %}
                                    checked
                                {% endif %}
                            >

                            <label
                                class="form-check-label"
                                for="delivery_updates"
                            >
                                Delivery and pickup updates
                            </label>

                        </div>


                        <div class="form-check form-switch">

                            <input
                                class="form-check-input"
                                type="checkbox"
                                id="return_refund_updates"
                                name="return_refund_updates"
                                {% if preferences.return_refund_updates %}
                                    checked
                                {% endif %}
                            >

                            <label
                                class="form-check-label"
                                for="return_refund_updates"
                            >
                                Return and refund updates
                            </label>

                        </div>

                    </div>

                </div>


                <!-- OPTIONAL -->

                <div class="card border-0 shadow-sm mb-4">

                    <div class="card-body">

                        <h5 class="mb-1">
                            Optional Messages
                        </h5>

                        <p class="text-muted small mb-4">
                            Promotional communication is off by
                            default and requires explicit opt-in.
                        </p>


                        <div class="form-check form-switch mb-3">

                            <input
                                class="form-check-input"
                                type="checkbox"
                                id="marketing_email"
                                name="marketing_email"
                                {% if preferences.marketing_email %}
                                    checked
                                {% endif %}
                            >

                            <label
                                class="form-check-label"
                                for="marketing_email"
                            >
                                Promotional email
                            </label>

                        </div>


                        <div class="form-check form-switch">

                            <input
                                class="form-check-input"
                                type="checkbox"
                                id="marketing_sms"
                                name="marketing_sms"
                                {% if preferences.marketing_sms %}
                                    checked
                                {% endif %}
                            >

                            <label
                                class="form-check-label"
                                for="marketing_sms"
                            >
                                Promotional SMS
                            </label>

                        </div>

                    </div>

                </div>


                <button
                    type="submit"
                    class="btn btn-primary"
                >
                    Save Preferences
                </button>

            </form>

        </div>

    </div>

</div>

{% endblock %}
'''.strip() + "\n",
encoding="utf-8",
)

print(
    "Preferences UI created."
)


# ============================================================
# 12. TESTS
# ============================================================

TESTS.write_text(
r'''
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
'''.strip() + "\n",
encoding="utf-8",
)

print(
    "Phase 11C tests created."
)


print()
print("=" * 72)
print("PHASE 11C INSTALLED")
print("=" * 72)
print()
print("Added:")
print("  Notification categories")
print("  Per-customer notification preferences")
print("  Email master switch")
print("  SMS master switch")
print("  Order update preference")
print("  Payment update preference")
print("  Delivery update preference")
print("  Return/refund preference")
print("  Marketing email opt-in")
print("  Marketing SMS opt-in")
print("  Legacy preference compatibility")
print("  In-app notifications remain available")
print()
print("Migration required.")
