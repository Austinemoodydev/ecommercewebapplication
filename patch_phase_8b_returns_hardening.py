from pathlib import Path
import re
import shutil

ROOT = Path.cwd()

ORDER_MODELS = ROOT / "orders" / "models.py"
PAYMENT_MODELS = ROOT / "payments" / "models.py"
CUSTOMER_RETURNS = ROOT / "payments" / "customer_returns.py"
ADMIN_RETURNS = ROOT / "payments" / "returns_admin_views.py"
PAYMENT_URLS = ROOT / "payments" / "urls.py"

SETTINGS = ROOT / "config" / "settings.py"

CUSTOMER_ORDER = (
    ROOT
    / "templates"
    / "dashboard"
    / "order_detail.html"
)

PAYMENTS = ROOT / "payments"


# ============================================================
# BACKUPS
# ============================================================

for path in [
    ORDER_MODELS,
    PAYMENT_MODELS,
    CUSTOMER_RETURNS,
    ADMIN_RETURNS,
    PAYMENT_URLS,
    SETTINGS,
    CUSTOMER_ORDER,
]:

    if path.exists():

        backup = Path(
            str(path) + ".phase8bbackup"
        )

        if not backup.exists():
            shutil.copy2(
                path,
                backup,
            )


# ============================================================
# 1. RETURN POLICY SETTINGS
# ============================================================

settings = SETTINGS.read_text(
    encoding="utf-8-sig"
)

if "RETURN_WINDOW_DAYS" not in settings:

    settings += '''

# ============================================================
# RETURNS / REFUNDS
# ============================================================

RETURN_WINDOW_DAYS = 14
'''

    SETTINGS.write_text(
        settings,
        encoding="utf-8",
    )

print(
    "Added RETURN_WINDOW_DAYS = 14."
)


# ============================================================
# 2. ADD PARTIALLY REFUNDED PAYMENT STATUS
# ============================================================

orders = ORDER_MODELS.read_text(
    encoding="utf-8-sig"
)

if '("partially_refunded", "Partially Refunded")' not in orders:

    marker = '''        ("refunded", "Refunded"),
'''

    if marker not in orders:

        raise RuntimeError(
            "Could not locate refunded "
            "payment status in Order."
        )

    orders = orders.replace(
        marker,
        '''        ("partially_refunded", "Partially Refunded"),
'''
        + marker,
        1,
    )

    ORDER_MODELS.write_text(
        orders,
        encoding="utf-8",
    )

print(
    "Added partially_refunded payment status."
)


# ============================================================
# 3. RETURN / REFUND BUSINESS SERVICES
# ============================================================

services = PAYMENTS / "returns_services.py"

services.write_text(
r'''
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db.models import Sum
from django.utils import timezone

from .models import (
    RefundRequest,
    ReturnRequestItem,
)


ACTIVE_RETURN_STATUSES = [
    "requested",
    "approved",
    "completed",
]


def get_order_delivered_at(order):

    """
    Prefer the actual Delivery delivered timestamp.

    Older orders may not have a Delivery object, so
    fall back to the Order updated timestamp.
    """

    try:

        delivery = order.delivery

    except Exception:

        delivery = None


    if (
        delivery
        and delivery.delivered_at
    ):

        return delivery.delivered_at


    return order.updated_at


def get_return_deadline(order):

    delivered_at = get_order_delivered_at(
        order
    )

    if not delivered_at:
        return None


    days = getattr(
        settings,
        "RETURN_WINDOW_DAYS",
        14,
    )

    return (
        delivered_at
        + timedelta(days=days)
    )


def return_window_open(order):

    deadline = get_return_deadline(
        order
    )

    if deadline is None:
        return True

    return timezone.now() <= deadline


def already_returned_quantity(
    order_item,
):

    total = (
        ReturnRequestItem.objects
        .filter(
            order_item=order_item,
            return_request__status__in=(
                ACTIVE_RETURN_STATUSES
            ),
        )
        .aggregate(
            total=Sum("quantity")
        )["total"]
        or 0
    )

    return int(total)


def remaining_returnable_quantity(
    order_item,
):

    used = already_returned_quantity(
        order_item
    )

    return max(
        int(order_item.quantity)
        - used,
        0,
    )


def processed_refund_total(order):

    return (
        RefundRequest.objects
        .filter(
            order=order,
            status="processed",
        )
        .aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )


def pending_refund_total(order):

    return (
        RefundRequest.objects
        .filter(
            order=order,
            status__in=[
                "requested",
                "approved",
            ],
        )
        .aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )


def remaining_refundable_amount(
    order,
    include_pending=True,
):

    used = processed_refund_total(
        order
    )

    if include_pending:

        used += pending_refund_total(
            order
        )

    remaining = (
        order.total_amount
        - used
    )

    return max(
        remaining,
        Decimal("0.00"),
    )
'''.strip() + "\n",
encoding="utf-8",
)

print(
    "Created returns/refunds service layer."
)


# ============================================================
# 4. CUSTOMER RETURNS VIEW HARDENING
# ============================================================

customer = CUSTOMER_RETURNS.read_text(
    encoding="utf-8-sig"
)


# ------------------------------------------------------------
# Imports
# ------------------------------------------------------------

if "from .returns_services import (" not in customer:

    marker = '''from .models import (
'''

    imports = '''from .returns_services import (
    get_return_deadline,
    remaining_refundable_amount,
    remaining_returnable_quantity,
    return_window_open,
)

'''

    if marker not in customer:

        raise RuntimeError(
            "Could not locate model imports "
            "in customer_returns.py"
        )

    customer = customer.replace(
        marker,
        imports + marker,
        1,
    )


# ------------------------------------------------------------
# Replace old processed refund calculation
# ------------------------------------------------------------

pattern = re.compile(
    r'''
    processed_total\s*=\s*\(
        RefundRequest\.objects
        .*?
    refundable_amount\s*=\s*\(
        order\.total_amount
        \s*-\s*processed_total
    \)
    ''',
    re.S | re.X,
)

customer, count = pattern.subn(
    '''refundable_amount = (
        remaining_refundable_amount(
            order,
            include_pending=True,
        )
    )''',
    customer,
    count=1,
)

if count:
    print(
        "Refund amount calculation hardened."
    )


# ------------------------------------------------------------
# Remove old active refund hard block
# ------------------------------------------------------------

customer = re.sub(
    r'''
    \n\s*if\s+RefundRequest\.objects\.filter\(
        order=order,
        status__in=\[
            "requested",
            "approved",
        \],
    \)\.exists\(\):
        .*?
        \n\s*\)\n
    ''',
    "\n",
    customer,
    count=1,
    flags=re.S | re.X,
)


# ------------------------------------------------------------
# Return-window validation
# ------------------------------------------------------------

if "The return period for this order has expired." not in customer:

    marker = '''    items = list(
        order.items.select_related(
'''

    block = '''    if not return_window_open(
        order
    ):

        return JsonResponse(
            {
                "success": False,
                "error": (
                    "The return period for "
                    "this order has expired."
                ),
            },
            status=400,
        )


'''

    if marker not in customer:

        raise RuntimeError(
            "Could not locate return item query."
        )

    customer = customer.replace(
        marker,
        block + marker,
        1,
    )


# ------------------------------------------------------------
# Replace item quantity maximum
# ------------------------------------------------------------

old = '''                if quantity > item.quantity:

                    error = (
                        f"You purchased only "
                        f"{item.quantity} of "
                        f"{item.product_name}."
                    )

                    break
'''

new = '''                remaining_quantity = (
                    remaining_returnable_quantity(
                        item
                    )
                )

                if quantity > remaining_quantity:

                    error = (
                        f"Only {remaining_quantity} "
                        f"of {item.product_name} "
                        "remain eligible for return."
                    )

                    break
'''

if old not in customer:

    if "remain eligible for return" not in customer:
        raise RuntimeError(
            "Could not locate return quantity "
            "validation."
        )
else:

    customer = customer.replace(
        old,
        new,
        1,
    )


# ------------------------------------------------------------
# Add return quantities to template context
# ------------------------------------------------------------

# Rather than changing template data structure, attach temporary
# attributes to each OrderItem.

marker = '''    items = list(
        order.items.select_related(
            "product",
            "variant",
        )
    )
'''

replacement = '''    items = list(
        order.items.select_related(
            "product",
            "variant",
        )
    )

    for item in items:

        item.returnable_quantity = (
            remaining_returnable_quantity(
                item
            )
        )
'''

if marker in customer:

    customer = customer.replace(
        marker,
        replacement,
        1,
    )


# ------------------------------------------------------------
# Customer history pages
# ------------------------------------------------------------

if "def customer_returns_refunds(" not in customer:

    customer += r'''


@login_required
def customer_returns_refunds(
    request,
):

    returns = (
        ReturnRequest.objects
        .filter(
            order__user=request.user
        )
        .select_related(
            "order"
        )
        .prefetch_related(
            "items"
        )
        .order_by(
            "-created_at"
        )
    )

    refunds = (
        RefundRequest.objects
        .filter(
            order__user=request.user
        )
        .select_related(
            "order"
        )
        .order_by(
            "-created_at"
        )
    )


    return render(
        request,
        "payments/customer_returns_refunds.html",
        {
            "returns": returns,
            "refunds": refunds,
        },
    )


@login_required
def customer_return_detail(
    request,
    pk,
):

    obj = get_object_or_404(
        ReturnRequest.objects
        .filter(
            order__user=request.user
        )
        .select_related(
            "order"
        )
        .prefetch_related(
            "items__order_item",
            "events__created_by",
        ),
        pk=pk,
    )


    return render(
        request,
        "payments/customer_return_detail.html",
        {
            "return_request": obj,
            "order": obj.order,
            "return_deadline": (
                get_return_deadline(
                    obj.order
                )
            ),
        },
    )


@login_required
def customer_refund_detail(
    request,
    pk,
):

    obj = get_object_or_404(
        RefundRequest.objects
        .filter(
            order__user=request.user
        )
        .select_related(
            "order"
        )
        .prefetch_related(
            "events__created_by"
        ),
        pk=pk,
    )


    return render(
        request,
        "payments/customer_refund_detail.html",
        {
            "refund": obj,
            "order": obj.order,
        },
    )
'''


CUSTOMER_RETURNS.write_text(
    customer,
    encoding="utf-8",
)

print(
    "Customer returns/refunds hardened."
)


# ============================================================
# 5. UPDATE RETURN FORM MAXIMUM
# ============================================================

return_template = (
    PAYMENTS
    / "templates"
    / "payments"
    / "return_request_v2.html"
)

html = return_template.read_text(
    encoding="utf-8-sig"
)

html = html.replace(
    '''max="{{ item.quantity }}"
                                                    value="0"''',
    '''max="{{ item.returnable_quantity }}"
                                                    value="0"''',
)

html = html.replace(
    '''                                            <td>
                                                {{ item.quantity }}
                                            </td>''',
    '''                                            <td>
                                                {{ item.quantity }}

                                                {% if item.returnable_quantity != item.quantity %}

                                                    <small class="d-block text-muted">
                                                        {{ item.returnable_quantity }}
                                                        still returnable
                                                    </small>

                                                {% endif %}
                                            </td>''',
    1,
)


return_template.write_text(
    html,
    encoding="utf-8",
)


# ============================================================
# 6. NOTIFICATION TASK
# ============================================================

notification_task = (
    PAYMENTS
    / "returns_tasks.py"
)

notification_task.write_text(
r'''
from celery import shared_task

from notifications.tasks import (
    _send_order_notifications,
)

from .models import (
    RefundRequest,
    ReturnRequest,
)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={
        "max_retries": 3,
    },
)
def send_return_status_notification(
    self,
    return_id,
):

    obj = (
        ReturnRequest.objects
        .select_related(
            "order",
            "order__user",
        )
        .get(
            pk=return_id
        )
    )

    order = obj.order

    status = obj.get_status_display()

    sms = (
        f"Order {order.order_number}: "
        f"your {obj.get_request_type_display().lower()} "
        f"request is now {status.lower()}."
    )

    email = (
        f"Hello {order.full_name},\n\n"
        f"Your {obj.get_request_type_display().lower()} "
        f"request for order "
        f"{order.order_number} is now "
        f"{status}.\n"
    )

    if obj.staff_note:

        email += (
            f"\nShop note:\n"
            f"{obj.staff_note}\n"
        )

    _send_order_notifications(
        order,
        sms,
        (
            f"{obj.get_request_type_display()} "
            f"request update"
        ),
        email,
    )


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={
        "max_retries": 3,
    },
)
def send_refund_status_notification(
    self,
    refund_id,
):

    obj = (
        RefundRequest.objects
        .select_related(
            "order",
            "order__user",
        )
        .get(
            pk=refund_id
        )
    )

    order = obj.order

    status = obj.get_status_display()

    sms = (
        f"Order {order.order_number}: "
        f"your refund of "
        f"KES {obj.amount:.2f} is now "
        f"{status.lower()}."
    )

    email = (
        f"Hello {order.full_name},\n\n"
        f"Your refund request for order "
        f"{order.order_number} is now "
        f"{status}.\n\n"
        f"Amount: KES {obj.amount:.2f}\n"
    )

    if obj.external_reference:

        email += (
            f"Refund reference: "
            f"{obj.external_reference}\n"
        )

    if obj.staff_note:

        email += (
            f"\nShop note:\n"
            f"{obj.staff_note}\n"
        )

    _send_order_notifications(
        order,
        sms,
        "Refund request update",
        email,
    )
'''.strip() + "\n",
encoding="utf-8",
)

print(
    "Return/refund notification tasks created."
)


# ============================================================
# 7. ADMIN WORKFLOW HARDENING
# ============================================================

admin = ADMIN_RETURNS.read_text(
    encoding="utf-8-sig"
)


# ------------------------------------------------------------
# Import refund helper
# ------------------------------------------------------------

if "from .returns_services import (" not in admin:

    marker = '''from .models import (
'''

    helper_import = '''from .returns_services import (
    processed_refund_total,
    remaining_refundable_amount,
)

'''

    if marker not in admin:

        raise RuntimeError(
            "Could not locate payments models "
            "import in returns_admin_views.py"
        )

    admin = admin.replace(
        marker,
        helper_import + marker,
        1,
    )


# ------------------------------------------------------------
# Notification helper
# ------------------------------------------------------------

if "def _queue_return_notification(" not in admin:

    insertion = r'''

def _queue_return_notification(
    return_id,
):

    try:

        from .returns_tasks import (
            send_return_status_notification,
        )

        send_return_status_notification.delay(
            return_id
        )

    except Exception:
        pass


def _queue_refund_notification(
    refund_id,
):

    try:

        from .returns_tasks import (
            send_refund_status_notification,
        )

        send_refund_status_notification.delay(
            refund_id
        )

    except Exception:
        pass


'''

    marker = '''@staff_member_required
def returns_refunds_list(
'''

    if marker not in admin:

        raise RuntimeError(
            "Could not locate admin list view."
        )

    admin = admin.replace(
        marker,
        insertion + marker,
        1,
    )


# ------------------------------------------------------------
# Queue return review notification
# ------------------------------------------------------------

needle = '''    ReturnRefundEvent.objects.create(
        return_request=return_request,
        status=return_request.status,
'''

if needle in admin and "lambda pk=return_request.pk" not in admin:

    pos = admin.find(
        '''    messages.success(
        request,
        (
            "Return approved."'''
    )

    if pos != -1:

        notification = '''    transaction.on_commit(
        lambda pk=return_request.pk: (
            _queue_return_notification(
                pk
            )
        ),
        robust=True,
    )


'''

        admin = (
            admin[:pos]
            + notification
            + admin[pos:]
        )


# ------------------------------------------------------------
# Queue return completion notification
# ------------------------------------------------------------

target = '''    messages.success(
        request,
        "Return completed successfully.",
    )
'''

if target in admin:

    replacement = '''    transaction.on_commit(
        lambda pk=return_request.pk: (
            _queue_return_notification(
                pk
            )
        ),
        robust=True,
    )

    messages.success(
        request,
        "Return completed successfully.",
    )
'''

    admin = admin.replace(
        target,
        replacement,
        1,
    )


# ------------------------------------------------------------
# Refund review notification
# ------------------------------------------------------------

refund_success = '''    messages.success(
        request,
        (
            "Refund approved."
'''

idx = admin.find(
    refund_success
)

if (
    idx != -1
    and "lambda pk=refund.pk" not in admin[:idx][-600:]
):

    notification = '''    transaction.on_commit(
        lambda pk=refund.pk: (
            _queue_refund_notification(
                pk
            )
        ),
        robust=True,
    )


'''

    admin = (
        admin[:idx]
        + notification
        + admin[idx:]
    )


# ------------------------------------------------------------
# Harden refund process against over-refunding
# ------------------------------------------------------------

if "Remaining refundable balance is" not in admin:

    marker = '''    reference = request.POST.get(
        "external_reference",
        "",
    ).strip()
'''

    guard = '''    remaining = (
        remaining_refundable_amount(
            refund.order,
            include_pending=False,
        )
    )

    if refund.amount > remaining:

        messages.error(
            request,
            (
                "Refund amount exceeds the "
                "remaining refundable balance. "
                f"Remaining refundable balance is "
                f"KES {remaining:.2f}."
            ),
        )

        return redirect(
            "admin_refund_detail",
            pk=pk,
        )


'''

    if marker not in admin:

        raise RuntimeError(
            "Could not locate refund reference "
            "section."
        )

    admin = admin.replace(
        marker,
        guard + marker,
        1,
    )


# ------------------------------------------------------------
# Replace refund status update logic
# ------------------------------------------------------------

pattern = re.compile(
    r'''
    processed_total\s*=\s*\(
        RefundRequest\.objects
        .*?
    if\s*\(
        processed_total
        \s*>=\s*
        refund\.order\.total_amount
    \):
        .*?
        refund\.order\.save\(
            update_fields=\[
                "payment_status",
                "updated_at",
            \]
        \)
    ''',
    re.S | re.X,
)

replacement = '''    processed_total = (
        processed_refund_total(
            refund.order
        )
    )

    if (
        processed_total
        >= refund.order.total_amount
    ):

        refund.order.payment_status = (
            "refunded"
        )

    elif processed_total > 0:

        refund.order.payment_status = (
            "partially_refunded"
        )

    refund.order.save(
        update_fields=[
            "payment_status",
            "updated_at",
        ]
    )
'''

admin, count = pattern.subn(
    replacement,
    admin,
    count=1,
)

if count:

    print(
        "Partial-refund status added."
    )


# ------------------------------------------------------------
# Refund process notification
# ------------------------------------------------------------

target = '''    messages.success(
        request,
        "Refund marked as processed.",
    )
'''

if target in admin:

    replacement = '''    transaction.on_commit(
        lambda pk=refund.pk: (
            _queue_refund_notification(
                pk
            )
        ),
        robust=True,
    )

    messages.success(
        request,
        "Refund marked as processed.",
    )
'''

    admin = admin.replace(
        target,
        replacement,
        1,
    )


ADMIN_RETURNS.write_text(
    admin,
    encoding="utf-8",
)

print(
    "Admin returns/refunds hardened."
)


# ============================================================
# 8. CUSTOMER HISTORY URLS
# ============================================================

urls = PAYMENT_URLS.read_text(
    encoding="utf-8-sig"
)

routes = []

if 'name="customer_returns_refunds"' not in urls:

    routes.append(
r'''
    path(
        "my-returns/",
        customer_returns.customer_returns_refunds,
        name="customer_returns_refunds",
    ),
'''
    )


if 'name="customer_return_detail"' not in urls:

    routes.append(
r'''
    path(
        "my-returns/returns/<int:pk>/",
        customer_returns.customer_return_detail,
        name="customer_return_detail",
    ),
'''
    )


if 'name="customer_refund_detail"' not in urls:

    routes.append(
r'''
    path(
        "my-returns/refunds/<int:pk>/",
        customer_returns.customer_refund_detail,
        name="customer_refund_detail",
    ),
'''
    )


if routes:

    marker = "urlpatterns = ["

    urls = urls.replace(
        marker,
        marker + "".join(routes),
        1,
    )


PAYMENT_URLS.write_text(
    urls,
    encoding="utf-8",
)

print(
    "Customer return/refund routes added."
)


# ============================================================
# 9. CUSTOMER RETURNS & REFUNDS PAGE
# ============================================================

template_dir = (
    PAYMENTS
    / "templates"
    / "payments"
)

template_dir.mkdir(
    parents=True,
    exist_ok=True,
)


(template_dir / "customer_returns_refunds.html").write_text(
r'''
{% extends "base.html" %}

{% block content %}

<div class="container py-5">

    <div class="d-flex justify-content-between align-items-center mb-4">

        <div>

            <h2 class="mb-1">
                Returns & Refunds
            </h2>

            <p class="text-muted mb-0">
                Track your return, replacement and refund requests.
            </p>

        </div>

        <a
            href="{% url 'order_history' %}"
            class="btn btn-outline-secondary"
        >
            My Orders
        </a>

    </div>


    <div class="card shadow-sm mb-4">

        <div class="card-header">
            <strong>
                Returns & Replacements
            </strong>
        </div>

        <div class="table-responsive">

            <table class="table mb-0 align-middle">

                <thead>

                    <tr>

                        <th>Order</th>
                        <th>Type</th>
                        <th>Status</th>
                        <th>Date</th>
                        <th></th>

                    </tr>

                </thead>

                <tbody>

                    {% for item in returns %}

                        <tr>

                            <td>
                                {{ item.order.order_number }}
                            </td>

                            <td>
                                {{ item.get_request_type_display }}
                            </td>

                            <td>
                                {{ item.get_status_display }}
                            </td>

                            <td>
                                {{ item.created_at|date:"d M Y H:i" }}
                            </td>

                            <td class="text-end">

                                <a
                                    href="{% url 'customer_return_detail' item.pk %}"
                                    class="btn btn-sm btn-outline-primary"
                                >
                                    View
                                </a>

                            </td>

                        </tr>

                    {% empty %}

                        <tr>

                            <td
                                colspan="5"
                                class="text-center text-muted py-4"
                            >
                                No return requests yet.
                            </td>

                        </tr>

                    {% endfor %}

                </tbody>

            </table>

        </div>

    </div>


    <div class="card shadow-sm">

        <div class="card-header">
            <strong>
                Refunds
            </strong>
        </div>

        <div class="table-responsive">

            <table class="table mb-0 align-middle">

                <thead>

                    <tr>

                        <th>Order</th>
                        <th>Amount</th>
                        <th>Status</th>
                        <th>Date</th>
                        <th></th>

                    </tr>

                </thead>

                <tbody>

                    {% for item in refunds %}

                        <tr>

                            <td>
                                {{ item.order.order_number }}
                            </td>

                            <td>
                                KES {{ item.amount|floatformat:2 }}
                            </td>

                            <td>
                                {{ item.get_status_display }}
                            </td>

                            <td>
                                {{ item.created_at|date:"d M Y H:i" }}
                            </td>

                            <td class="text-end">

                                <a
                                    href="{% url 'customer_refund_detail' item.pk %}"
                                    class="btn btn-sm btn-outline-primary"
                                >
                                    View
                                </a>

                            </td>

                        </tr>

                    {% empty %}

                        <tr>

                            <td
                                colspan="5"
                                class="text-center text-muted py-4"
                            >
                                No refund requests yet.
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


# ============================================================
# 10. CUSTOMER RETURN DETAIL
# ============================================================

(template_dir / "customer_return_detail.html").write_text(
r'''
{% extends "base.html" %}

{% block content %}

<div class="container py-5">

    <a
        href="{% url 'customer_returns_refunds' %}"
        class="btn btn-outline-secondary btn-sm mb-4"
    >
        &larr; Returns & Refunds
    </a>


    <div class="row g-4">

        <div class="col-lg-8">

            <div class="card shadow-sm mb-4">

                <div class="card-body">

                    <h3>
                        {{ return_request.get_request_type_display }}
                    </h3>

                    <p class="text-muted">
                        Order {{ order.order_number }}
                    </p>


                    <div class="mb-3">

                        <strong>Status:</strong>

                        {{ return_request.get_status_display }}

                    </div>


                    <h5>
                        Items
                    </h5>

                    <div class="table-responsive">

                        <table class="table">

                            <thead>

                                <tr>
                                    <th>Product</th>
                                    <th>Quantity</th>
                                </tr>

                            </thead>

                            <tbody>

                                {% for line in return_request.items.all %}

                                    <tr>

                                        <td>
                                            {{ line.order_item.product_name }}
                                        </td>

                                        <td>
                                            {{ line.quantity }}
                                        </td>

                                    </tr>

                                {% empty %}

                                    <tr>

                                        <td colspan="2">
                                            Whole-order legacy request
                                        </td>

                                    </tr>

                                {% endfor %}

                            </tbody>

                        </table>

                    </div>


                    <h5>
                        Reason
                    </h5>

                    <p>
                        {{ return_request.reason }}
                    </p>

                </div>

            </div>


            <div class="card shadow-sm">

                <div class="card-body">

                    <h5>
                        Request Timeline
                    </h5>

                    {% for event in return_request.events.all %}

                        <div class="border-start ps-3 py-2">

                            <strong>
                                {{ event.status|title }}
                            </strong>

                            <div class="small text-muted">
                                {{ event.created_at|date:"d M Y H:i" }}
                            </div>

                            {% if event.message %}

                                <div>
                                    {{ event.message }}
                                </div>

                            {% endif %}

                        </div>

                    {% empty %}

                        <p class="text-muted">
                            No timeline activity.
                        </p>

                    {% endfor %}

                </div>

            </div>

        </div>


        <div class="col-lg-4">

            {% if return_deadline %}

                <div class="card shadow-sm mb-4">

                    <div class="card-body">

                        <small class="text-muted">
                            Return Window
                        </small>

                        <div class="fw-semibold">
                            {{ return_deadline|date:"d M Y H:i" }}
                        </div>

                    </div>

                </div>

            {% endif %}


            {% if return_request.staff_note %}

                <div class="card shadow-sm">

                    <div class="card-body">

                        <h5>
                            Shop Note
                        </h5>

                        <p class="mb-0">
                            {{ return_request.staff_note }}
                        </p>

                    </div>

                </div>

            {% endif %}

        </div>

    </div>

</div>

{% endblock %}
'''.strip() + "\n",
encoding="utf-8",
)


# ============================================================
# 11. CUSTOMER REFUND DETAIL
# ============================================================

(template_dir / "customer_refund_detail.html").write_text(
r'''
{% extends "base.html" %}

{% block content %}

<div class="container py-5">

    <a
        href="{% url 'customer_returns_refunds' %}"
        class="btn btn-outline-secondary btn-sm mb-4"
    >
        &larr; Returns & Refunds
    </a>


    <div class="row g-4">

        <div class="col-lg-8">

            <div class="card shadow-sm mb-4">

                <div class="card-body">

                    <h3>
                        Refund Request
                    </h3>

                    <p class="text-muted">
                        Order {{ order.order_number }}
                    </p>


                    <div class="row g-3">

                        <div class="col-md-6">

                            <small class="text-muted">
                                Amount
                            </small>

                            <div class="fs-4 fw-bold">
                                KES {{ refund.amount|floatformat:2 }}
                            </div>

                        </div>


                        <div class="col-md-6">

                            <small class="text-muted">
                                Status
                            </small>

                            <div class="fw-semibold">
                                {{ refund.get_status_display }}
                            </div>

                        </div>

                    </div>


                    {% if refund.external_reference %}

                        <hr>

                        <strong>
                            Refund Reference
                        </strong>

                        <div>
                            <code>
                                {{ refund.external_reference }}
                            </code>
                        </div>

                    {% endif %}

                </div>

            </div>


            <div class="card shadow-sm">

                <div class="card-body">

                    <h5>
                        Refund Timeline
                    </h5>

                    {% for event in refund.events.all %}

                        <div class="border-start ps-3 py-2">

                            <strong>
                                {{ event.status|title }}
                            </strong>

                            <div class="small text-muted">
                                {{ event.created_at|date:"d M Y H:i" }}
                            </div>

                            {% if event.message %}

                                <div>
                                    {{ event.message }}
                                </div>

                            {% endif %}

                        </div>

                    {% empty %}

                        <p class="text-muted">
                            No timeline activity.
                        </p>

                    {% endfor %}

                </div>

            </div>

        </div>


        <div class="col-lg-4">

            {% if refund.staff_note %}

                <div class="card shadow-sm">

                    <div class="card-body">

                        <h5>
                            Shop Note
                        </h5>

                        <p class="mb-0">
                            {{ refund.staff_note }}
                        </p>

                    </div>

                </div>

            {% endif %}

        </div>

    </div>

</div>

{% endblock %}
'''.strip() + "\n",
encoding="utf-8",
)


# ============================================================
# 12. ADD CUSTOMER RETURNS LINK TO ORDER DETAIL
# ============================================================

if CUSTOMER_ORDER.exists():

    order_html = CUSTOMER_ORDER.read_text(
        encoding="utf-8-sig"
    )

    if "customer_returns_refunds" not in order_html:

        marker = '''{% block content %}'''

        addition = '''{% block content %}

<div class="container pt-3">

    <div class="text-end">

        <a
            href="{% url 'customer_returns_refunds' %}"
            class="btn btn-sm btn-outline-secondary"
        >
            My Returns & Refunds
        </a>

    </div>

</div>
'''

        if marker in order_html:

            order_html = order_html.replace(
                marker,
                addition,
                1,
            )

            CUSTOMER_ORDER.write_text(
                order_html,
                encoding="utf-8",
            )


# ============================================================
# 13. TESTS
# ============================================================

tests = PAYMENTS / "test_phase8b.py"

tests.write_text(
r'''
from decimal import Decimal
from datetime import timedelta

from django.contrib.auth import (
    get_user_model,
)

from django.test import TestCase

from django.urls import reverse

from django.utils import timezone

from categories.models import Category

from products.models import Product

from orders.models import (
    Order,
    OrderItem,
)

from payments.models import (
    RefundRequest,
    ReturnRequest,
    ReturnRequestItem,
)

from payments.returns_services import (
    remaining_refundable_amount,
    remaining_returnable_quantity,
)


User = get_user_model()


class Phase8BTests(TestCase):

    def setUp(self):

        self.customer = (
            User.objects.create_user(
                username="phase8bcustomer",
                password="pass12345",
                role=User.CUSTOMER,
            )
        )

        self.staff = (
            User.objects.create_user(
                username="phase8bstaff",
                password="pass12345",
                role=User.ADMIN,
                is_staff=True,
            )
        )

        self.category = (
            Category.objects.create(
                name="Phase8B Category",
                slug="phase8b-category",
            )
        )

        self.product = (
            Product.objects.create(
                category=self.category,
                name="Phase8B Product",
                slug="phase8b-product",
                sku="P8B-001",
                price=Decimal("1000.00"),
                stock=10,
                reserved_stock=0,
                is_active=True,
            )
        )

        self.order = Order.objects.create(
            user=self.customer,
            order_number="PHASE8B-001",
            full_name="Phase 8B Customer",
            phone="0712345678",
            email="phase8b@example.com",
            county="Nairobi",
            city="Nairobi",
            estate="CBD",
            house_number="1",
            subtotal=Decimal("3000.00"),
            shipping_cost=Decimal("0.00"),
            discount=Decimal("0.00"),
            total_amount=Decimal("3000.00"),
            status="delivered",
            payment_status="paid",
            inventory_status="consumed",
        )

        self.item = (
            OrderItem.objects.create(
                order=self.order,
                product=self.product,
                product_name=self.product.name,
                price=Decimal("1000.00"),
                quantity=3,
                subtotal=Decimal("3000.00"),
            )
        )


    def test_duplicate_return_quantity_is_blocked(
        self
    ):

        first = ReturnRequest.objects.create(
            order=self.order,
            request_type="return",
            reason="First return",
            status="completed",
        )

        ReturnRequestItem.objects.create(
            return_request=first,
            order_item=self.item,
            quantity=2,
        )

        self.assertEqual(
            remaining_returnable_quantity(
                self.item
            ),
            1,
        )


    def test_pending_refund_reserves_balance(
        self
    ):

        RefundRequest.objects.create(
            order=self.order,
            amount=Decimal("1000.00"),
            reason="Pending refund",
            status="approved",
        )

        self.assertEqual(
            remaining_refundable_amount(
                self.order,
                include_pending=True,
            ),
            Decimal("2000.00"),
        )


    def test_partial_refund_sets_partial_status(
        self
    ):

        refund = RefundRequest.objects.create(
            order=self.order,
            amount=Decimal("1000.00"),
            reason="Partial refund",
            status="approved",
        )

        self.client.login(
            username="phase8bstaff",
            password="pass12345",
        )

        response = self.client.post(
            reverse(
                "admin_refund_process",
                kwargs={
                    "pk": refund.pk
                },
            ),
            {
                "external_reference": (
                    "TEST-REF-001"
                ),
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.order.refresh_from_db()

        self.assertEqual(
            self.order.payment_status,
            "partially_refunded",
        )


    def test_customer_cannot_view_other_return(
        self
    ):

        other = User.objects.create_user(
            username="other8b",
            password="pass12345",
            role=User.CUSTOMER,
        )

        obj = ReturnRequest.objects.create(
            order=self.order,
            request_type="return",
            reason="Test",
        )

        self.client.login(
            username="other8b",
            password="pass12345",
        )

        response = self.client.get(
            reverse(
                "customer_return_detail",
                kwargs={
                    "pk": obj.pk
                },
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )
'''.strip() + "\n",
encoding="utf-8",
)


print()
print("=" * 72)
print("PHASE 8B RETURNS / REFUNDS HARDENING COMPLETE")
print("=" * 72)
print()
print("Next commands:")
print("python manage.py makemigrations orders")
print("python manage.py migrate")
print("python manage.py check")
