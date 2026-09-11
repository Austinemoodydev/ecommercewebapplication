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
