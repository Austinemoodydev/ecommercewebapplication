from pathlib import Path
import shutil


ROOT = Path.cwd()

MODELS = ROOT / "notifications" / "models.py"
VIEWS = ROOT / "notifications" / "views.py"
URLS = ROOT / "notifications" / "urls.py"
CONTEXT = ROOT / "notifications" / "context_processors.py"

SETTINGS = ROOT / "config" / "settings.py"
CONFIG_URLS = ROOT / "config" / "urls.py"

NAVBAR = ROOT / "templates" / "includes" / "navbar.html"
ADMIN_BASE = ROOT / "templates" / "dashboard" / "admin" / "base.html"

CUSTOMER_TEMPLATE = (
    ROOT
    / "templates"
    / "notifications"
    / "customer_list.html"
)

ADMIN_TEMPLATE = (
    ROOT
    / "templates"
    / "notifications"
    / "admin_list.html"
)

TESTS = ROOT / "notifications" / "test_phase11a.py"


# ============================================================
# VALIDATE
# ============================================================

for path in [
    MODELS,
    VIEWS,
    SETTINGS,
    CONFIG_URLS,
    NAVBAR,
    ADMIN_BASE,
]:

    if not path.exists():

        raise RuntimeError(
            f"Missing required file: {path}"
        )


CUSTOMER_TEMPLATE.parent.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# BACKUPS
# ============================================================

for path in [
    MODELS,
    VIEWS,
    SETTINGS,
    CONFIG_URLS,
    NAVBAR,
    ADMIN_BASE,
]:

    backup = Path(
        str(path)
        + ".phase11abackup"
    )

    if not backup.exists():

        shutil.copy2(
            path,
            backup,
        )


# ============================================================
# 1. ADD READ STATE TO NOTIFICATION MODEL
# ============================================================

text = MODELS.read_text(
    encoding="utf-8-sig"
)


if "read_at = models.DateTimeField" not in text:

    marker = (
        "\tsent_at = models.DateTimeField"
        "(null=True, blank=True)\n"
    )

    replacement = marker + (
        "\tread_at = models.DateTimeField"
        "(null=True, blank=True, db_index=True)\n"
    )


    if marker not in text:

        # fallback spaces version
        marker = (
            "    sent_at = models.DateTimeField"
            "(null=True, blank=True)\n"
        )

        replacement = marker + (
            "    read_at = models.DateTimeField"
            "(null=True, blank=True, db_index=True)\n"
        )


    if marker not in text:

        raise RuntimeError(
            "Could not locate sent_at field "
            "in notifications/models.py"
        )


    text = text.replace(
        marker,
        replacement,
        1,
    )


if "def is_read(self):" not in text:

    marker = (
        "\tdef __str__(self):\n"
        "\t\treturn f\"{self.subject} - {self.status}\"\n"
    )


    replacement = (
        "\t@property\n"
        "\tdef is_read(self):\n"
        "\t\treturn self.read_at is not None\n\n"
        + marker
    )


    if marker not in text:

        marker = (
            "    def __str__(self):\n"
            "        return f\"{self.subject} - {self.status}\"\n"
        )

        replacement = (
            "    @property\n"
            "    def is_read(self):\n"
            "        return self.read_at is not None\n\n"
            + marker
        )


    if marker not in text:

        raise RuntimeError(
            "Could not locate Notification.__str__."
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
    "Notification read tracking added."
)


# ============================================================
# 2. NOTIFICATION VIEWS
# ============================================================

VIEWS.write_text(
r'''
from django.contrib import messages

from django.contrib.admin.views.decorators import (
    staff_member_required,
)

from django.contrib.auth.decorators import (
    login_required,
)

from django.core.paginator import Paginator

from django.db.models import Q

from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from django.utils import timezone

from django.views.decorators.http import (
    require_POST,
)

from notifications.models import (
    Notification,
)

from notifications.tasks import (
    retry_notification,
)


# ============================================================
# CUSTOMER
# ============================================================

@login_required
def customer_notifications(
    request,
):

    queryset = (
        Notification.objects
        .filter(
            user=request.user
        )
        .order_by(
            "-created_at"
        )
    )


    filter_value = (
        request.GET.get(
            "filter",
            "all",
        )
        .strip()
        .lower()
    )


    if filter_value == "unread":

        queryset = queryset.filter(
            read_at__isnull=True
        )

    elif filter_value == "read":

        queryset = queryset.filter(
            read_at__isnull=False
        )

    elif filter_value == "failed":

        queryset = queryset.filter(
            status="failed"
        )


    paginator = Paginator(
        queryset,
        20,
    )

    page_obj = paginator.get_page(
        request.GET.get(
            "page"
        )
    )


    return render(
        request,
        "notifications/customer_list.html",
        {
            "page_obj":
                page_obj,

            "filter_value":
                filter_value,

            "unread_count":
                Notification.objects
                .filter(
                    user=request.user,
                    read_at__isnull=True,
                )
                .count(),
        },
    )


@login_required
@require_POST
def customer_notification_mark_read(
    request,
    notification_id,
):

    notification = get_object_or_404(
        Notification,
        pk=notification_id,
        user=request.user,
    )


    if notification.read_at is None:

        notification.read_at = (
            timezone.now()
        )

        notification.save(
            update_fields=[
                "read_at",
                "updated_at",
            ]
        )


    return redirect(
        request.POST.get(
            "next"
        )
        or "customer_notifications"
    )


@login_required
@require_POST
def customer_notifications_mark_all_read(
    request,
):

    (
        Notification.objects
        .filter(
            user=request.user,
            read_at__isnull=True,
        )
        .update(
            read_at=timezone.now()
        )
    )


    messages.success(
        request,
        "All notifications marked as read.",
    )


    return redirect(
        "customer_notifications"
    )


# ============================================================
# ADMIN
# ============================================================

@staff_member_required
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
            ""
        )
        .strip()
        .lower()
    )


    channel = (
        request.GET.get(
            "channel",
            ""
        )
        .strip()
    )


    search = (
        request.GET.get(
            "q",
            ""
        )
        .strip()
    )


    if status in {
        "pending",
        "sent",
        "failed",
    }:

        queryset = queryset.filter(
            status=status
        )


    if channel:

        queryset = queryset.filter(
            channel=channel
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


    stats = {

        "total":
            Notification.objects.count(),

        "pending":
            Notification.objects.filter(
                status="pending"
            ).count(),

        "sent":
            Notification.objects.filter(
                status="sent"
            ).count(),

        "failed":
            Notification.objects.filter(
                status="failed"
            ).count(),
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

            "search":
                search,
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
        status="failed",
    )


    if not notification.order_id:

        messages.error(
            request,
            "This notification has no linked "
            "order and cannot be retried automatically.",
        )

        return redirect(
            "admin_notifications"
        )


    retry_notification.delay(
        notification.pk
    )


    messages.success(
        request,
        "Notification retry queued.",
    )


    return redirect(
        "admin_notifications"
    )
'''.strip() + "\n",
encoding="utf-8",
)

print(
    "Notification center views created."
)


# ============================================================
# 3. NOTIFICATION URLS
# ============================================================

URLS.write_text(
r'''
from django.urls import path

from notifications import views


urlpatterns = [

    # ========================================================
    # CUSTOMER
    # ========================================================

    path(
        "",
        views.customer_notifications,
        name="customer_notifications",
    ),

    path(
        "<int:notification_id>/read/",
        views.customer_notification_mark_read,
        name="customer_notification_mark_read",
    ),

    path(
        "mark-all-read/",
        views.customer_notifications_mark_all_read,
        name="customer_notifications_mark_all_read",
    ),


    # ========================================================
    # ADMIN
    # ========================================================

    path(
        "admin/",
        views.admin_notifications,
        name="admin_notifications",
    ),

    path(
        "admin/<int:notification_id>/retry/",
        views.admin_retry_notification,
        name="admin_retry_notification",
    ),

]
'''.strip() + "\n",
encoding="utf-8",
)

print(
    "Notification routes created."
)


# ============================================================
# 4. CONTEXT PROCESSOR FOR UNREAD BADGE
# ============================================================

CONTEXT.write_text(
r'''
def notification_counts(
    request,
):

    if not request.user.is_authenticated:

        return {
            "notification_unread_count": 0,
        }


    from notifications.models import (
        Notification,
    )


    return {

        "notification_unread_count":
            Notification.objects
            .filter(
                user=request.user,
                read_at__isnull=True,
            )
            .count(),
    }
'''.strip() + "\n",
encoding="utf-8",
)

print(
    "Notification badge context processor created."
)


# ============================================================
# 5. REGISTER CONTEXT PROCESSOR
# ============================================================

text = SETTINGS.read_text(
    encoding="utf-8-sig"
)


context_entry = (
    "'notifications.context_processors."
    "notification_counts',"
)


if context_entry not in text:

    marker = (
        "'django.contrib.messages.context_processors.messages',"
    )


    if marker not in text:

        marker = (
            '"django.contrib.messages.context_processors.messages",'
        )


    if marker not in text:

        raise RuntimeError(
            "Could not locate Django template "
            "context processors."
        )


    text = text.replace(
        marker,
        marker
        + "\n                "
        + context_entry,
        1,
    )


SETTINGS.write_text(
    text,
    encoding="utf-8",
)

print(
    "Notification context processor registered."
)


# ============================================================
# 6. INCLUDE NOTIFICATION URLS
# ============================================================

text = CONFIG_URLS.read_text(
    encoding="utf-8-sig"
)


if (
    'path("notifications/", include("notifications.urls"))'
    not in text
):

    if "include" not in text.splitlines()[0:20].__str__():

        # Most projects already import include.
        pass


    marker = "urlpatterns = ["

    if marker not in text:

        raise RuntimeError(
            "Could not locate urlpatterns "
            "in config/urls.py"
        )


    text = text.replace(
        marker,
        marker
        + '\n    path("notifications/", include("notifications.urls")),',
        1,
    )


CONFIG_URLS.write_text(
    text,
    encoding="utf-8",
)

print(
    "Notification URLs included."
)


# ============================================================
# 7. CUSTOMER NAVBAR NOTIFICATION ICON
# ============================================================

text = NAVBAR.read_text(
    encoding="utf-8-sig"
)


if "customer_notifications" not in text:

    marker = (
        '<li class="nav-item"><a href="{% url \'wishlist\' %}"'
    )


    block = r'''<li class="nav-item">
          <a
            href="{% url 'customer_notifications' %}"
            class="nav-icon position-relative"
            aria-label="Notifications"
          >
            <i class="bi bi-bell"></i>

            {% if notification_unread_count %}
              <span class="count-badge">
                {{ notification_unread_count }}
              </span>
            {% endif %}
          </a>
        </li>
        '''


    if marker not in text:

        raise RuntimeError(
            "Could not locate wishlist navbar item."
        )


    text = text.replace(
        marker,
        block + marker,
        1,
    )


NAVBAR.write_text(
    text,
    encoding="utf-8",
)

print(
    "Customer notification bell added."
)


# ============================================================
# 8. ADMIN SIDEBAR LINK
# ============================================================

text = ADMIN_BASE.read_text(
    encoding="utf-8-sig"
)


old = r'''            <!-- NOTIFICATIONS -->

            <a
                href="#"
                class="sidebar-link"
            >

                <i class="bi bi-bell"></i>

                <span>
                    Notifications
                </span>

            </a>
'''


new = r'''            <!-- NOTIFICATIONS -->

            <a
                href="{% url 'admin_notifications' %}"
                class="
                    sidebar-link
                    {% if request.resolver_match.url_name == 'admin_notifications' %}
                        active
                    {% endif %}
                "
            >

                <i class="bi bi-bell"></i>

                <span>
                    Notifications
                </span>

            </a>
'''


if old in text:

    text = text.replace(
        old,
        new,
        1,
    )

elif "admin_notifications" not in text:

    raise RuntimeError(
        "Could not locate admin notification placeholder."
    )


ADMIN_BASE.write_text(
    text,
    encoding="utf-8",
)

print(
    "Admin notifications sidebar activated."
)


# ============================================================
# 9. CUSTOMER NOTIFICATION TEMPLATE
# ============================================================

CUSTOMER_TEMPLATE.write_text(
r'''
{% extends "base.html" %}


{% block content %}

<div class="py-4">

    <div
        class="
            d-flex
            justify-content-between
            align-items-center
            flex-wrap
            gap-3
            mb-4
        "
    >

        <div>

            <h2 class="mb-1">
                Notifications
            </h2>

            <p class="text-muted mb-0">
                Order, payment, delivery and account updates.
            </p>

        </div>


        {% if unread_count %}

            <form
                method="post"
                action="{% url 'customer_notifications_mark_all_read' %}"
            >

                {% csrf_token %}

                <button
                    class="btn btn-outline-primary"
                    type="submit"
                >
                    Mark all as read
                </button>

            </form>

        {% endif %}

    </div>


    <div class="mb-4">

        <a
            href="{% url 'customer_notifications' %}"
            class="
                btn
                btn-sm
                {% if filter_value == 'all' %}
                    btn-primary
                {% else %}
                    btn-outline-primary
                {% endif %}
            "
        >
            All
        </a>


        <a
            href="{% url 'customer_notifications' %}?filter=unread"
            class="
                btn
                btn-sm
                {% if filter_value == 'unread' %}
                    btn-primary
                {% else %}
                    btn-outline-primary
                {% endif %}
            "
        >
            Unread
        </a>


        <a
            href="{% url 'customer_notifications' %}?filter=read"
            class="
                btn
                btn-sm
                {% if filter_value == 'read' %}
                    btn-primary
                {% else %}
                    btn-outline-primary
                {% endif %}
            "
        >
            Read
        </a>


        <a
            href="{% url 'customer_notifications' %}?filter=failed"
            class="
                btn
                btn-sm
                {% if filter_value == 'failed' %}
                    btn-danger
                {% else %}
                    btn-outline-danger
                {% endif %}
            "
        >
            Failed delivery
        </a>

    </div>


    <div class="card border-0 shadow-sm">

        <div class="list-group list-group-flush">

            {% for notification in page_obj %}

                <div
                    class="
                        list-group-item
                        py-4
                        {% if not notification.read_at %}
                            bg-light
                        {% endif %}
                    "
                >

                    <div
                        class="
                            d-flex
                            justify-content-between
                            gap-3
                        "
                    >

                        <div>

                            <div
                                class="
                                    d-flex
                                    align-items-center
                                    gap-2
                                    mb-1
                                "
                            >

                                {% if not notification.read_at %}

                                    <span
                                        class="badge bg-primary"
                                    >
                                        New
                                    </span>

                                {% endif %}


                                {% if notification.status == "failed" %}

                                    <span
                                        class="badge bg-danger"
                                    >
                                        Delivery failed
                                    </span>

                                {% elif notification.status == "pending" %}

                                    <span
                                        class="
                                            badge
                                            bg-warning
                                            text-dark
                                        "
                                    >
                                        Pending
                                    </span>

                                {% else %}

                                    <span
                                        class="badge bg-success"
                                    >
                                        Sent
                                    </span>

                                {% endif %}

                            </div>


                            <h5 class="mb-2">

                                {{ notification.subject }}

                            </h5>


                            <p class="mb-2">

                                {{ notification.message }}

                            </p>


                            <div class="small text-muted">

                                {{ notification.created_at|date:"d M Y H:i" }}

                                ·

                                {{ notification.channel }}

                            </div>

                        </div>


                        {% if not notification.read_at %}

                            <form
                                method="post"
                                action="{% url 'customer_notification_mark_read' notification.pk %}"
                            >

                                {% csrf_token %}

                                <input
                                    type="hidden"
                                    name="next"
                                    value="{{ request.get_full_path }}"
                                >

                                <button
                                    class="
                                        btn
                                        btn-sm
                                        btn-outline-secondary
                                    "
                                    type="submit"
                                >
                                    Mark read
                                </button>

                            </form>

                        {% endif %}

                    </div>

                </div>


            {% empty %}

                <div
                    class="
                        text-center
                        text-muted
                        p-5
                    "
                >

                    No notifications found.

                </div>

            {% endfor %}

        </div>

    </div>


    {% if page_obj.paginator.num_pages > 1 %}

        <nav class="mt-4">

            <ul class="pagination">

                {% if page_obj.has_previous %}

                    <li class="page-item">

                        <a
                            class="page-link"
                            href="?page={{ page_obj.previous_page_number }}&filter={{ filter_value }}"
                        >
                            Previous
                        </a>

                    </li>

                {% endif %}


                <li class="page-item disabled">

                    <span class="page-link">

                        Page
                        {{ page_obj.number }}
                        of
                        {{ page_obj.paginator.num_pages }}

                    </span>

                </li>


                {% if page_obj.has_next %}

                    <li class="page-item">

                        <a
                            class="page-link"
                            href="?page={{ page_obj.next_page_number }}&filter={{ filter_value }}"
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
    "Customer notification UI created."
)


# ============================================================
# 10. ADMIN NOTIFICATION TEMPLATE
# ============================================================

ADMIN_TEMPLATE.write_text(
r'''
{% extends "dashboard/admin/base.html" %}


{% block admin_content %}

<div class="container-fluid">

    <div
        class="
            d-flex
            justify-content-between
            align-items-center
            flex-wrap
            gap-3
            mb-4
        "
    >

        <div>

            <h1 class="h3 mb-1">
                Notifications
            </h1>

            <p class="text-muted mb-0">
                Monitor customer notification delivery and failures.
            </p>

        </div>

    </div>


    <div class="row g-3 mb-4">

        <div class="col-md-3">

            <div class="dashboard-card h-100">

                <div class="text-muted small">
                    Total
                </div>

                <div class="fs-3 fw-bold">
                    {{ stats.total }}
                </div>

            </div>

        </div>


        <div class="col-md-3">

            <div class="dashboard-card h-100">

                <div class="text-muted small">
                    Sent
                </div>

                <div class="fs-3 fw-bold">
                    {{ stats.sent }}
                </div>

            </div>

        </div>


        <div class="col-md-3">

            <div class="dashboard-card h-100">

                <div class="text-muted small">
                    Pending
                </div>

                <div class="fs-3 fw-bold">
                    {{ stats.pending }}
                </div>

            </div>

        </div>


        <div class="col-md-3">

            <div class="dashboard-card h-100">

                <div class="text-muted small">
                    Failed
                </div>

                <div class="fs-3 fw-bold">
                    {{ stats.failed }}
                </div>

            </div>

        </div>

    </div>


    <div class="dashboard-card mb-4">

        <form
            method="get"
            class="row g-3"
        >

            <div class="col-lg-5">

                <label class="form-label">
                    Search
                </label>

                <input
                    class="form-control"
                    name="q"
                    value="{{ search }}"
                    placeholder="Subject, message, customer..."
                >

            </div>


            <div class="col-lg-3">

                <label class="form-label">
                    Status
                </label>

                <select
                    class="form-select"
                    name="status"
                >

                    <option value="">
                        All statuses
                    </option>

                    <option
                        value="pending"
                        {% if selected_status == "pending" %}
                            selected
                        {% endif %}
                    >
                        Pending
                    </option>

                    <option
                        value="sent"
                        {% if selected_status == "sent" %}
                            selected
                        {% endif %}
                    >
                        Sent
                    </option>

                    <option
                        value="failed"
                        {% if selected_status == "failed" %}
                            selected
                        {% endif %}
                    >
                        Failed
                    </option>

                </select>

            </div>


            <div class="col-lg-2">

                <label class="form-label">
                    Channel
                </label>

                <select
                    class="form-select"
                    name="channel"
                >

                    <option value="">
                        All
                    </option>

                    <option
                        value="email"
                        {% if selected_channel == "email" %}
                            selected
                        {% endif %}
                    >
                        Email
                    </option>

                    <option
                        value="sms"
                        {% if selected_channel == "sms" %}
                            selected
                        {% endif %}
                    >
                        SMS
                    </option>

                    <option
                        value="email_and_sms"
                        {% if selected_channel == "email_and_sms" %}
                            selected
                        {% endif %}
                    >
                        Email + SMS
                    </option>

                </select>

            </div>


            <div
                class="
                    col-lg-2
                    d-flex
                    align-items-end
                "
            >

                <button
                    class="btn btn-primary w-100"
                    type="submit"
                >
                    Filter
                </button>

            </div>

        </form>

    </div>


    <div class="dashboard-card">

        <div class="table-responsive">

            <table class="table align-middle">

                <thead>

                    <tr>

                        <th>
                            Customer
                        </th>

                        <th>
                            Notification
                        </th>

                        <th>
                            Channel
                        </th>

                        <th>
                            Status
                        </th>

                        <th>
                            Attempts
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

                                <strong>
                                    {{ notification.subject }}
                                </strong>

                                <div class="small text-muted">

                                    {{ notification.message|truncatechars:90 }}

                                </div>


                                {% if notification.last_error %}

                                    <div
                                        class="
                                            small
                                            text-danger
                                            mt-1
                                        "
                                    >

                                        {{ notification.last_error|truncatechars:120 }}

                                    </div>

                                {% endif %}

                            </td>


                            <td>

                                {{ notification.channel }}

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

                                {% else %}

                                    <span
                                        class="
                                            badge
                                            bg-warning
                                            text-dark
                                        "
                                    >
                                        Pending
                                    </span>

                                {% endif %}

                            </td>


                            <td>
                                {{ notification.attempts }}
                            </td>


                            <td>

                                {{ notification.created_at|date:"d M Y H:i" }}

                            </td>


                            <td class="text-end">

                                {% if notification.status == "failed" %}

                                    <form
                                        method="post"
                                        action="{% url 'admin_retry_notification' notification.pk %}"
                                    >

                                        {% csrf_token %}

                                        <button
                                            type="submit"
                                            class="
                                                btn
                                                btn-sm
                                                btn-outline-danger
                                            "
                                        >
                                            Retry
                                        </button>

                                    </form>

                                {% else %}

                                    <span class="text-muted">
                                        —
                                    </span>

                                {% endif %}

                            </td>

                        </tr>


                    {% empty %}

                        <tr>

                            <td
                                colspan="7"
                                class="
                                    text-center
                                    text-muted
                                    py-5
                                "
                            >
                                No notifications found.
                            </td>

                        </tr>

                    {% endfor %}

                </tbody>

            </table>

        </div>

    </div>

</div>

{% endblock %}
'''.strip() + "\n",
encoding="utf-8",
)

print(
    "Admin notification UI created."
)


# ============================================================
# 11. TESTS
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


User = get_user_model()


class Phase11ANotificationCenterTests(
    TestCase
):

    def setUp(self):

        self.customer = (
            User.objects.create_user(
                username="phase11customer",
                password="pass12345",
                email="phase11@example.com",
                role=User.CUSTOMER,
            )
        )


        self.other = (
            User.objects.create_user(
                username="phase11other",
                password="pass12345",
                role=User.CUSTOMER,
            )
        )


        self.staff = (
            User.objects.create_user(
                username="phase11staff",
                password="pass12345",
                role=User.ADMIN,
                is_staff=True,
            )
        )


        self.notification = (
            Notification.objects.create(
                user=self.customer,
                order_id=101,
                channel="email",
                subject="Order shipped",
                message=(
                    "Your order has been shipped."
                ),
                status="sent",
            )
        )


    def test_customer_sees_own_notification(
        self
    ):

        self.client.login(
            username="phase11customer",
            password="pass12345",
        )


        response = self.client.get(
            reverse(
                "customer_notifications"
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        self.assertContains(
            response,
            "Order shipped",
        )


    def test_customer_does_not_see_another_users_notification(
        self
    ):

        Notification.objects.create(
            user=self.other,
            subject="Private notification",
            message="Other customer only.",
            status="sent",
        )


        self.client.login(
            username="phase11customer",
            password="pass12345",
        )


        response = self.client.get(
            reverse(
                "customer_notifications"
            )
        )


        self.assertNotContains(
            response,
            "Private notification",
        )


    def test_customer_can_mark_notification_read(
        self
    ):

        self.client.login(
            username="phase11customer",
            password="pass12345",
        )


        response = self.client.post(
            reverse(
                "customer_notification_mark_read",
                args=[
                    self.notification.pk
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            302,
        )


        self.notification.refresh_from_db()


        self.assertIsNotNone(
            self.notification.read_at
        )


    def test_customer_cannot_mark_other_notification_read(
        self
    ):

        other_notification = (
            Notification.objects.create(
                user=self.other,
                subject="Other",
                message="Other",
                status="sent",
            )
        )


        self.client.login(
            username="phase11customer",
            password="pass12345",
        )


        response = self.client.post(
            reverse(
                "customer_notification_mark_read",
                args=[
                    other_notification.pk
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            404,
        )


    def test_staff_can_view_admin_notification_center(
        self
    ):

        self.client.login(
            username="phase11staff",
            password="pass12345",
        )


        response = self.client.get(
            reverse(
                "admin_notifications"
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        self.assertContains(
            response,
            "Order shipped",
        )


    @patch(
        "notifications.views.retry_notification.delay"
    )
    def test_staff_can_queue_failed_notification_retry(
        self,
        mocked_delay,
    ):

        failed = (
            Notification.objects.create(
                user=self.customer,
                order_id=200,
                subject="Payment received",
                message="Payment notification.",
                status="failed",
                last_error="SMTP unavailable",
            )
        )


        self.client.login(
            username="phase11staff",
            password="pass12345",
        )


        response = self.client.post(
            reverse(
                "admin_retry_notification",
                args=[
                    failed.pk
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            302,
        )


        mocked_delay.assert_called_once_with(
            failed.pk
        )
'''.strip() + "\n",
encoding="utf-8",
)

print(
    "Phase 11A tests created."
)


print()
print("=" * 72)
print("PHASE 11A NOTIFICATION CENTER INSTALLED")
print("=" * 72)
print()
print("Added:")
print("  Customer notification center")
print("  Read/unread state")
print("  Mark one notification read")
print("  Mark all notifications read")
print("  Navbar unread badge")
print("  Admin notification monitoring")
print("  Sent/pending/failed statistics")
print("  Search and filters")
print("  Failed notification retry")
print("  Admin sidebar link")
print()
print("Migration required.")
