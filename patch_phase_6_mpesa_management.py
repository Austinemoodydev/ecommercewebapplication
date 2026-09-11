from pathlib import Path
import re
import shutil


ROOT = Path.cwd()

order_models = (
    ROOT / "orders" / "models.py"
)

config_urls = (
    ROOT / "config" / "urls.py"
)

base_template = (
    ROOT
    / "templates"
    / "dashboard"
    / "admin"
    / "base.html"
)

forms_path = (
    ROOT
    / "payments"
    / "admin_forms.py"
)

views_path = (
    ROOT
    / "payments"
    / "admin_views.py"
)

urls_path = (
    ROOT
    / "payments"
    / "admin_urls.py"
)

tests_path = (
    ROOT
    / "payments"
    / "test_admin_payments.py"
)

template_dir = (
    ROOT
    / "templates"
    / "dashboard"
    / "admin"
    / "payments"
)

list_template = (
    template_dir / "list.html"
)

detail_template = (
    template_dir / "detail.html"
)


def backup(path):

    if path.exists():

        target = Path(
            str(path) + ".phase6backup"
        )

        shutil.copy2(
            path,
            target,
        )

        print(
            f"Backup: {target}"
        )


for path in [
    order_models,
    config_urls,
    base_template,
]:

    backup(path)


# ============================================================
# 1. ORDER PAYMENT REVIEW AUDIT FIELDS
# ============================================================

text = order_models.read_text(
    encoding="utf-8-sig"
)

if (
    "payment_review_resolution ="
    not in text
):

    marker = r'''    payment_review_reason = models.TextField(
        blank=True,
    )
'''

    addition = r'''
    payment_review_resolution = models.TextField(
        blank=True,
    )

    payment_review_resolved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    payment_review_resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_payment_reviews",
    )
'''

    if marker not in text:

        raise RuntimeError(
            "Could not locate payment_review_reason."
        )

    text = text.replace(
        marker,
        marker + addition,
        1,
    )

    order_models.write_text(
        text,
        encoding="utf-8",
    )

    print(
        "Added payment review resolution audit fields."
    )

else:

    print(
        "Payment review audit fields already exist."
    )


# ============================================================
# 2. ADMIN PAYMENT FORM
# ============================================================

forms_path.write_text(
r'''
from django import forms


class PaymentReviewResolutionForm(
    forms.Form
):

    resolution = forms.CharField(
        label="Resolution",
        min_length=3,
        max_length=2000,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": (
                    "Explain what was verified "
                    "and how this payment case "
                    "was resolved."
                ),
            }
        ),
    )

    def clean_resolution(self):

        return (
            self.cleaned_data[
                "resolution"
            ].strip()
        )
'''.strip() + "\n",
    encoding="utf-8",
)

print(
    "Created payments/admin_forms.py"
)


# ============================================================
# 3. ADMIN PAYMENT VIEWS
# ============================================================

views_path.write_text(
r'''
import csv

from decimal import Decimal

from django.contrib import messages

from django.contrib.admin.views.decorators import (
    staff_member_required,
)

from django.core.paginator import (
    Paginator,
)

from django.db.models import (
    Count,
    Q,
    Sum,
)

from django.http import (
    HttpResponse,
)

from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from django.utils import timezone

from orders.models import Order

from .admin_forms import (
    PaymentReviewResolutionForm,
)

from .models import (
    MpesaTransaction,
)


# ============================================================
# QUERYSET
# ============================================================

def payment_queryset():

    return (
        MpesaTransaction.objects
        .select_related(
            "order",
            "order__user",
            "order__payment_review_resolved_by",
        )
        .order_by(
            "-created_at"
        )
    )


# ============================================================
# PAYMENT LIST
# ============================================================

@staff_member_required
def admin_payment_list(
    request,
):

    transactions = (
        payment_queryset()
    )

    query = request.GET.get(
        "q",
        "",
    ).strip()

    status = request.GET.get(
        "status",
        "",
    )

    review = request.GET.get(
        "review",
        "",
    )

    if query:

        transactions = (
            transactions.filter(
                Q(
                    order__order_number__icontains=query
                )
                | Q(
                    phone_number__icontains=query
                )
                | Q(
                    mpesa_receipt_number__icontains=query
                )
                | Q(
                    checkout_request_id__icontains=query
                )
                | Q(
                    merchant_request_id__icontains=query
                )
                | Q(
                    order__user__username__icontains=query
                )
                | Q(
                    order__user__email__icontains=query
                )
            )
        )

    valid_statuses = dict(
        MpesaTransaction.STATUS_CHOICES
    )

    if status in valid_statuses:

        transactions = (
            transactions.filter(
                status=status
            )
        )

    if review == "required":

        transactions = (
            transactions.filter(
                order__payment_review_required=True
            )
        )

    elif review == "clear":

        transactions = (
            transactions.filter(
                order__payment_review_required=False
            )
        )

    all_transactions = (
        MpesaTransaction.objects.all()
    )

    successful_count = (
        all_transactions.filter(
            status="success"
        ).count()
    )

    pending_count = (
        all_transactions.filter(
            status="pending"
        ).count()
    )

    failed_count = (
        all_transactions.filter(
            status="failed"
        ).count()
    )

    review_count = (
        Order.objects.filter(
            payment_review_required=True
        ).count()
    )

    successful_amount = (
        all_transactions
        .filter(
            status="success"
        )
        .aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )

    paginator = Paginator(
        transactions,
        30,
    )

    page_obj = (
        paginator.get_page(
            request.GET.get("page")
        )
    )

    return render(
        request,
        (
            "dashboard/admin/payments/"
            "list.html"
        ),
        {
            "transactions": (
                page_obj.object_list
            ),
            "page_obj": page_obj,

            "query": query,

            "selected_status": status,

            "selected_review": review,

            "status_choices": (
                MpesaTransaction
                .STATUS_CHOICES
            ),

            "successful_count": (
                successful_count
            ),

            "pending_count": (
                pending_count
            ),

            "failed_count": (
                failed_count
            ),

            "review_count": (
                review_count
            ),

            "successful_amount": (
                successful_amount
            ),
        },
    )


# ============================================================
# TRANSACTION DETAIL
# ============================================================

@staff_member_required
def admin_payment_detail(
    request,
    pk,
):

    payment = get_object_or_404(
        payment_queryset(),
        pk=pk,
    )

    order = payment.order

    all_order_transactions = (
        order.mpesa_transactions
        .order_by(
            "-created_at"
        )
    )

    success_transactions = (
        all_order_transactions.filter(
            status="success"
        )
    )

    successful_payment_count = (
        success_transactions.count()
    )

    successful_payment_total = (
        success_transactions.aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )

    form = (
        PaymentReviewResolutionForm()
    )

    return render(
        request,
        (
            "dashboard/admin/payments/"
            "detail.html"
        ),
        {
            "payment": payment,
            "order": order,

            "all_order_transactions": (
                all_order_transactions
            ),

            "successful_payment_count": (
                successful_payment_count
            ),

            "successful_payment_total": (
                successful_payment_total
            ),

            "review_form": form,
        },
    )


# ============================================================
# RESOLVE PAYMENT REVIEW
# ============================================================

@staff_member_required
def admin_payment_review_resolve(
    request,
    pk,
):

    payment = get_object_or_404(
        payment_queryset(),
        pk=pk,
    )

    order = payment.order

    if request.method != "POST":

        return redirect(
            "admin_payment_detail",
            pk=payment.pk,
        )

    if (
        not order.payment_review_required
    ):

        messages.info(
            request,
            (
                "This order does not "
                "currently require payment review."
            ),
        )

        return redirect(
            "admin_payment_detail",
            pk=payment.pk,
        )

    form = (
        PaymentReviewResolutionForm(
            request.POST
        )
    )

    if not form.is_valid():

        messages.error(
            request,
            (
                "Enter a proper resolution "
                "before closing the review."
            ),
        )

        return redirect(
            "admin_payment_detail",
            pk=payment.pk,
        )

    order.payment_review_required = False

    order.payment_review_resolution = (
        form.cleaned_data[
            "resolution"
        ]
    )

    order.payment_review_resolved_at = (
        timezone.now()
    )

    order.payment_review_resolved_by = (
        request.user
    )

    order.save(
        update_fields=[
            "payment_review_required",
            "payment_review_resolution",
            "payment_review_resolved_at",
            "payment_review_resolved_by",
            "updated_at",
        ]
    )

    messages.success(
        request,
        (
            "Payment review resolved "
            "and recorded in the audit trail."
        ),
    )

    return redirect(
        "admin_payment_detail",
        pk=payment.pk,
    )


# ============================================================
# REOPEN REVIEW
# ============================================================

@staff_member_required
def admin_payment_review_reopen(
    request,
    pk,
):

    payment = get_object_or_404(
        payment_queryset(),
        pk=pk,
    )

    order = payment.order

    if request.method != "POST":

        return redirect(
            "admin_payment_detail",
            pk=payment.pk,
        )

    if order.payment_review_required:

        messages.info(
            request,
            (
                "Payment review is "
                "already open."
            ),
        )

        return redirect(
            "admin_payment_detail",
            pk=payment.pk,
        )

    order.payment_review_required = True

    if not order.payment_review_reason:

        order.payment_review_reason = (
            "Payment review reopened "
            "manually by staff."
        )

    order.save(
        update_fields=[
            "payment_review_required",
            "payment_review_reason",
            "updated_at",
        ]
    )

    messages.warning(
        request,
        "Payment review reopened.",
    )

    return redirect(
        "admin_payment_detail",
        pk=payment.pk,
    )


# ============================================================
# CSV EXPORT
# ============================================================

@staff_member_required
def admin_payment_export_csv(
    request,
):

    response = HttpResponse(
        content_type=(
            "text/csv; charset=utf-8"
        )
    )

    response[
        "Content-Disposition"
    ] = (
        'attachment; '
        'filename="mpesa_transactions.csv"'
    )

    response.write(
        "\ufeff"
    )

    writer = csv.writer(
        response
    )

    writer.writerow([
        "Date",
        "Order",
        "Customer",
        "Phone",
        "Amount",
        "Transaction Status",
        "Order Payment Status",
        "Receipt Number",
        "Merchant Request ID",
        "Checkout Request ID",
        "Result Code",
        "Result Description",
        "Review Required",
        "Review Reason",
        "Review Resolution",
        "Review Resolved At",
        "Review Resolved By",
    ])

    for payment in (
        payment_queryset()
    ):

        order = payment.order

        writer.writerow([
            payment.created_at,

            order.order_number,

            order.user.username,

            payment.phone_number,

            payment.amount,

            payment.status,

            order.payment_status,

            payment.mpesa_receipt_number,

            payment.merchant_request_id,

            payment.checkout_request_id,

            payment.result_code,

            payment.result_description,

            (
                "Yes"
                if order.payment_review_required
                else "No"
            ),

            order.payment_review_reason,

            order.payment_review_resolution,

            order.payment_review_resolved_at or "",

            (
                str(
                    order.payment_review_resolved_by
                )
                if order.payment_review_resolved_by
                else ""
            ),
        ])

    return response
'''.strip() + "\n",
    encoding="utf-8",
)

print(
    "Created payments/admin_views.py"
)


# ============================================================
# 4. PAYMENT ADMIN URLS
# ============================================================

urls_path.write_text(
r'''
from django.urls import path

from . import admin_views


urlpatterns = [

    path(
        "",
        admin_views.admin_payment_list,
        name="admin_payment_list",
    ),

    path(
        "export/",
        admin_views.admin_payment_export_csv,
        name="admin_payment_export_csv",
    ),

    path(
        "<int:pk>/",
        admin_views.admin_payment_detail,
        name="admin_payment_detail",
    ),

    path(
        "<int:pk>/review/resolve/",
        admin_views.admin_payment_review_resolve,
        name="admin_payment_review_resolve",
    ),

    path(
        "<int:pk>/review/reopen/",
        admin_views.admin_payment_review_reopen,
        name="admin_payment_review_reopen",
    ),

]
'''.strip() + "\n",
    encoding="utf-8",
)

print(
    "Created payments/admin_urls.py"
)


# ============================================================
# 5. CONFIG URLS
# ============================================================

text = config_urls.read_text(
    encoding="utf-8-sig"
)

# Fix duplicate include import currently present
text = re.sub(
    r'from django\.urls import [^\n]+',
    'from django.urls import include, path',
    text,
    count=1,
)

if (
    'include("payments.admin_urls")'
    not in text
):

    marker = "urlpatterns = ["

    if marker not in text:

        raise RuntimeError(
            "Could not find urlpatterns."
        )

    route = r'''
    path(
        "dashboard/admin/payments/",
        include("payments.admin_urls"),
    ),
'''

    text = text.replace(
        marker,
        marker + route,
        1,
    )

config_urls.write_text(
    text,
    encoding="utf-8",
)

print(
    "Connected payment management URLs."
)

print(
    "Normalized django.urls import."
)


# ============================================================
# 6. PAYMENT LIST TEMPLATE
# ============================================================

template_dir.mkdir(
    parents=True,
    exist_ok=True,
)

list_template.write_text(
r'''
{% extends "dashboard/admin/base.html" %}

{% block title %}
Payments | Store Management
{% endblock %}

{% block page_heading %}
Payments
{% endblock %}

{% block admin_content %}


<div class="dashboard-heading">

    <div
        class="
            d-flex
            justify-content-between
            align-items-start
            flex-wrap
            gap-3
        "
    >

        <div>

            <h1>
                M-Pesa Payments
            </h1>

            <p>
                Monitor STK transactions,
                receipts and payment-review cases.
            </p>

        </div>


        <a
            href="{% url 'admin_payment_export_csv' %}"
            class="btn btn-outline-success"
        >
            <i class="bi bi-file-earmark-spreadsheet"></i>
            Export CSV
        </a>

    </div>

</div>


<!-- STATS -->

<div class="row g-3 mb-4">

    <div class="col-md-6 col-xl">

        <div class="dashboard-card mini-stat">

            <span>
                Successful
            </span>

            <strong>
                {{ successful_count }}
            </strong>

        </div>

    </div>


    <div class="col-md-6 col-xl">

        <div class="dashboard-card mini-stat">

            <span>
                Successful Value
            </span>

            <strong>
                KES {{ successful_amount|floatformat:2 }}
            </strong>

        </div>

    </div>


    <div class="col-md-6 col-xl">

        <div class="dashboard-card mini-stat">

            <span>
                Pending
            </span>

            <strong>
                {{ pending_count }}
            </strong>

        </div>

    </div>


    <div class="col-md-6 col-xl">

        <div class="dashboard-card mini-stat">

            <span>
                Failed
            </span>

            <strong>
                {{ failed_count }}
            </strong>

        </div>

    </div>


    <div class="col-md-6 col-xl">

        <div class="dashboard-card mini-stat">

            <span>
                Needs Review
            </span>

            <strong>
                {{ review_count }}
            </strong>

        </div>

    </div>

</div>


{% if review_count %}

<div class="alert alert-warning">

    <i class="bi bi-exclamation-triangle-fill me-1"></i>

    <strong>
        {{ review_count }}
    </strong>

    order{{ review_count|pluralize }}
    currently require payment review.

    These can include duplicate or late
    successful M-Pesa payments.

</div>

{% endif %}


<!-- FILTERS -->

<div class="dashboard-card mb-4">

    <div class="card-header-custom">

        <div>

            <h2>
                Find Transactions
            </h2>

            <p>
                Search using an order,
                customer, phone or M-Pesa reference.
            </p>

        </div>

    </div>


    <form method="GET">

        <div class="row g-3">

            <div class="col-lg-6">

                <label class="form-label">
                    Search
                </label>

                <div class="input-group">

                    <span class="input-group-text">
                        <i class="bi bi-search"></i>
                    </span>

                    <input
                        type="text"
                        name="q"
                        value="{{ query }}"
                        class="form-control"
                        placeholder="Order, phone, receipt, CheckoutRequestID..."
                    >

                </div>

            </div>


            <div class="col-lg-3">

                <label class="form-label">
                    Transaction Status
                </label>

                <select
                    name="status"
                    class="form-select"
                >

                    <option value="">
                        All Statuses
                    </option>

                    {% for value, label in status_choices %}

                        <option
                            value="{{ value }}"
                            {% if selected_status == value %}
                                selected
                            {% endif %}
                        >
                            {{ label }}
                        </option>

                    {% endfor %}

                </select>

            </div>


            <div class="col-lg-3">

                <label class="form-label">
                    Review
                </label>

                <select
                    name="review"
                    class="form-select"
                >

                    <option value="">
                        All
                    </option>

                    <option
                        value="required"
                        {% if selected_review == "required" %}
                            selected
                        {% endif %}
                    >
                        Needs Review
                    </option>

                    <option
                        value="clear"
                        {% if selected_review == "clear" %}
                            selected
                        {% endif %}
                    >
                        No Open Review
                    </option>

                </select>

            </div>

        </div>


        <div class="mt-3">

            <button
                type="submit"
                class="btn btn-primary"
            >
                <i class="bi bi-funnel"></i>
                Apply Filters
            </button>


            <a
                href="{% url 'admin_payment_list' %}"
                class="btn btn-outline-secondary"
            >
                Reset
            </a>

        </div>

    </form>

</div>


<!-- TABLE -->

<div class="dashboard-card">

    <div class="card-header-custom">

        <div>

            <h2>
                M-Pesa Transactions
            </h2>

            <p>
                Safaricom STK transaction records.
            </p>

        </div>

    </div>


    <div class="table-responsive">

        <table
            class="
                table
                dashboard-table
                align-middle
            "
        >

            <thead>

                <tr>

                    <th>
                        Order
                    </th>

                    <th>
                        Customer
                    </th>

                    <th>
                        Phone
                    </th>

                    <th>
                        Amount
                    </th>

                    <th>
                        Receipt
                    </th>

                    <th>
                        Transaction
                    </th>

                    <th>
                        Order Payment
                    </th>

                    <th>
                        Review
                    </th>

                    <th>
                        Date
                    </th>

                    <th class="text-end">
                        Action
                    </th>

                </tr>

            </thead>


            <tbody>

                {% for payment in transactions %}

                    <tr>

                        <td>

                            <strong>
                                {{ payment.order.order_number }}
                            </strong>

                        </td>


                        <td>

                            {% if payment.order.user.get_full_name %}

                                {{ payment.order.user.get_full_name }}

                            {% else %}

                                {{ payment.order.user.username }}

                            {% endif %}


                            <small class="d-block text-muted">
                                {{ payment.order.user.email|default:"" }}
                            </small>

                        </td>


                        <td>
                            {{ payment.phone_number }}
                        </td>


                        <td>

                            <strong>
                                KES
                                {{ payment.amount|floatformat:2 }}
                            </strong>

                        </td>


                        <td>

                            {% if payment.mpesa_receipt_number %}

                                <code>
                                    {{ payment.mpesa_receipt_number }}
                                </code>

                            {% else %}

                                <span class="text-muted">
                                    —
                                </span>

                            {% endif %}

                        </td>


                        <td>

                            {% if payment.status == "success" %}

                                <span class="badge text-bg-success">
                                    Success
                                </span>

                            {% elif payment.status == "failed" %}

                                <span class="badge text-bg-danger">
                                    Failed
                                </span>

                            {% elif payment.status == "cancelled" %}

                                <span class="badge text-bg-secondary">
                                    Cancelled
                                </span>

                            {% else %}

                                <span class="badge text-bg-warning">
                                    Pending
                                </span>

                            {% endif %}

                        </td>


                        <td>

                            {% if payment.order.payment_status == "paid" %}

                                <span class="badge text-bg-success">
                                    Paid
                                </span>

                            {% elif payment.order.payment_status == "failed" %}

                                <span class="badge text-bg-danger">
                                    Failed
                                </span>

                            {% elif payment.order.payment_status == "refunded" %}

                                <span class="badge text-bg-info">
                                    Refunded
                                </span>

                            {% else %}

                                <span class="badge text-bg-warning">
                                    Pending
                                </span>

                            {% endif %}

                        </td>


                        <td>

                            {% if payment.order.payment_review_required %}

                                <span class="badge text-bg-warning">
                                    <i class="bi bi-exclamation-triangle"></i>
                                    Review
                                </span>

                            {% else %}

                                <span class="text-muted">
                                    Clear
                                </span>

                            {% endif %}

                        </td>


                        <td>

                            {{ payment.created_at|date:"d M Y" }}

                            <small class="d-block text-muted">
                                {{ payment.created_at|date:"H:i" }}
                            </small>

                        </td>


                        <td class="text-end">

                            <a
                                href="{% url 'admin_payment_detail' payment.pk %}"
                                class="btn btn-sm btn-outline-primary"
                            >
                                <i class="bi bi-eye"></i>
                                View
                            </a>

                        </td>

                    </tr>


                {% empty %}

                    <tr>

                        <td
                            colspan="10"
                            class="text-center py-5"
                        >

                            <i
                                class="
                                    bi
                                    bi-phone
                                    fs-1
                                    text-muted
                                "
                            ></i>

                            <h5 class="mt-3">
                                No transactions found
                            </h5>

                            <p class="text-muted mb-0">
                                No M-Pesa transactions match
                                the selected filters.
                            </p>

                        </td>

                    </tr>

                {% endfor %}

            </tbody>

        </table>

    </div>


    {% if page_obj.paginator.num_pages > 1 %}

        <div
            class="
                d-flex
                justify-content-between
                align-items-center
                flex-wrap
                gap-3
                border-top
                pt-3
            "
        >

            <small class="text-muted">

                Page
                {{ page_obj.number }}
                of
                {{ page_obj.paginator.num_pages }}

            </small>


            <div class="d-flex gap-2">

                {% if page_obj.has_previous %}

                    <a
                        href="?page={{ page_obj.previous_page_number }}&q={{ query|urlencode }}&status={{ selected_status|urlencode }}&review={{ selected_review|urlencode }}"
                        class="btn btn-sm btn-outline-secondary"
                    >
                        Previous
                    </a>

                {% endif %}


                {% if page_obj.has_next %}

                    <a
                        href="?page={{ page_obj.next_page_number }}&q={{ query|urlencode }}&status={{ selected_status|urlencode }}&review={{ selected_review|urlencode }}"
                        class="btn btn-sm btn-outline-secondary"
                    >
                        Next
                    </a>

                {% endif %}

            </div>

        </div>

    {% endif %}

</div>


{% endblock %}
'''.strip() + "\n",
    encoding="utf-8",
)

print(
    "Created payment list template."
)


# ============================================================
# 7. PAYMENT DETAIL TEMPLATE
# ============================================================

detail_template.write_text(
r'''
{% extends "dashboard/admin/base.html" %}

{% block title %}
Payment | {{ order.order_number }}
{% endblock %}

{% block page_heading %}
Payment Details
{% endblock %}

{% block admin_content %}


<div class="dashboard-heading">

    <div
        class="
            d-flex
            justify-content-between
            align-items-start
            flex-wrap
            gap-3
        "
    >

        <div>

            <h1>
                M-Pesa Transaction
            </h1>

            <p>
                Order
                {{ order.order_number }}
            </p>

        </div>


        <div class="d-flex gap-2 flex-wrap">

            <a
                href="{% url 'admin_payment_list' %}"
                class="btn btn-outline-secondary"
            >
                <i class="bi bi-arrow-left"></i>
                Payments
            </a>


            <a
                href="{% url 'admin_order_detail' order.order_number %}"
                class="btn btn-outline-primary"
            >
                <i class="bi bi-bag-check"></i>
                View Order
            </a>

        </div>

    </div>

</div>


<!-- SUMMARY -->

<div class="row g-3 mb-4">

    <div class="col-md-6 col-xl-3">

        <div class="dashboard-card mini-stat">

            <span>
                Amount
            </span>

            <strong>
                KES {{ payment.amount|floatformat:2 }}
            </strong>

        </div>

    </div>


    <div class="col-md-6 col-xl-3">

        <div class="dashboard-card mini-stat">

            <span>
                Transaction
            </span>

            <strong class="fs-6">
                {{ payment.get_status_display }}
            </strong>

        </div>

    </div>


    <div class="col-md-6 col-xl-3">

        <div class="dashboard-card mini-stat">

            <span>
                Order Payment
            </span>

            <strong class="fs-6">
                {{ order.get_payment_status_display }}
            </strong>

        </div>

    </div>


    <div class="col-md-6 col-xl-3">

        <div class="dashboard-card mini-stat">

            <span>
                Successful Attempts
            </span>

            <strong>
                {{ successful_payment_count }}
            </strong>

        </div>

    </div>

</div>


<!-- REVIEW WARNING -->

{% if order.payment_review_required %}

<div class="alert alert-warning">

    <div class="d-flex gap-3">

        <i
            class="
                bi
                bi-exclamation-triangle-fill
                fs-4
            "
        ></i>


        <div>

            <strong class="d-block mb-1">
                Payment Review Required
            </strong>

            {{ order.payment_review_reason|default:"This payment requires staff review." }}

        </div>

    </div>

</div>

{% endif %}


<div class="row g-3 mb-4">


    <!-- TRANSACTION -->

    <div class="col-xl-7">

        <div class="dashboard-card h-100">

            <div class="card-header-custom">

                <div>

                    <h2>
                        Transaction Information
                    </h2>

                    <p>
                        Raw M-Pesa transaction identifiers
                        recorded by the payment system.
                    </p>

                </div>

            </div>


            <div class="table-responsive">

                <table
                    class="
                        table
                        dashboard-table
                        mb-0
                    "
                >

                    <tbody>

                        <tr>

                            <th style="width:34%;">
                                M-Pesa Receipt
                            </th>

                            <td>

                                {% if payment.mpesa_receipt_number %}

                                    <code>
                                        {{ payment.mpesa_receipt_number }}
                                    </code>

                                {% else %}
                                    —
                                {% endif %}

                            </td>

                        </tr>


                        <tr>

                            <th>
                                Phone Number
                            </th>

                            <td>
                                {{ payment.phone_number }}
                            </td>

                        </tr>


                        <tr>

                            <th>
                                Amount
                            </th>

                            <td>
                                KES {{ payment.amount|floatformat:2 }}
                            </td>

                        </tr>


                        <tr>

                            <th>
                                Status
                            </th>

                            <td>
                                {{ payment.get_status_display }}
                            </td>

                        </tr>


                        <tr>

                            <th>
                                Result Code
                            </th>

                            <td>
                                {{ payment.result_code|default:"—" }}
                            </td>

                        </tr>


                        <tr>

                            <th>
                                Result Description
                            </th>

                            <td>
                                {{ payment.result_description|default:"—" }}
                            </td>

                        </tr>


                        <tr>

                            <th>
                                Merchant Request ID
                            </th>

                            <td>
                                <code>
                                    {{ payment.merchant_request_id|default:"—" }}
                                </code>
                            </td>

                        </tr>


                        <tr>

                            <th>
                                Checkout Request ID
                            </th>

                            <td>
                                <code>
                                    {{ payment.checkout_request_id|default:"—" }}
                                </code>
                            </td>

                        </tr>


                        <tr>

                            <th>
                                Created
                            </th>

                            <td>
                                {{ payment.created_at|date:"d M Y H:i:s" }}
                            </td>

                        </tr>


                        <tr>

                            <th>
                                Last Updated
                            </th>

                            <td>
                                {{ payment.updated_at|date:"d M Y H:i:s" }}
                            </td>

                        </tr>

                    </tbody>

                </table>

            </div>

        </div>

    </div>


    <!-- ORDER / CUSTOMER -->

    <div class="col-xl-5">

        <div class="dashboard-card h-100">

            <div class="card-header-custom">

                <div>

                    <h2>
                        Order & Customer
                    </h2>

                    <p>
                        Related ecommerce record.
                    </p>

                </div>

            </div>


            <dl class="row mb-0">

                <dt class="col-5">
                    Order
                </dt>

                <dd class="col-7">
                    {{ order.order_number }}
                </dd>


                <dt class="col-5">
                    Customer
                </dt>

                <dd class="col-7">

                    {% if order.user.get_full_name %}

                        {{ order.user.get_full_name }}

                    {% else %}

                        {{ order.user.username }}

                    {% endif %}

                </dd>


                <dt class="col-5">
                    Email
                </dt>

                <dd class="col-7">
                    {{ order.user.email|default:"—" }}
                </dd>


                <dt class="col-5">
                    Order Total
                </dt>

                <dd class="col-7">
                    KES {{ order.total_amount|floatformat:2 }}
                </dd>


                <dt class="col-5">
                    Successful Paid
                </dt>

                <dd class="col-7">
                    KES {{ successful_payment_total|floatformat:2 }}
                </dd>


                <dt class="col-5">
                    Order Status
                </dt>

                <dd class="col-7">
                    {{ order.get_status_display }}
                </dd>


                <dt class="col-5">
                    Payment Status
                </dt>

                <dd class="col-7">
                    {{ order.get_payment_status_display }}
                </dd>


                <dt class="col-5">
                    Inventory
                </dt>

                <dd class="col-7">
                    {{ order.get_inventory_status_display }}
                </dd>

            </dl>


            <hr>


            <a
                href="{% url 'admin_order_detail' order.order_number %}"
                class="btn btn-outline-primary"
            >
                Open Full Order
            </a>

        </div>

    </div>

</div>


<!-- ======================================================
     PAYMENT REVIEW
====================================================== -->

<div class="dashboard-card mb-4">

    <div class="card-header-custom">

        <div>

            <h2>
                Reconciliation Review
            </h2>

            <p>
                Staff audit trail for exceptional payment cases.
            </p>

        </div>


        {% if order.payment_review_required %}

            <span class="badge text-bg-warning">
                Open
            </span>

        {% else %}

            <span class="badge text-bg-success">
                Clear
            </span>

        {% endif %}

    </div>


    {% if order.payment_review_reason %}

        <div class="mb-4">

            <label class="form-label fw-semibold">
                Review Reason
            </label>

            <div
                class="
                    border
                    rounded
                    p-3
                    bg-body-tertiary
                "
            >
                {{ order.payment_review_reason }}
            </div>

        </div>

    {% endif %}


    {% if order.payment_review_resolution %}

        <div class="mb-4">

            <label class="form-label fw-semibold">
                Last Resolution
            </label>

            <div
                class="
                    border
                    rounded
                    p-3
                "
            >

                <div style="white-space:pre-wrap;">{{ order.payment_review_resolution }}</div>


                {% if order.payment_review_resolved_at %}

                    <small class="d-block text-muted mt-2">

                        Resolved

                        {{ order.payment_review_resolved_at|date:"d M Y H:i" }}

                        {% if order.payment_review_resolved_by %}

                            by

                            {{ order.payment_review_resolved_by.get_full_name|default:order.payment_review_resolved_by.username }}

                        {% endif %}

                    </small>

                {% endif %}

            </div>

        </div>

    {% endif %}


    {% if order.payment_review_required %}

        <form
            method="POST"
            action="{% url 'admin_payment_review_resolve' payment.pk %}"
        >

            {% csrf_token %}

            <label
                class="
                    form-label
                    fw-semibold
                "
            >
                Resolution Note
            </label>

            {{ review_form.resolution }}

            <div class="form-text mb-3">

                Record what you verified before
                closing this payment-review case.

            </div>


            <button
                type="submit"
                class="btn btn-success"
                onclick="return confirm('Mark this payment review as resolved?');"
            >
                <i class="bi bi-check-circle"></i>
                Resolve Review
            </button>

        </form>

    {% else %}

        <form
            method="POST"
            action="{% url 'admin_payment_review_reopen' payment.pk %}"
        >

            {% csrf_token %}

            <button
                type="submit"
                class="btn btn-outline-warning"
            >
                <i class="bi bi-arrow-counterclockwise"></i>
                Reopen Review
            </button>

        </form>

    {% endif %}

</div>


<!-- ======================================================
     ALL STK ATTEMPTS FOR ORDER
====================================================== -->

<div class="dashboard-card">

    <div class="card-header-custom">

        <div>

            <h2>
                All M-Pesa Attempts
            </h2>

            <p>
                Every STK transaction linked
                to order {{ order.order_number }}.
            </p>

        </div>

        <span class="badge text-bg-light border">

            {{ all_order_transactions.count }}
            attempt{{ all_order_transactions.count|pluralize }}

        </span>

    </div>


    <div class="table-responsive">

        <table
            class="
                table
                dashboard-table
                align-middle
            "
        >

            <thead>

                <tr>

                    <th>
                        Date
                    </th>

                    <th>
                        Phone
                    </th>

                    <th>
                        Amount
                    </th>

                    <th>
                        Status
                    </th>

                    <th>
                        Receipt
                    </th>

                    <th>
                        Result
                    </th>

                    <th class="text-end">
                        Action
                    </th>

                </tr>

            </thead>


            <tbody>

                {% for tx in all_order_transactions %}

                    <tr
                        {% if tx.pk == payment.pk %}
                            class="table-active"
                        {% endif %}
                    >

                        <td>
                            {{ tx.created_at|date:"d M Y H:i" }}
                        </td>


                        <td>
                            {{ tx.phone_number }}
                        </td>


                        <td>
                            KES {{ tx.amount|floatformat:2 }}
                        </td>


                        <td>
                            {{ tx.get_status_display }}
                        </td>


                        <td>
                            {{ tx.mpesa_receipt_number|default:"—" }}
                        </td>


                        <td>
                            {{ tx.result_description|default:"—"|truncatechars:50 }}
                        </td>


                        <td class="text-end">

                            <a
                                href="{% url 'admin_payment_detail' tx.pk %}"
                                class="btn btn-sm btn-outline-primary"
                            >
                                View
                            </a>

                        </td>

                    </tr>

                {% endfor %}

            </tbody>

        </table>

    </div>

</div>


{% endblock %}
'''.strip() + "\n",
    encoding="utf-8",
)

print(
    "Created payment detail template."
)


# ============================================================
# 8. ACTIVATE PAYMENTS SIDEBAR
# ============================================================

text = base_template.read_text(
    encoding="utf-8-sig"
)

if (
    "admin_payment_list"
    not in text
):

    payment_pos = text.find(
        "<span>\n                    Payments\n                </span>"
    )

    if payment_pos == -1:

        payment_pos = text.find(
            "<span>Payments</span>"
        )

    if payment_pos == -1:

        raise RuntimeError(
            "Could not locate Payments sidebar entry."
        )

    link_start = text.rfind(
        "<a",
        0,
        payment_pos,
    )

    link_end = text.find(
        "</a>",
        payment_pos,
    )

    if (
        link_start == -1
        or link_end == -1
    ):

        raise RuntimeError(
            "Could not determine Payments link boundaries."
        )

    link_end += len("</a>")

    replacement = r'''
            <a
                href="{% url 'admin_payment_list' %}"
                class="
                    sidebar-link
                    {% if 'admin_payment' in request.resolver_match.url_name %}
                        active
                    {% endif %}
                "
            >

                <i class="bi bi-phone"></i>

                <span>
                    Payments
                </span>

            </a>'''

    text = (
        text[:link_start]
        + replacement
        + text[link_end:]
    )

    base_template.write_text(
        text,
        encoding="utf-8",
    )

    print(
        "Activated Payments sidebar."
    )

else:

    print(
        "Payments sidebar already active."
    )


# ============================================================
# 9. TESTS
# ============================================================

tests_path.write_text(
r'''
from decimal import Decimal

from django.contrib.auth import (
    get_user_model,
)

from django.test import TestCase

from django.urls import reverse

from orders.models import Order

from payments.models import (
    MpesaTransaction,
)


User = get_user_model()


class AdminPaymentTests(TestCase):

    def setUp(self):

        self.staff = (
            User.objects.create_user(
                username="paymentadmin",
                password="testpass123",
                role=User.ADMIN,
                is_staff=True,
                is_active=True,
            )
        )

        self.customer = (
            User.objects.create_user(
                username="paymentbuyer",
                password="testpass123",
                email="buyer@example.com",
                phone="0712345678",
                role=User.CUSTOMER,
            )
        )

        self.order = (
            Order.objects.create(
                user=self.customer,
                order_number="PAY-TEST-001",
                full_name="Payment Buyer",
                phone="0712345678",
                email="buyer@example.com",
                county="Nairobi",
                city="Nairobi",
                estate="CBD",
                house_number="1",
                subtotal=Decimal(
                    "2500.00"
                ),
                shipping_cost=Decimal(
                    "0.00"
                ),
                discount=Decimal(
                    "0.00"
                ),
                total_amount=Decimal(
                    "2500.00"
                ),
                payment_status="paid",
                inventory_status="consumed",
                status="confirmed",
                payment_review_required=True,
                payment_review_reason=(
                    "Possible duplicate payment."
                ),
            )
        )

        self.payment = (
            MpesaTransaction.objects.create(
                order=self.order,
                phone_number="0712345678",
                amount=Decimal(
                    "2500.00"
                ),
                merchant_request_id=(
                    "MERCHANT-TEST"
                ),
                checkout_request_id=(
                    "CHECKOUT-TEST"
                ),
                mpesa_receipt_number=(
                    "TESTRECEIPT"
                ),
                status="success",
                result_code="0",
                result_description=(
                    "Processed successfully"
                ),
            )
        )

    def test_payment_list_requires_staff(
        self
    ):

        response = self.client.get(
            reverse(
                "admin_payment_list"
            )
        )

        self.assertNotEqual(
            response.status_code,
            200,
        )

        self.client.login(
            username="paymentadmin",
            password="testpass123",
        )

        response = self.client.get(
            reverse(
                "admin_payment_list"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_payment_detail(
        self
    ):

        self.client.login(
            username="paymentadmin",
            password="testpass123",
        )

        response = self.client.get(
            reverse(
                "admin_payment_detail",
                kwargs={
                    "pk": self.payment.pk
                },
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "TESTRECEIPT",
        )

    def test_payment_review_resolution(
        self
    ):

        self.client.login(
            username="paymentadmin",
            password="testpass123",
        )

        response = self.client.post(
            reverse(
                "admin_payment_review_resolve",
                kwargs={
                    "pk": self.payment.pk
                },
            ),
            {
                "resolution": (
                    "Verified duplicate payment "
                    "and escalated for refund."
                ),
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.order.refresh_from_db()

        self.assertFalse(
            self.order.payment_review_required
        )

        self.assertTrue(
            self.order.payment_review_resolution
        )

        self.assertEqual(
            self.order.payment_review_resolved_by,
            self.staff,
        )
'''.strip() + "\n",
    encoding="utf-8",
)

print(
    "Created payment admin tests."
)


print()
print("=" * 68)
print("PHASE 6 M-PESA MANAGEMENT PATCH COMPLETE")
print("=" * 68)
print()
print("Run:")
print("python manage.py makemigrations orders")
print("python manage.py migrate")
print("python manage.py check")
