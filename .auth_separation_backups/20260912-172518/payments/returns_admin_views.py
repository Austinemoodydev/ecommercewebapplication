from decimal import Decimal

from django.contrib import messages

from django.contrib.admin.views.decorators import (
    staff_member_required,
)

from django.core.paginator import Paginator

from django.db import transaction

from django.db.models import (
    Q,
    Sum,
)

from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from django.utils import timezone

from inventory.services import (
    adjust_product_stock,
    adjust_variant_stock,
)

from orders.models import Order

from .returns_services import (
    processed_refund_total,
    remaining_refundable_amount,
)

from .models import (
    RefundRequest,
    ReturnRefundEvent,
    ReturnRequest,
)




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


@staff_member_required
def returns_refunds_list(
    request,
):

    tab = request.GET.get(
        "tab",
        "returns",
    )

    status = request.GET.get(
        "status",
        "",
    ).strip()

    query = request.GET.get(
        "q",
        "",
    ).strip()


    returns = (
        ReturnRequest.objects
        .select_related(
            "order",
            "order__user",
        )
        .prefetch_related(
            "items",
        )
        .order_by(
            "-created_at"
        )
    )


    refunds = (
        RefundRequest.objects
        .select_related(
            "order",
            "order__user",
        )
        .order_by(
            "-created_at"
        )
    )


    if query:

        lookup = (
            Q(
                order__order_number__icontains=query
            )
            | Q(
                order__full_name__icontains=query
            )
            | Q(
                order__phone__icontains=query
            )
        )

        returns = returns.filter(
            lookup
        )

        refunds = refunds.filter(
            lookup
        )


    if status:

        returns = returns.filter(
            status=status
        )

        refunds = refunds.filter(
            status=status
        )


    counts = {

        "return_requested": (
            ReturnRequest.objects.filter(
                status="requested"
            ).count()
        ),

        "return_approved": (
            ReturnRequest.objects.filter(
                status="approved"
            ).count()
        ),

        "refund_requested": (
            RefundRequest.objects.filter(
                status="requested"
            ).count()
        ),

        "refund_approved": (
            RefundRequest.objects.filter(
                status="approved"
            ).count()
        ),
    }


    queryset = (
        refunds
        if tab == "refunds"
        else returns
    )


    paginator = Paginator(
        queryset,
        25,
    )

    page_obj = paginator.get_page(
        request.GET.get("page")
    )


    return render(
        request,
        "dashboard/admin/returns/list.html",
        {
            "tab": tab,
            "records": (
                page_obj.object_list
            ),
            "page_obj": page_obj,
            "status": status,
            "query": query,
            "counts": counts,
        },
    )


@staff_member_required
def return_detail(
    request,
    pk,
):

    return_request = get_object_or_404(
        ReturnRequest.objects
        .select_related(
            "order",
            "order__user",
            "processed_by",
        )
        .prefetch_related(
            "items__order_item",
            "events__created_by",
        ),
        pk=pk,
    )

    return render(
        request,
        "dashboard/admin/returns/return_detail.html",
        {
            "return_request": (
                return_request
            ),
            "order": return_request.order,
        },
    )


@staff_member_required
@transaction.atomic
def return_review(
    request,
    pk,
):

    return_request = get_object_or_404(
        ReturnRequest.objects
        .select_for_update(),
        pk=pk,
    )


    if request.method != "POST":

        return redirect(
            "admin_return_detail",
            pk=pk,
        )


    action = request.POST.get(
        "action",
        "",
    )

    note = request.POST.get(
        "staff_note",
        "",
    ).strip()


    if (
        return_request.status
        != "requested"
    ):

        messages.error(
            request,
            "Only requested returns can be reviewed.",
        )

        return redirect(
            "admin_return_detail",
            pk=pk,
        )


    if action not in {
        "approve",
        "reject",
    }:

        messages.error(
            request,
            "Invalid action.",
        )

        return redirect(
            "admin_return_detail",
            pk=pk,
        )


    if (
        action == "reject"
        and not note
    ):

        messages.error(
            request,
            "Add a reason before rejecting.",
        )

        return redirect(
            "admin_return_detail",
            pk=pk,
        )


    return_request.status = (
        "approved"
        if action == "approve"
        else "rejected"
    )

    return_request.staff_note = note

    return_request.processed_by = (
        request.user
    )

    return_request.save(
        update_fields=[
            "status",
            "staff_note",
            "processed_by",
            "updated_at",
        ]
    )


    ReturnRefundEvent.objects.create(
        return_request=return_request,
        status=return_request.status,
        message=(
            note
            or (
                "Return request approved."
                if action == "approve"
                else "Return request rejected."
            )
        ),
        created_by=request.user,
    )


    transaction.on_commit(
        lambda pk=return_request.pk: (
            _queue_return_notification(
                pk
            )
        ),
        robust=True,
    )


    messages.success(
        request,
        (
            "Return approved."
            if action == "approve"
            else "Return rejected."
        ),
    )


    return redirect(
        "admin_return_detail",
        pk=pk,
    )


@staff_member_required
@transaction.atomic
def return_complete(
    request,
    pk,
):

    return_request = get_object_or_404(
        ReturnRequest.objects
        .select_for_update()
        .select_related(
            "order"
        )
        .prefetch_related(
            "items__order_item",
        ),
        pk=pk,
    )


    if request.method != "POST":

        return redirect(
            "admin_return_detail",
            pk=pk,
        )


    if (
        return_request.status
        != "approved"
    ):

        messages.error(
            request,
            "Approve the return before completing it.",
        )

        return redirect(
            "admin_return_detail",
            pk=pk,
        )


    if return_request.inventory_restored:

        messages.error(
            request,
            "Inventory has already been restored.",
        )

        return redirect(
            "admin_return_detail",
            pk=pk,
        )


    restored_any = False


    for item in return_request.items.all():

        should_restock = (
            request.POST.get(
                f"restock_{item.pk}"
            )
            == "1"
        )

        item.restock = should_restock

        item.save(
            update_fields=[
                "restock"
            ]
        )


        if not should_restock:
            continue


        order_item = item.order_item

        reference = (
            f"RETURN-{return_request.pk}-"
            f"{return_request.order.order_number}"
        )


        if order_item.variant_id:

            adjust_variant_stock(
                variant_id=(
                    order_item.variant_id
                ),
                movement_type="return",
                quantity=item.quantity,
                reference=reference,
                notes=(
                    "Customer return accepted "
                    "back into sellable inventory."
                ),
                user=request.user,
            )

        else:

            adjust_product_stock(
                product_id=(
                    order_item.product_id
                ),
                movement_type="return",
                quantity=item.quantity,
                reference=reference,
                notes=(
                    "Customer return accepted "
                    "back into sellable inventory."
                ),
                user=request.user,
            )


        restored_any = True


    return_request.status = (
        "completed"
    )

    return_request.received_at = (
        timezone.now()
    )

    return_request.completed_at = (
        timezone.now()
    )

    return_request.inventory_restored = (
        restored_any
    )

    return_request.processed_by = (
        request.user
    )

    return_request.save(
        update_fields=[
            "status",
            "received_at",
            "completed_at",
            "inventory_restored",
            "processed_by",
            "updated_at",
        ]
    )


    ReturnRefundEvent.objects.create(
        return_request=return_request,
        status="completed",
        message=(
            "Return completed. "
            + (
                "Selected items were restored "
                "to inventory."
                if restored_any
                else (
                    "No items were marked as "
                    "restockable."
                )
            )
        ),
        created_by=request.user,
    )


    transaction.on_commit(
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


    return redirect(
        "admin_return_detail",
        pk=pk,
    )


@staff_member_required
def refund_detail(
    request,
    pk,
):

    refund = get_object_or_404(
        RefundRequest.objects
        .select_related(
            "order",
            "order__user",
            "processed_by",
        )
        .prefetch_related(
            "events__created_by"
        ),
        pk=pk,
    )

    processed_total = (
        RefundRequest.objects
        .filter(
            order=refund.order,
            status="processed",
        )
        .aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )


    return render(
        request,
        "dashboard/admin/returns/refund_detail.html",
        {
            "refund": refund,
            "order": refund.order,
            "processed_total": (
                processed_total
            ),
        },
    )


@staff_member_required
@transaction.atomic
def refund_review(
    request,
    pk,
):

    refund = get_object_or_404(
        RefundRequest.objects
        .select_for_update()
        .select_related(
            "order"
        ),
        pk=pk,
    )


    if request.method != "POST":

        return redirect(
            "admin_refund_detail",
            pk=pk,
        )


    if refund.status != "requested":

        messages.error(
            request,
            "Only requested refunds can be reviewed.",
        )

        return redirect(
            "admin_refund_detail",
            pk=pk,
        )


    action = request.POST.get(
        "action",
        "",
    )

    note = request.POST.get(
        "staff_note",
        "",
    ).strip()


    if action not in {
        "approve",
        "reject",
    }:

        messages.error(
            request,
            "Invalid action.",
        )

        return redirect(
            "admin_refund_detail",
            pk=pk,
        )


    if (
        action == "reject"
        and not note
    ):

        messages.error(
            request,
            "Add a reason before rejecting.",
        )

        return redirect(
            "admin_refund_detail",
            pk=pk,
        )


    refund.status = (
        "approved"
        if action == "approve"
        else "rejected"
    )

    refund.staff_note = note

    refund.processed_by = (
        request.user
    )

    refund.save(
        update_fields=[
            "status",
            "staff_note",
            "processed_by",
            "updated_at",
        ]
    )


    ReturnRefundEvent.objects.create(
        refund=refund,
        status=refund.status,
        message=(
            note
            or (
                "Refund approved."
                if action == "approve"
                else "Refund rejected."
            )
        ),
        created_by=request.user,
    )


    transaction.on_commit(
        lambda pk=refund.pk: (
            _queue_refund_notification(
                pk
            )
        ),
        robust=True,
    )


    messages.success(
        request,
        (
            "Refund approved."
            if action == "approve"
            else "Refund rejected."
        ),
    )


    return redirect(
        "admin_refund_detail",
        pk=pk,
    )


@staff_member_required
@transaction.atomic
def refund_process(
    request,
    pk,
):

    refund = get_object_or_404(
        RefundRequest.objects
        .select_for_update()
        .select_related(
            "order"
        ),
        pk=pk,
    )


    if request.method != "POST":

        return redirect(
            "admin_refund_detail",
            pk=pk,
        )


    if refund.status != "approved":

        messages.error(
            request,
            "Approve the refund before processing it.",
        )

        return redirect(
            "admin_refund_detail",
            pk=pk,
        )


    remaining = (
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


    reference = request.POST.get(
        "external_reference",
        "",
    ).strip()


    if not reference:

        messages.error(
            request,
            (
                "Enter the actual M-PESA, bank, "
                "cash or other refund reference."
            ),
        )

        return redirect(
            "admin_refund_detail",
            pk=pk,
        )


    refund.status = "processed"

    refund.external_reference = (
        reference
    )

    refund.processed_by = (
        request.user
    )

    refund.processed_at = (
        timezone.now()
    )

    refund.save(
        update_fields=[
            "status",
            "external_reference",
            "processed_by",
            "processed_at",
            "updated_at",
        ]
    )


    processed_total = (
        RefundRequest.objects
        .filter(
            order=refund.order,
            status="processed",
        )
        .aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
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


    ReturnRefundEvent.objects.create(
        refund=refund,
        status="processed",
        message=(
            "Refund recorded with reference "
            f"{reference}."
        ),
        created_by=request.user,
    )


    transaction.on_commit(
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


    return redirect(
        "admin_refund_detail",
        pk=pk,
    )
