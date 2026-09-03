import json
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db import transaction as db_transaction
from django_ratelimit.decorators import ratelimit
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt

from orders.models import Order
from .models import MpesaTransaction
from .forms import RefundRequestForm, ReturnRequestForm
from .models import RefundRequest, ReturnRequest
from .mpesa import MpesaError, stk_push


@login_required
@ratelimit(key="user", rate="5/m", method="POST", block=True)
def initiate_payment(request, order_number):

    order = get_object_or_404(Order, order_number=order_number, user=request.user)

    if order.payment_status == "paid":
        return JsonResponse({"success": False, "error": "This order has already been paid."}, status=400)
    if order.status == "cancelled":
        return JsonResponse({"success": False, "error": "This order has been cancelled."}, status=400)

    if request.method == "POST":

        phone_number = request.POST.get("phone_number", order.phone)

        try:
            response = stk_push(
                phone_number=phone_number,
                amount=order.total_amount,
                order_number=order.order_number,
            )
        except MpesaError as exc:
            return JsonResponse({"success": False, "error": str(exc)}, status=400)
        except Exception:
            return JsonResponse(
                {"success": False, "error": "Could not start the M-PESA request. Please try again."},
                status=502,
            )

        if response.get("ResponseCode") == "0":

            MpesaTransaction.objects.create(
                order=order,
                phone_number=phone_number,
                amount=order.total_amount,
                merchant_request_id=response.get("MerchantRequestID", ""),
                checkout_request_id=response.get("CheckoutRequestID", ""),
            )

            return JsonResponse({"success": True, "message": "STK push sent. Check your phone."})

        return JsonResponse({"success": False, "error": response.get("errorMessage", "Failed to initiate payment.")}, status=400)

    return render(
        request,
        "payments/pay.html",
        {
            "order": order,
        },
    )


@csrf_exempt
def mpesa_callback(request):

    from django.conf import settings

    token = request.GET.get("token")

    if not settings.MPESA_CALLBACK_SECRET or token != settings.MPESA_CALLBACK_SECRET:
        return JsonResponse({"ResultCode": 1, "ResultDesc": "Unauthorized"}, status=403)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({"ResultCode": 1, "ResultDesc": "Invalid payload"})

    body = data.get("Body")
    if not isinstance(body, dict):
        return JsonResponse({"ResultCode": 1, "ResultDesc": "Invalid payload structure"})

    stk_callback = body.get("stkCallback")
    if not isinstance(stk_callback, dict):
        return JsonResponse({"ResultCode": 1, "ResultDesc": "Invalid payload structure"})

    checkout_request_id = stk_callback.get("CheckoutRequestID")
    result_code = stk_callback.get("ResultCode")
    result_desc = stk_callback.get("ResultDesc", "")

    if checkout_request_id is None or result_code is None:
        return JsonResponse({"ResultCode": 1, "ResultDesc": "Missing required fields"})

    with db_transaction.atomic():
        transaction = MpesaTransaction.objects.select_for_update().select_related("order").filter(
            checkout_request_id=checkout_request_id
        ).first()

        if not transaction:
            return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})

        if transaction.status in ("success", "failed"):
            return JsonResponse({"ResultCode": 0, "ResultDesc": "Already processed"})

        transaction.result_code = str(result_code)
        transaction.result_description = result_desc

        if result_code == 0 and transaction.order.status == "cancelled":
            transaction.status = "failed"
            transaction.result_description = "The order was cancelled before payment completed."
        elif result_code == 0:
            metadata = stk_callback.get("CallbackMetadata", {}).get("Item", [])
            callback_values = {
                item.get("Name"): item.get("Value")
                for item in metadata
                if isinstance(item, dict) and item.get("Name")
            }
            receipt_number = callback_values.get("MpesaReceiptNumber")
            callback_amount = callback_values.get("Amount")

            if receipt_number is None or callback_amount is None:
                transaction.status = "failed"
                transaction.result_description = "M-PESA callback did not include payment metadata."
            elif int(callback_amount) != int(transaction.amount.quantize(Decimal("1"))):
                transaction.status = "failed"
                transaction.result_description = "M-PESA callback amount did not match the order amount."
            else:
                transaction.status = "success"
                transaction.mpesa_receipt_number = str(receipt_number)

                transaction.order.payment_status = "paid"
                transaction.order.status = "confirmed"
                transaction.order.save(update_fields=["payment_status", "status", "updated_at"])

                for order_item in transaction.order.items.select_related("product"):
                    inventory = order_item.variant.__class__.objects.select_for_update().get(id=order_item.variant_id) if order_item.variant_id else order_item.product.__class__.objects.select_for_update().get(id=order_item.product_id)
                    inventory.stock -= order_item.quantity
                    inventory.reserved_stock = max(inventory.reserved_stock - order_item.quantity, 0)
                    inventory.save(update_fields=["stock", "reserved_stock"] + (["updated_at"] if not order_item.variant_id else []))

        else:
            transaction.status = "failed"
            for order_item in transaction.order.items.select_related("product"):
                inventory = order_item.variant.__class__.objects.select_for_update().get(id=order_item.variant_id) if order_item.variant_id else order_item.product.__class__.objects.select_for_update().get(id=order_item.product_id)
                inventory.reserved_stock = max(inventory.reserved_stock - order_item.quantity, 0)
                inventory.save(update_fields=["reserved_stock"] + (["updated_at"] if not order_item.variant_id else []))

        transaction.save()

    if result_code == 0 and transaction.status == "success":
        from notifications.tasks import send_payment_confirmation
        try:
            db_transaction.on_commit(lambda: send_payment_confirmation.delay(transaction.order_id))
        except Exception:
            # Payment confirmation must not fail merely because Redis is down.
            pass

    return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})


@login_required
def check_payment_status(request, order_number):

    order = get_object_or_404(Order, order_number=order_number, user=request.user)

    transaction = order.mpesa_transactions.order_by("-created_at").first()

    if not transaction:
        return JsonResponse({"status": "none"})

    return JsonResponse({
        "status": transaction.status,
        "receipt": transaction.mpesa_receipt_number,
    })


@login_required
def request_refund(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    if order.payment_status != "paid" or order.status != "delivered":
        return JsonResponse({"success": False, "error": "Refunds are available only for paid delivered orders."}, status=400)
    if RefundRequest.objects.filter(order=order, status__in=("requested", "approved", "processed")).exists():
        return JsonResponse({"success": False, "error": "A refund request already exists for this order."}, status=400)
    if request.method != "POST":
        return render(request, "payments/refund_request.html", {"order": order, "form": RefundRequestForm(order=order)})

    form = RefundRequestForm(request.POST, order=order)
    if form.is_valid():
        refund = form.save(commit=False)
        refund.order = order
        refund.save()
        return render(request, "payments/refund_submitted.html", {"refund": refund})
    return render(request, "payments/refund_request.html", {"order": order, "form": form})


@login_required
def request_return(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    if order.payment_status != "paid" or order.status != "delivered":
        return JsonResponse({"success": False, "error": "Returns are available only for paid delivered orders."}, status=400)
    if ReturnRequest.objects.filter(order=order, status__in=("requested", "approved")).exists():
        return JsonResponse({"success": False, "error": "An active return request already exists for this order."}, status=400)
    form = ReturnRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        return_request = form.save(commit=False)
        return_request.order = order
        return_request.save()
        return render(request, "payments/return_submitted.html", {"return_request": return_request})
    return render(request, "payments/return_request.html", {"order": order, "form": form})





