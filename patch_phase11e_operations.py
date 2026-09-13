from pathlib import Path
import shutil
import re


ROOT = Path.cwd()

TASKS = ROOT / "notifications" / "tasks.py"
VIEWS = ROOT / "notifications" / "views.py"
URLS = ROOT / "notifications" / "urls.py"

ADMIN_LIST = (
    ROOT
    / "templates"
    / "notifications"
    / "admin_list.html"
)

ADMIN_DETAIL = (
    ROOT
    / "templates"
    / "notifications"
    / "admin_detail.html"
)

TESTS = (
    ROOT
    / "notifications"
    / "test_phase11e.py"
)


required = [
    TASKS,
    VIEWS,
    URLS,
    ADMIN_LIST,
]

for path in required:

    if not path.exists():
        raise RuntimeError(
            f"Missing required file: {path}"
        )


for path in required:

    backup = Path(
        str(path)
        + ".phase11ebackup"
    )

    if not backup.exists():
        shutil.copy2(
            path,
            backup,
        )


# ============================================================
# 1. TASKS — CONTROLLED RETRY ENGINE
# ============================================================

text = TASKS.read_text(
    encoding="utf-8-sig"
)


# Add operational constant near imports.
if "MAX_CHANNEL_DELIVERY_ATTEMPTS = 3" not in text:

    marker = '''from notifications.preference_service import (
    email_allowed,
    sms_allowed,
)
'''

    addition = marker + '''

# Maximum total provider attempts for one notification/channel.
# Initial delivery counts as one attempt.
MAX_CHANNEL_DELIVERY_ATTEMPTS = 3
'''

    if marker not in text:
        raise RuntimeError(
            "Could not locate preference imports."
        )

    text = text.replace(
        marker,
        addition,
        1,
    )


# Replace current retry section at end of tasks.py.
marker = '''# ============================================================
# MANUAL RETRY
# ============================================================
'''

index = text.find(marker)

if index == -1:
    raise RuntimeError(
        "Could not locate MANUAL RETRY section."
    )


new_retry_section = r'''# ============================================================
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
'''


text = (
    text[:index]
    + new_retry_section
    + "\n"
)


TASKS.write_text(
    text,
    encoding="utf-8",
)

print(
    "Controlled notification retry engine installed."
)


# ============================================================
# 2. VIEWS IMPORTS
# ============================================================

text = VIEWS.read_text(
    encoding="utf-8-sig"
)


old = '''from notifications.tasks import (
    retry_notification,
)
'''

new = '''from notifications.tasks import (
    MAX_CHANNEL_DELIVERY_ATTEMPTS,
    channel_retry_available,
    retry_notification,
    retry_notification_channel,
)
'''

if old in text:

    text = text.replace(
        old,
        new,
        1,
    )

elif "retry_notification_channel" not in text:

    raise RuntimeError(
        "Could not patch notification task imports."
    )


# ============================================================
# 3. REPLACE ADMIN NOTIFICATION OPERATIONS
# ============================================================

admin_start = text.find(
    "@staff_member_required\ndef admin_notifications("
)

preferences_marker = text.find(
    "# ============================================================\n"
    "# CUSTOMER NOTIFICATION PREFERENCES"
)


if (
    admin_start == -1
    or preferences_marker == -1
    or preferences_marker <= admin_start
):

    raise RuntimeError(
        "Could not locate admin notification view section."
    )


admin_views = r'''@staff_member_required
def admin_notifications(
    request,
):

    queryset = (
        Notification.objects
        .select_related(
            "user"
        )
        .order_by(
            "-created_at"
        )
    )


    status = (
        request.GET.get(
            "status",
            "",
        )
        .strip()
        .lower()
    )


    channel = (
        request.GET.get(
            "channel",
            "",
        )
        .strip()
    )


    category = (
        request.GET.get(
            "category",
            "",
        )
        .strip()
    )


    search = (
        request.GET.get(
            "q",
            "",
        )
        .strip()
    )


    if status in {
        "pending",
        "sent",
        "failed",
        "partial",
    }:

        queryset = queryset.filter(
            status=status
        )


    if channel in {
        "email",
        "sms",
        "email_and_sms",
    }:

        queryset = queryset.filter(
            channel=channel
        )


    if category in {
        "general",
        "orders",
        "payments",
        "delivery",
        "returns",
        "marketing",
    }:

        queryset = queryset.filter(
            category=category
        )


    if search:

        queryset = queryset.filter(

            Q(
                subject__icontains=search
            )

            |

            Q(
                message__icontains=search
            )

            |

            Q(
                event_key__icontains=search
            )

            |

            Q(
                user__username__icontains=search
            )

            |

            Q(
                user__email__icontains=search
            )
        )


    paginator = Paginator(
        queryset,
        30,
    )


    page_obj = paginator.get_page(
        request.GET.get(
            "page"
        )
    )


    all_notifications = (
        Notification.objects.all()
    )


    total = (
        all_notifications.count()
    )

    sent = (
        all_notifications
        .filter(
            status="sent"
        )
        .count()
    )

    pending = (
        all_notifications
        .filter(
            status="pending"
        )
        .count()
    )

    failed = (
        all_notifications
        .filter(
            status="failed"
        )
        .count()
    )

    partial = (
        all_notifications
        .filter(
            status="partial"
        )
        .count()
    )


    email_sent = (
        all_notifications
        .filter(
            email_status="sent"
        )
        .count()
    )

    email_failed = (
        all_notifications
        .filter(
            email_status="failed"
        )
        .count()
    )

    email_attempted = (
        email_sent
        + email_failed
    )


    sms_sent = (
        all_notifications
        .filter(
            sms_status="sent"
        )
        .count()
    )

    sms_failed = (
        all_notifications
        .filter(
            sms_status="failed"
        )
        .count()
    )

    sms_attempted = (
        sms_sent
        + sms_failed
    )


    email_success_rate = (
        round(
            email_sent
            * 100
            / email_attempted,
            1,
        )
        if email_attempted
        else 0
    )


    sms_success_rate = (
        round(
            sms_sent
            * 100
            / sms_attempted,
            1,
        )
        if sms_attempted
        else 0
    )


    stats = {

        "total":
            total,

        "sent":
            sent,

        "pending":
            pending,

        "failed":
            failed,

        "partial":
            partial,

        "email_sent":
            email_sent,

        "email_failed":
            email_failed,

        "email_success_rate":
            email_success_rate,

        "sms_sent":
            sms_sent,

        "sms_failed":
            sms_failed,

        "sms_success_rate":
            sms_success_rate,
    }


    return render(
        request,
        "notifications/admin_list.html",
        {
            "page_obj":
                page_obj,

            "stats":
                stats,

            "selected_status":
                status,

            "selected_channel":
                channel,

            "selected_category":
                category,

            "search":
                search,

            "max_channel_attempts":
                MAX_CHANNEL_DELIVERY_ATTEMPTS,
        },
    )


@staff_member_required
def admin_notification_detail(
    request,
    notification_id,
):

    notification = get_object_or_404(
        Notification.objects
        .select_related(
            "user"
        ),
        pk=notification_id,
    )


    order = None


    if notification.order_id:

        try:

            from orders.models import Order

            order = (
                Order.objects
                .filter(
                    pk=notification.order_id
                )
                .first()
            )

        except Exception:

            order = None


    email_retry_available = (
        channel_retry_available(
            notification,
            "email",
        )
    )


    sms_retry_available = (
        channel_retry_available(
            notification,
            "sms",
        )
    )


    return render(
        request,
        "notifications/admin_detail.html",
        {
            "notification":
                notification,

            "order":
                order,

            "email_retry_available":
                email_retry_available,

            "sms_retry_available":
                sms_retry_available,

            "max_channel_attempts":
                MAX_CHANNEL_DELIVERY_ATTEMPTS,
        },
    )


@staff_member_required
@require_POST
def admin_retry_notification(
    request,
    notification_id,
):

    notification = get_object_or_404(
        Notification,
        pk=notification_id,
    )


    if not notification.order_id:

        messages.error(
            request,
            "This notification has no linked "
            "order and cannot be retried.",
        )

        return redirect(
            "admin_notification_detail",
            notification_id=notification.pk,
        )


    retryable = (
        channel_retry_available(
            notification,
            "email",
        )
        or
        channel_retry_available(
            notification,
            "sms",
        )
    )


    if not retryable:

        messages.warning(
            request,
            "There are no failed channels available "
            "for retry, or the retry limit has been reached.",
        )

        return redirect(
            "admin_notification_detail",
            notification_id=notification.pk,
        )


    retry_notification.delay(
        notification.pk
    )


    messages.success(
        request,
        "Failed notification channels queued for retry.",
    )


    return redirect(
        "admin_notification_detail",
        notification_id=notification.pk,
    )


@staff_member_required
@require_POST
def admin_retry_notification_channel(
    request,
    notification_id,
    channel,
):

    notification = get_object_or_404(
        Notification,
        pk=notification_id,
    )


    if channel not in {
        "email",
        "sms",
    }:

        messages.error(
            request,
            "Invalid notification channel.",
        )

        return redirect(
            "admin_notification_detail",
            notification_id=notification.pk,
        )


    if not notification.order_id:

        messages.error(
            request,
            "This notification has no linked "
            "order and cannot be retried.",
        )

        return redirect(
            "admin_notification_detail",
            notification_id=notification.pk,
        )


    if not channel_retry_available(
        notification,
        channel,
    ):

        messages.warning(
            request,
            (
                f"{channel.title()} cannot be retried. "
                f"It is either not failed or has reached "
                f"the {MAX_CHANNEL_DELIVERY_ATTEMPTS}-attempt limit."
            ),
        )

        return redirect(
            "admin_notification_detail",
            notification_id=notification.pk,
        )


    retry_notification_channel.delay(
        notification.pk,
        channel,
    )


    messages.success(
        request,
        (
            f"{channel.title()} retry queued."
        ),
    )


    return redirect(
        "admin_notification_detail",
        notification_id=notification.pk,
    )


@staff_member_required
@require_POST
def admin_bulk_retry_notifications(
    request,
):

    raw_ids = (
        request.POST.getlist(
            "notification_ids"
        )
    )


    valid_ids = []


    for value in raw_ids:

        try:

            valid_ids.append(
                int(value)
            )

        except (
            TypeError,
            ValueError,
        ):

            continue


    # Operational safety guard:
    # one browser request cannot enqueue an unlimited batch.
    valid_ids = (
        list(
            dict.fromkeys(
                valid_ids
            )
        )[:50]
    )


    if not valid_ids:

        messages.warning(
            request,
            "Select at least one notification.",
        )

        return redirect(
            "admin_notifications"
        )


    notifications = (
        Notification.objects
        .filter(
            pk__in=valid_ids,
            status__in=[
                "failed",
                "partial",
            ],
        )
    )


    queued = 0
    skipped = 0


    for notification in notifications:

        if not notification.order_id:

            skipped += 1
            continue


        retryable = (
            channel_retry_available(
                notification,
                "email",
            )
            or
            channel_retry_available(
                notification,
                "sms",
            )
        )


        if not retryable:

            skipped += 1
            continue


        retry_notification.delay(
            notification.pk
        )

        queued += 1


    if queued:

        messages.success(
            request,
            (
                f"{queued} notification"
                f"{'' if queued == 1 else 's'} "
                f"queued for retry."
            ),
        )


    if skipped:

        messages.warning(
            request,
            (
                f"{skipped} selected notification"
                f"{'' if skipped == 1 else 's'} "
                f"could not be retried."
            ),
        )


    return redirect(
        "admin_notifications"
    )


'''


text = (
    text[:admin_start]
    + admin_views
    + text[preferences_marker:]
)


VIEWS.write_text(
    text,
    encoding="utf-8",
)

print(
    "Admin notification operations upgraded."
)


# ============================================================
# 4. URLS
# ============================================================

text = URLS.read_text(
    encoding="utf-8-sig"
)


if 'name="admin_notification_detail"' not in text:

    marker = '''    path(
        "admin/",
        views.admin_notifications,
        name="admin_notifications",
    ),
'''

    addition = marker + '''

    path(
        "admin/bulk-retry/",
        views.admin_bulk_retry_notifications,
        name="admin_bulk_retry_notifications",
    ),

    path(
        "admin/<int:notification_id>/",
        views.admin_notification_detail,
        name="admin_notification_detail",
    ),
'''

    if marker not in text:

        raise RuntimeError(
            "Could not locate admin notifications URL."
        )


    text = text.replace(
        marker,
        addition,
        1,
    )


if 'name="admin_retry_notification_channel"' not in text:

    marker = '''    path(
        "admin/<int:notification_id>/retry/",
        views.admin_retry_notification,
        name="admin_retry_notification",
    ),
'''

    addition = marker + '''

    path(
        "admin/<int:notification_id>/retry/<str:channel>/",
        views.admin_retry_notification_channel,
        name="admin_retry_notification_channel",
    ),
'''

    if marker not in text:

        raise RuntimeError(
            "Could not locate admin retry URL."
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
    "Phase 11E routes added."
)


# ============================================================
# 5. ADMIN LIST TEMPLATE
# ============================================================

ADMIN_LIST.write_text(
r'''
{% extends "dashboard/admin/base.html" %}


{% block admin_content %}

<div class="container-fluid">

    <div class="d-flex justify-content-between align-items-center flex-wrap gap-3 mb-4">

        <div>

            <h1 class="h3 mb-1">
                Notification Operations
            </h1>

            <p class="text-muted mb-0">
                Monitor delivery health, failures and controlled retries.
            </p>

        </div>

    </div>


    <!-- OVERALL METRICS -->

    <div class="row g-3 mb-4">

        <div class="col-md-6 col-xl-2">

            <div class="dashboard-card h-100">

                <div class="text-muted small">
                    Total
                </div>

                <div class="fs-3 fw-bold">
                    {{ stats.total }}
                </div>

            </div>

        </div>


        <div class="col-md-6 col-xl-2">

            <div class="dashboard-card h-100">

                <div class="text-muted small">
                    Sent
                </div>

                <div class="fs-3 fw-bold text-success">
                    {{ stats.sent }}
                </div>

            </div>

        </div>


        <div class="col-md-6 col-xl-2">

            <div class="dashboard-card h-100">

                <div class="text-muted small">
                    Partial
                </div>

                <div class="fs-3 fw-bold text-warning">
                    {{ stats.partial }}
                </div>

            </div>

        </div>


        <div class="col-md-6 col-xl-2">

            <div class="dashboard-card h-100">

                <div class="text-muted small">
                    Failed
                </div>

                <div class="fs-3 fw-bold text-danger">
                    {{ stats.failed }}
                </div>

            </div>

        </div>


        <div class="col-md-6 col-xl-2">

            <div class="dashboard-card h-100">

                <div class="text-muted small">
                    Email Success
                </div>

                <div class="fs-4 fw-bold">
                    {{ stats.email_success_rate }}%
                </div>

                <div class="small text-muted">
                    {{ stats.email_failed }} failed
                </div>

            </div>

        </div>


        <div class="col-md-6 col-xl-2">

            <div class="dashboard-card h-100">

                <div class="text-muted small">
                    SMS Success
                </div>

                <div class="fs-4 fw-bold">
                    {{ stats.sms_success_rate }}%
                </div>

                <div class="small text-muted">
                    {{ stats.sms_failed }} failed
                </div>

            </div>

        </div>

    </div>


    <!-- FILTERS -->

    <div class="dashboard-card mb-4">

        <form method="get" class="row g-3">

            <div class="col-lg-4">

                <label class="form-label">
                    Search
                </label>

                <input
                    class="form-control"
                    name="q"
                    value="{{ search }}"
                    placeholder="Subject, event key, customer..."
                >

            </div>


            <div class="col-lg-2">

                <label class="form-label">
                    Status
                </label>

                <select class="form-select" name="status">

                    <option value="">
                        All
                    </option>

                    <option value="pending"
                        {% if selected_status == "pending" %}selected{% endif %}>
                        Pending
                    </option>

                    <option value="sent"
                        {% if selected_status == "sent" %}selected{% endif %}>
                        Sent
                    </option>

                    <option value="partial"
                        {% if selected_status == "partial" %}selected{% endif %}>
                        Partial
                    </option>

                    <option value="failed"
                        {% if selected_status == "failed" %}selected{% endif %}>
                        Failed
                    </option>

                </select>

            </div>


            <div class="col-lg-2">

                <label class="form-label">
                    Channel
                </label>

                <select class="form-select" name="channel">

                    <option value="">
                        All
                    </option>

                    <option value="email"
                        {% if selected_channel == "email" %}selected{% endif %}>
                        Email
                    </option>

                    <option value="sms"
                        {% if selected_channel == "sms" %}selected{% endif %}>
                        SMS
                    </option>

                    <option value="email_and_sms"
                        {% if selected_channel == "email_and_sms" %}selected{% endif %}>
                        Email + SMS
                    </option>

                </select>

            </div>


            <div class="col-lg-2">

                <label class="form-label">
                    Category
                </label>

                <select class="form-select" name="category">

                    <option value="">
                        All
                    </option>

                    <option value="orders"
                        {% if selected_category == "orders" %}selected{% endif %}>
                        Orders
                    </option>

                    <option value="payments"
                        {% if selected_category == "payments" %}selected{% endif %}>
                        Payments
                    </option>

                    <option value="delivery"
                        {% if selected_category == "delivery" %}selected{% endif %}>
                        Delivery
                    </option>

                    <option value="returns"
                        {% if selected_category == "returns" %}selected{% endif %}>
                        Returns
                    </option>

                    <option value="general"
                        {% if selected_category == "general" %}selected{% endif %}>
                        General
                    </option>

                    <option value="marketing"
                        {% if selected_category == "marketing" %}selected{% endif %}>
                        Marketing
                    </option>

                </select>

            </div>


            <div class="col-lg-2 d-flex align-items-end">

                <button
                    type="submit"
                    class="btn btn-primary w-100"
                >
                    Filter
                </button>

            </div>

        </form>

    </div>


    <!-- TABLE + BULK OPERATIONS -->

    <form
        method="post"
        action="{% url 'admin_bulk_retry_notifications' %}"
    >

        {% csrf_token %}


        <div class="dashboard-card">

            <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-3">

                <div class="small text-muted">

                    Retry limit:
                    <strong>
                        {{ max_channel_attempts }}
                    </strong>
                    provider attempts per channel.

                </div>


                <button
                    type="submit"
                    class="btn btn-sm btn-outline-danger"
                >
                    Retry Selected Failures
                </button>

            </div>


            <div class="table-responsive">

                <table class="table align-middle">

                    <thead>

                        <tr>

                            <th style="width:40px;">
                                Select
                            </th>

                            <th>
                                Customer
                            </th>

                            <th>
                                Notification
                            </th>

                            <th>
                                Category
                            </th>

                            <th>
                                Overall
                            </th>

                            <th>
                                Email
                            </th>

                            <th>
                                SMS
                            </th>

                            <th>
                                Created
                            </th>

                            <th class="text-end">
                                Action
                            </th>

                        </tr>

                    </thead>


                    <tbody>

                        {% for notification in page_obj %}

                            <tr>

                                <td>

                                    {% if notification.status == "failed" or notification.status == "partial" %}

                                        <input
                                            type="checkbox"
                                            class="form-check-input"
                                            name="notification_ids"
                                            value="{{ notification.pk }}"
                                        >

                                    {% endif %}

                                </td>


                                <td>

                                    <strong>
                                        {{ notification.user.username }}
                                    </strong>

                                    {% if notification.user.email %}

                                        <div class="small text-muted">
                                            {{ notification.user.email }}
                                        </div>

                                    {% endif %}

                                </td>


                                <td>

                                    <a
                                        href="{% url 'admin_notification_detail' notification.pk %}"
                                        class="fw-semibold text-decoration-none"
                                    >
                                        {{ notification.subject }}
                                    </a>

                                    <div class="small text-muted">
                                        {{ notification.message|truncatechars:85 }}
                                    </div>

                                    {% if notification.event_key %}

                                        <div class="small text-muted">
                                            {{ notification.event_key }}
                                        </div>

                                    {% endif %}

                                </td>


                                <td>
                                    {{ notification.get_category_display }}
                                </td>


                                <td>

                                    {% if notification.status == "sent" %}

                                        <span class="badge bg-success">
                                            Sent
                                        </span>

                                    {% elif notification.status == "failed" %}

                                        <span class="badge bg-danger">
                                            Failed
                                        </span>

                                    {% elif notification.status == "partial" %}

                                        <span class="badge bg-warning text-dark">
                                            Partial
                                        </span>

                                    {% else %}

                                        <span class="badge bg-secondary">
                                            Pending
                                        </span>

                                    {% endif %}

                                </td>


                                <td>

                                    {% if notification.email_status == "sent" %}

                                        <span class="badge bg-success">
                                            Sent
                                        </span>

                                    {% elif notification.email_status == "failed" %}

                                        <span class="badge bg-danger">
                                            Failed
                                        </span>

                                    {% elif notification.email_status == "skipped" %}

                                        <span class="badge bg-secondary">
                                            Skipped
                                        </span>

                                    {% else %}

                                        <span class="badge bg-light text-dark">
                                            {{ notification.email_status }}
                                        </span>

                                    {% endif %}

                                    <div class="small text-muted mt-1">
                                        {{ notification.email_attempts }}/{{ max_channel_attempts }}
                                    </div>

                                </td>


                                <td>

                                    {% if notification.sms_status == "sent" %}

                                        <span class="badge bg-success">
                                            Sent
                                        </span>

                                    {% elif notification.sms_status == "failed" %}

                                        <span class="badge bg-danger">
                                            Failed
                                        </span>

                                    {% elif notification.sms_status == "skipped" %}

                                        <span class="badge bg-secondary">
                                            Skipped
                                        </span>

                                    {% else %}

                                        <span class="badge bg-light text-dark">
                                            {{ notification.sms_status }}
                                        </span>

                                    {% endif %}

                                    <div class="small text-muted mt-1">
                                        {{ notification.sms_attempts }}/{{ max_channel_attempts }}
                                    </div>

                                </td>


                                <td>
                                    {{ notification.created_at|date:"d M Y H:i" }}
                                </td>


                                <td class="text-end">

                                    <a
                                        href="{% url 'admin_notification_detail' notification.pk %}"
                                        class="btn btn-sm btn-outline-primary"
                                    >
                                        View
                                    </a>

                                </td>

                            </tr>


                        {% empty %}

                            <tr>

                                <td
                                    colspan="9"
                                    class="text-center text-muted py-5"
                                >
                                    No notifications found.
                                </td>

                            </tr>

                        {% endfor %}

                    </tbody>

                </table>

            </div>

        </div>

    </form>


    {% if page_obj.has_other_pages %}

        <nav class="mt-4">

            <ul class="pagination">

                {% if page_obj.has_previous %}

                    <li class="page-item">

                        <a
                            class="page-link"
                            href="?page={{ page_obj.previous_page_number }}&status={{ selected_status }}&channel={{ selected_channel }}&category={{ selected_category }}&q={{ search|urlencode }}"
                        >
                            Previous
                        </a>

                    </li>

                {% endif %}


                <li class="page-item active">

                    <span class="page-link">
                        {{ page_obj.number }}
                    </span>

                </li>


                {% if page_obj.has_next %}

                    <li class="page-item">

                        <a
                            class="page-link"
                            href="?page={{ page_obj.next_page_number }}&status={{ selected_status }}&channel={{ selected_channel }}&category={{ selected_category }}&q={{ search|urlencode }}"
                        >
                            Next
                        </a>

                    </li>

                {% endif %}

            </ul>

        </nav>

    {% endif %}

</div>

{% endblock %}
'''.strip() + "\n",
encoding="utf-8",
)

print(
    "Admin notification operations dashboard created."
)


# ============================================================
# 6. ADMIN DETAIL TEMPLATE
# ============================================================

ADMIN_DETAIL.write_text(
r'''
{% extends "dashboard/admin/base.html" %}


{% block admin_content %}

<div class="container-fluid">

    <div class="d-flex justify-content-between align-items-center flex-wrap gap-3 mb-4">

        <div>

            <a
                href="{% url 'admin_notifications' %}"
                class="text-decoration-none"
            >
                ← Notifications
            </a>

            <h1 class="h3 mt-2 mb-1">
                Notification Detail
            </h1>

            <p class="text-muted mb-0">
                {{ notification.subject }}
            </p>

        </div>


        {% if notification.status == "failed" or notification.status == "partial" %}

            <form
                method="post"
                action="{% url 'admin_retry_notification' notification.pk %}"
            >

                {% csrf_token %}

                <button
                    type="submit"
                    class="btn btn-outline-danger"
                >
                    Retry Available Failed Channels
                </button>

            </form>

        {% endif %}

    </div>


    <div class="row g-4">

        <div class="col-xl-8">

            <div class="dashboard-card mb-4">

                <h5 class="mb-3">
                    Notification
                </h5>


                <dl class="row mb-0">

                    <dt class="col-md-3">
                        Customer
                    </dt>

                    <dd class="col-md-9">
                        {{ notification.user.username }}

                        {% if notification.user.email %}
                            — {{ notification.user.email }}
                        {% endif %}
                    </dd>


                    <dt class="col-md-3">
                        Category
                    </dt>

                    <dd class="col-md-9">
                        {{ notification.get_category_display }}
                    </dd>


                    <dt class="col-md-3">
                        Requested channel
                    </dt>

                    <dd class="col-md-9">
                        {{ notification.channel }}
                    </dd>


                    <dt class="col-md-3">
                        Event key
                    </dt>

                    <dd class="col-md-9">
                        {{ notification.event_key|default:"—" }}
                    </dd>


                    <dt class="col-md-3">
                        Overall status
                    </dt>

                    <dd class="col-md-9">

                        {% if notification.status == "sent" %}

                            <span class="badge bg-success">
                                Sent
                            </span>

                        {% elif notification.status == "failed" %}

                            <span class="badge bg-danger">
                                Failed
                            </span>

                        {% elif notification.status == "partial" %}

                            <span class="badge bg-warning text-dark">
                                Partial
                            </span>

                        {% else %}

                            <span class="badge bg-secondary">
                                Pending
                            </span>

                        {% endif %}

                    </dd>


                    <dt class="col-md-3">
                        Created
                    </dt>

                    <dd class="col-md-9">
                        {{ notification.created_at|date:"d M Y H:i:s" }}
                    </dd>


                    <dt class="col-md-3">
                        Updated
                    </dt>

                    <dd class="col-md-9">
                        {{ notification.updated_at|date:"d M Y H:i:s" }}
                    </dd>

                </dl>

            </div>


            <div class="dashboard-card mb-4">

                <h5>
                    Email Message
                </h5>

                <p class="text-muted">
                    {{ notification.message|linebreaksbr }}
                </p>

            </div>


            {% if notification.sms_message %}

                <div class="dashboard-card">

                    <h5>
                        SMS Message
                    </h5>

                    <p class="text-muted mb-0">
                        {{ notification.sms_message }}
                    </p>

                </div>

            {% endif %}

        </div>


        <div class="col-xl-4">

            <!-- EMAIL -->

            <div class="dashboard-card mb-4">

                <div class="d-flex justify-content-between align-items-center mb-3">

                    <h5 class="mb-0">
                        Email Delivery
                    </h5>


                    {% if notification.email_status == "sent" %}

                        <span class="badge bg-success">
                            Sent
                        </span>

                    {% elif notification.email_status == "failed" %}

                        <span class="badge bg-danger">
                            Failed
                        </span>

                    {% elif notification.email_status == "skipped" %}

                        <span class="badge bg-secondary">
                            Skipped
                        </span>

                    {% else %}

                        <span class="badge bg-light text-dark">
                            {{ notification.email_status }}
                        </span>

                    {% endif %}

                </div>


                <p class="mb-2">

                    Attempts:

                    <strong>
                        {{ notification.email_attempts }}
                        /
                        {{ max_channel_attempts }}
                    </strong>

                </p>


                <p class="mb-2">

                    Sent:

                    <strong>
                        {% if notification.email_sent_at %}
                            {{ notification.email_sent_at|date:"d M Y H:i:s" }}
                        {% else %}
                            —
                        {% endif %}
                    </strong>

                </p>


                {% if notification.email_error %}

                    <div class="alert alert-danger small">
                        {{ notification.email_error }}
                    </div>

                {% endif %}


                {% if email_retry_available %}

                    <form
                        method="post"
                        action="{% url 'admin_retry_notification_channel' notification.pk 'email' %}"
                    >

                        {% csrf_token %}

                        <button
                            type="submit"
                            class="btn btn-outline-danger w-100"
                        >
                            Retry Email Only
                        </button>

                    </form>

                {% elif notification.email_status == "failed" %}

                    <div class="alert alert-warning small mb-0">
                        Email retry limit reached.
                    </div>

                {% endif %}

            </div>


            <!-- SMS -->

            <div class="dashboard-card mb-4">

                <div class="d-flex justify-content-between align-items-center mb-3">

                    <h5 class="mb-0">
                        SMS Delivery
                    </h5>


                    {% if notification.sms_status == "sent" %}

                        <span class="badge bg-success">
                            Sent
                        </span>

                    {% elif notification.sms_status == "failed" %}

                        <span class="badge bg-danger">
                            Failed
                        </span>

                    {% elif notification.sms_status == "skipped" %}

                        <span class="badge bg-secondary">
                            Skipped
                        </span>

                    {% else %}

                        <span class="badge bg-light text-dark">
                            {{ notification.sms_status }}
                        </span>

                    {% endif %}

                </div>


                <p class="mb-2">

                    Attempts:

                    <strong>
                        {{ notification.sms_attempts }}
                        /
                        {{ max_channel_attempts }}
                    </strong>

                </p>


                <p class="mb-2">

                    Sent:

                    <strong>
                        {% if notification.sms_sent_at %}
                            {{ notification.sms_sent_at|date:"d M Y H:i:s" }}
                        {% else %}
                            —
                        {% endif %}
                    </strong>

                </p>


                {% if notification.sms_error %}

                    <div class="alert alert-danger small">
                        {{ notification.sms_error }}
                    </div>

                {% endif %}


                {% if sms_retry_available %}

                    <form
                        method="post"
                        action="{% url 'admin_retry_notification_channel' notification.pk 'sms' %}"
                    >

                        {% csrf_token %}

                        <button
                            type="submit"
                            class="btn btn-outline-danger w-100"
                        >
                            Retry SMS Only
                        </button>

                    </form>

                {% elif notification.sms_status == "failed" %}

                    <div class="alert alert-warning small mb-0">
                        SMS retry limit reached.
                    </div>

                {% endif %}

            </div>


            {% if order %}

                <div class="dashboard-card">

                    <h5>
                        Related Order
                    </h5>

                    <div class="mb-2">
                        {{ order.order_number }}
                    </div>

                    <a
                        href="{% url 'admin_order_detail' order.order_number %}"
                        class="btn btn-outline-primary btn-sm"
                    >
                        Open Order
                    </a>

                </div>

            {% endif %}

        </div>

    </div>

</div>

{% endblock %}
'''.strip() + "\n",
encoding="utf-8",
)

print(
    "Admin notification detail page created."
)


# ============================================================
# 7. TESTS
# ============================================================

TESTS.write_text(
r'''
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
'''.strip() + "\n",
encoding="utf-8",
)


print(
    "Phase 11E tests created."
)


print()
print("=" * 72)
print("PHASE 11E INSTALLED")
print("=" * 72)
print()
print("Added:")
print("  Admin notification detail page")
print("  Email-only retry")
print("  SMS-only retry")
print("  Retry failed channels together")
print("  Maximum 3 attempts per provider channel")
print("  Bulk retry for selected failures")
print("  Maximum 50 rows per bulk request")
print("  Email delivery success metric")
print("  SMS delivery success metric")
print("  Per-channel failure visibility")
print("  Retry-cap visibility")
print()
print("No migration required.")
