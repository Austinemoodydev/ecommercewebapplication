import json

from django.contrib.auth.decorators import login_required
from django.db import transaction as db_transaction
from django_ratelimit.decorators import ratelimit
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt

from orders.models import Order
from .models import MpesaTransaction
from .mpesa import MpesaError, stk_push


@login_required
@ratelimit(key="user", rate="5/m", method="POST", block=True)
def initiate_payment(request, order_number):

    order = get_object_or_404(Order, order_number=order_number, user=request.user)

    if order.payment_status == "paid":
        return JsonResponse({"success": False, "error": "This order has already been paid."}, status=400)

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

    transaction = MpesaTransaction.objects.filter(
        checkout_request_id=checkout_request_id
    ).first()

    if not transaction:
        return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})

    if transaction.status in ("success", "failed"):
        return JsonResponse({"ResultCode": 0, "ResultDesc": "Already processed"})

    transaction.result_code = str(result_code)
    transaction.result_description = result_desc

    if result_code == 0:

        transaction.status = "success"

        metadata = stk_callback.get("CallbackMetadata", {}).get("Item", [])

        for item in metadata:
            if item.get("Name") == "MpesaReceiptNumber":
                transaction.mpesa_receipt_number = item.get("Value", "")

        transaction.order.payment_status = "paid"
        transaction.order.status = "confirmed"
        transaction.order.save(update_fields=["payment_status", "status", "updated_at"])

        for order_item in transaction.order.items.select_related("product"):
            product = order_item.product
            product.stock = max(product.stock - order_item.quantity, 0)
            product.save(update_fields=["stock"])

    else:
        transaction.status = "failed"

    transaction.save()

    if result_code == 0:
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





