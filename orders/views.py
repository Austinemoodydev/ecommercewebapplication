from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django_ratelimit.decorators import ratelimit
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import Address
from cart.selectors.cart_selector import CartSelector
from .forms import CheckoutForm
from django.http import JsonResponse

from .models import Coupon, DeliveryArea, Order, OrderItem
from .utils import generate_order_number


@login_required
@ratelimit(key="user", rate="10/m", method="POST", block=True)
def checkout(request):

    cart = CartSelector.get_cart(request)

    items = cart.items.select_related("product")

    if not items.exists():
        return redirect("cart")

    addresses = Address.objects.filter(user=request.user)

    default_address = addresses.filter(is_default=True).first()

    delivery_areas = DeliveryArea.objects.filter(is_active=True)

    form = CheckoutForm(request.POST or None)

    stock_error = None

    if request.method == "POST":

        if form.is_valid():

            for item in items:
                if item.quantity > item.product.stock:
                    stock_error = f"Only {item.product.stock} of {item.product.name} left in stock."
                    break

        if form.is_valid() and not stock_error:

            with transaction.atomic():

                delivery_area = form.cleaned_data["delivery_area"]

                subtotal = cart.total_price
                shipping_cost = delivery_area.fee

                discount = Decimal("0")
                coupon_obj = None

                coupon_code = request.session.get("coupon_code")

                if coupon_code:
                    coupon_obj = Coupon.objects.filter(code=coupon_code).first()
                    if coupon_obj:
                        valid, _reason = coupon_obj.is_valid(subtotal)
                        if valid:
                            discount = coupon_obj.calculate_discount(subtotal)
                        else:
                            coupon_obj = None

                total_amount = subtotal + shipping_cost - discount

                order = Order.objects.create(
                    user=request.user,
                    order_number=generate_order_number(),
                    full_name=form.cleaned_data["full_name"],
                    phone=form.cleaned_data["phone"],
                    email=form.cleaned_data.get("email", ""),
                    county=form.cleaned_data["county"],
                    city=form.cleaned_data["city"],
                    estate=delivery_area.name,
                    house_number=form.cleaned_data["house_number"],
                    landmark=form.cleaned_data.get("landmark", ""),
                    delivery_notes=form.cleaned_data.get("delivery_notes", ""),
                    latitude=form.cleaned_data.get("latitude"),
                    longitude=form.cleaned_data.get("longitude"),
                    subtotal=subtotal,
                    shipping_cost=shipping_cost,
                    discount=discount,
                    coupon=coupon_obj,
                    total_amount=total_amount,
                )

                if coupon_obj:
                    coupon_obj.times_used += 1
                    coupon_obj.save(update_fields=["times_used"])
                    request.session.pop("coupon_code", None)

                for item in items:
                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        product_name=item.product.name,
                        price=item.product.current_price,
                        quantity=item.quantity,
                        subtotal=item.subtotal,
                    )

                cart.items.all().delete()

            return redirect("order_confirmation", order_number=order.order_number)

    return render(
        request,
        "orders/checkout.html",
        {
            "cart": cart,
            "items": items,
            "addresses": addresses,
            "default_address": default_address,
            "delivery_areas": delivery_areas,
            "form": form,
            "stock_error": stock_error,
        },
    )


@login_required
def order_confirmation(request, order_number):

    order = get_object_or_404(Order, order_number=order_number, user=request.user)

    return render(
        request,
        "orders/order_confirmation.html",
        {
            "order": order,
        },
    )





@login_required
@ratelimit(key="user", rate="15/m", method="POST", block=True)
def apply_coupon(request):

    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid request."}, status=400)

    code = request.POST.get("code", "").strip().upper()

    cart = CartSelector.get_cart(request)

    subtotal = cart.total_price

    coupon = Coupon.objects.filter(code__iexact=code).first()

    if not coupon:
        return JsonResponse({"success": False, "error": "Invalid coupon code."}, status=400)

    valid, reason = coupon.is_valid(subtotal)

    if not valid:
        return JsonResponse({"success": False, "error": reason}, status=400)

    discount = coupon.calculate_discount(subtotal)

    request.session["coupon_code"] = coupon.code

    return JsonResponse({
        "success": True,
        "discount": str(discount),
        "new_total": str(subtotal - discount + Decimal("0")),
        "code": coupon.code,
    })


@login_required
def remove_coupon(request):

    request.session.pop("coupon_code", None)

    return JsonResponse({"success": True})




