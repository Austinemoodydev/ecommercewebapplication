from decimal import Decimal

from django.contrib.auth.decorators import (
    login_required,
)

from django.db import transaction

from django.db.models import Sum

from django.http import JsonResponse, Http404

from django.shortcuts import (
    get_object_or_404,
    render,
)

from orders.models import Order

from orders.guest_access import (
    verify_guest_access_token,
)

from .forms import RefundRequestForm

from .returns_services import (
    get_return_deadline,
    remaining_refundable_amount,
    remaining_returnable_quantity,
    return_window_open,
)

from .models import (
    RefundRequest,
    ReturnRefundEvent,
    ReturnRequest,
    ReturnRequestItem,
)




SETTLED_RETURN_PAYMENT_STATUSES = {
    "paid",
    "partially_refunded",
    "refunded",
}

REFUND_ELIGIBLE_PAYMENT_STATUSES = {
    "paid",
    "partially_refunded",
}


def _get_guest_order(
    order_number,
    token,
    *,
    lock=False,
    prefetch_items=False,
):

    queryset = Order.objects


    if lock:
        queryset = (
            queryset.select_for_update()
        )


    if prefetch_items:
        queryset = (
            queryset.prefetch_related(
                "items"
            )
        )


    order = get_object_or_404(
        queryset,
        order_number=order_number,
        guest_checkout=True,
        user__isnull=True,
    )


    if not verify_guest_access_token(
        order,
        token,
    ):

        raise Http404(
            "Order not found."
        )


    return order



@login_required
@transaction.atomic
def request_refund(
    request,
    order_number,
):

    order = get_object_or_404(
        Order.objects.select_for_update(),
        order_number=order_number,
        user=request.user,
    )

    if (
        order.payment_status not in REFUND_ELIGIBLE_PAYMENT_STATUSES
        or order.status != "delivered"
    ):

        return JsonResponse(
            {
                "success": False,
                "error": (
                    "Refunds are available only "
                    "for paid delivered orders."
                ),
            },
            status=400,
        )


    processed_total = (
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

    refundable_amount = (
        order.total_amount
        - processed_total
    )


    if refundable_amount <= 0:

        return JsonResponse(
            {
                "success": False,
                "error": (
                    "This order has already been "
                    "fully refunded."
                ),
            },
            status=400,
        )


    if RefundRequest.objects.filter(
        order=order,
        status__in=[
            "requested",
            "approved",
        ],
    ).exists():

        return JsonResponse(
            {
                "success": False,
                "error": (
                    "An active refund request "
                    "already exists."
                ),
            },
            status=400,
        )


    if request.method != "POST":

        form = RefundRequestForm(
            order=order
        )

        form.fields[
            "amount"
        ].initial = refundable_amount

        return render(
            request,
            "payments/refund_request.html",
            {
                "order": order,
                "form": form,
                "refundable_amount": (
                    refundable_amount
                ),
            },
        )


    form = RefundRequestForm(
        request.POST,
        order=order,
    )


    if form.is_valid():

        amount = form.cleaned_data[
            "amount"
        ]

        if amount > refundable_amount:

            form.add_error(
                "amount",
                (
                    "Refund amount exceeds the "
                    "remaining refundable balance."
                ),
            )

        else:

            refund = form.save(
                commit=False
            )

            refund.order = order

            refund.save()

            ReturnRefundEvent.objects.create(
                refund=refund,
                status="requested",
                message=(
                    "Customer submitted "
                    "refund request."
                ),
                created_by=request.user,
            )

            return render(
                request,
                "payments/refund_submitted.html",
                {
                    "refund": refund
                },
            )


    return render(
        request,
        "payments/refund_request.html",
        {
            "order": order,
            "form": form,
            "refundable_amount": (
                refundable_amount
            ),
        },
    )


@login_required
@transaction.atomic
def request_return(
    request,
    order_number,
):

    order = get_object_or_404(
        Order.objects
        .select_for_update()
        .prefetch_related(
            "items"
        ),
        order_number=order_number,
        user=request.user,
    )


    if (
        order.payment_status not in SETTLED_RETURN_PAYMENT_STATUSES
        or order.status != "delivered"
    ):

        return JsonResponse(
            {
                "success": False,
                "error": (
                    "Returns are available only "
                    "for paid delivered orders."
                ),
            },
            status=400,
        )


    if ReturnRequest.objects.filter(
        order=order,
        status__in=[
            "requested",
            "approved",
        ],
    ).exists():

        return JsonResponse(
            {
                "success": False,
                "error": (
                    "An active return request "
                    "already exists."
                ),
            },
            status=400,
        )


    if not return_window_open(
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


    items = list(
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


    if request.method == "POST":

        request_type = (
            request.POST.get(
                "request_type",
                ""
            )
        )

        reason = (
            request.POST.get(
                "reason",
                ""
            ).strip()
        )


        if request_type not in {
            "return",
            "replacement",
        }:

            error = (
                "Select Return or Replacement."
            )

        elif not reason:

            error = (
                "Please explain why you are "
                "returning the item."
            )

        else:

            selected = []

            quantity_fields_present = any(
                key.startswith("quantity_")
                for key in request.POST.keys()
            )

            for item in items:

                # -------------------------------------------------
                # BACKWARD COMPATIBILITY
                # -------------------------------------------------
                #
                # Phase 8A introduced item-level quantities.
                # Older clients/tests posted a whole-order
                # return/replacement without quantity_* fields.
                #
                # If NO quantity field exists in the POST at all,
                # preserve the former whole-order behaviour.
                #
                # The current Phase 8A form always sends the
                # quantity fields, so normal modern requests are
                # unaffected.
                # -------------------------------------------------

                if not quantity_fields_present:

                    raw_quantity = str(
                        item.quantity
                    )

                else:

                    raw_quantity = (
                        request.POST.get(
                            f"quantity_{item.pk}",
                            "0",
                        )
                    )

                try:

                    quantity = int(
                        raw_quantity
                    )

                except (
                    TypeError,
                    ValueError,
                ):

                    quantity = 0


                if quantity < 0:

                    error = (
                        "Return quantity cannot "
                        "be negative."
                    )

                    break


                remaining_quantity = (
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


                if quantity:

                    selected.append(
                        (
                            item,
                            quantity,
                        )
                    )

            else:

                error = None


            if (
                not error
                and not selected
                and items
            ):

                error = (
                    "Select at least one item "
                    "to return."
                )


        if not error:

            return_request = (
                ReturnRequest.objects.create(
                    order=order,
                    request_type=request_type,
                    reason=reason,
                )
            )


            for (
                item,
                quantity,
            ) in selected:

                ReturnRequestItem.objects.create(
                    return_request=(
                        return_request
                    ),
                    order_item=item,
                    quantity=quantity,
                )


            ReturnRefundEvent.objects.create(
                return_request=(
                    return_request
                ),
                status="requested",
                message=(
                    "Customer submitted "
                    f"{return_request.get_request_type_display().lower()} "
                    "request."
                ),
                created_by=request.user,
            )


            return render(
                request,
                "payments/return_submitted.html",
                {
                    "return_request": (
                        return_request
                    )
                },
            )


        return render(
            request,
            "payments/return_request_v2.html",
            {
                "order": order,
                "items": items,
                "error": error,
                "request_type": request_type,
                "reason": reason,
            },
        )


    return render(
        request,
        "payments/return_request_v2.html",
        {
            "order": order,
            "items": items,
        },
    )



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


@transaction.atomic
def guest_request_refund(
    request,
    order_number,
    token,
):

    order = _get_guest_order(
        order_number,
        token,
        lock=True,
    )


    if (
        order.payment_status
        not in REFUND_ELIGIBLE_PAYMENT_STATUSES
        or
        order.status != "delivered"
    ):

        return JsonResponse(
            {
                "success": False,
                "error": (
                    "Refunds are available only "
                    "for paid delivered orders."
                ),
            },
            status=400,
        )


    refundable_amount = (
        remaining_refundable_amount(
            order,
            include_pending=True,
        )
    )


    if refundable_amount <= 0:

        return JsonResponse(
            {
                "success": False,
                "error": (
                    "This order has no remaining "
                    "refundable balance."
                ),
            },
            status=400,
        )


    if RefundRequest.objects.filter(
        order=order,
        status__in=[
            "requested",
            "approved",
        ],
    ).exists():

        return JsonResponse(
            {
                "success": False,
                "error": (
                    "An active refund request "
                    "already exists."
                ),
            },
            status=400,
        )


    if request.method != "POST":

        form = RefundRequestForm(
            order=order
        )

        form.fields[
            "amount"
        ].initial = (
            refundable_amount
        )


        return render(
            request,
            "payments/refund_request.html",
            {
                "order": order,
                "form": form,
                "refundable_amount":
                    refundable_amount,
                "is_guest_request": True,
                "guest_access_token": token,
            },
        )


    form = RefundRequestForm(
        request.POST,
        order=order,
    )


    if form.is_valid():

        amount = (
            form.cleaned_data[
                "amount"
            ]
        )


        if amount > refundable_amount:

            form.add_error(
                "amount",
                (
                    "Refund amount exceeds the "
                    "remaining refundable balance."
                ),
            )

        else:

            refund = form.save(
                commit=False
            )

            refund.order = order
            refund.save()


            ReturnRefundEvent.objects.create(
                refund=refund,
                status="requested",
                message=(
                    "Guest customer submitted "
                    "refund request."
                ),
                created_by=None,
            )


            return render(
                request,
                "payments/refund_submitted.html",
                {
                    "refund": refund,
                    "is_guest_request": True,
                    "guest_access_token": token,
                },
            )


    return render(
        request,
        "payments/refund_request.html",
        {
            "order": order,
            "form": form,
            "refundable_amount":
                refundable_amount,
            "is_guest_request": True,
            "guest_access_token": token,
        },
    )



@transaction.atomic
def guest_request_return(
    request,
    order_number,
    token,
):

    order = _get_guest_order(
        order_number,
        token,
        lock=True,
        prefetch_items=True,
    )


    if (
        order.payment_status
        not in SETTLED_RETURN_PAYMENT_STATUSES
        or
        order.status != "delivered"
    ):

        return JsonResponse(
            {
                "success": False,
                "error": (
                    "Returns are available only "
                    "for paid delivered orders."
                ),
            },
            status=400,
        )


    if ReturnRequest.objects.filter(
        order=order,
        status__in=[
            "requested",
            "approved",
        ],
    ).exists():

        return JsonResponse(
            {
                "success": False,
                "error": (
                    "An active return request "
                    "already exists."
                ),
            },
            status=400,
        )


    if not return_window_open(
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


    items = list(
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


    context = {
        "order": order,
        "items": items,
        "is_guest_request": True,
        "guest_access_token": token,
    }


    if request.method == "POST":

        request_type = (
            request.POST.get(
                "request_type",
                ""
            )
        )


        reason = (
            request.POST.get(
                "reason",
                ""
            ).strip()
        )


        error = None


        if request_type not in {
            "return",
            "replacement",
        }:

            error = (
                "Select Return or Replacement."
            )


        elif not reason:

            error = (
                "Please explain why you are "
                "returning the item."
            )


        else:

            selected = []


            for item in items:

                raw_quantity = (
                    request.POST.get(
                        f"quantity_{item.pk}",
                        "0",
                    )
                )


                try:

                    quantity = int(
                        raw_quantity
                    )

                except (
                    TypeError,
                    ValueError,
                ):

                    quantity = 0


                if quantity < 0:

                    error = (
                        "Return quantity cannot "
                        "be negative."
                    )

                    break


                remaining_quantity = (
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


                if quantity:

                    selected.append(
                        (
                            item,
                            quantity,
                        )
                    )


            if (
                not error
                and
                not selected
                and
                items
            ):

                error = (
                    "Select at least one item "
                    "to return."
                )


        if not error:

            return_request = (
                ReturnRequest.objects.create(
                    order=order,
                    request_type=request_type,
                    reason=reason,
                )
            )


            for item, quantity in selected:

                ReturnRequestItem.objects.create(
                    return_request=
                        return_request,
                    order_item=item,
                    quantity=quantity,
                )


            ReturnRefundEvent.objects.create(
                return_request=
                    return_request,
                status="requested",
                message=(
                    "Guest customer submitted "
                    f"{return_request.get_request_type_display().lower()} "
                    "request."
                ),
                created_by=None,
            )


            return render(
                request,
                "payments/return_submitted.html",
                {
                    "return_request":
                        return_request,
                    "is_guest_request":
                        True,
                    "guest_access_token":
                        token,
                },
            )


        context.update(
            {
                "error": error,
                "request_type":
                    request_type,
                "reason": reason,
            }
        )


    return render(
        request,
        "payments/return_request_v2.html",
        context,
    )



def guest_return_detail(
    request,
    order_number,
    token,
    pk,
):

    order = _get_guest_order(
        order_number,
        token,
    )


    obj = get_object_or_404(
        ReturnRequest.objects
        .filter(
            order=order
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
            "order": order,
            "return_deadline":
                get_return_deadline(
                    order
                ),
            "is_guest_request": True,
            "guest_access_token": token,
        },
    )



def guest_refund_detail(
    request,
    order_number,
    token,
    pk,
):

    order = _get_guest_order(
        order_number,
        token,
    )


    obj = get_object_or_404(
        RefundRequest.objects
        .filter(
            order=order
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
            "order": order,
            "is_guest_request": True,
            "guest_access_token": token,
        },
    )

