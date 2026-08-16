from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render

from products.models import Product
from cart.selectors.cart_selector import CartSelector
from cart.services.cart_service import CartService


def cart_view(request):

    cart = CartSelector.get_cart(request)

    return render(
        request,
        "cart/cart.html",
        {
            "cart": cart,
            "items": cart.items.select_related("product").all(),
            "total": cart.total_price,
        }
    )


def _cart_json(cart, item=None):

    data = {
        "success": True,
        "count": cart.total_items,
        "total": str(cart.total_price),
    }

    if item is not None:
        data["item_id"] = item.id
        data["quantity"] = item.quantity
        data["subtotal"] = str(item.subtotal)

    return JsonResponse(data)


def add_to_cart(request, product_id):

    product = get_object_or_404(Product, id=product_id)

    cart = CartService.add(request, product)

    item = cart.items.filter(product=product).first()

    return _cart_json(cart, item)


def increase_quantity(request, item_id):

    cart = CartService.increase(request, item_id)

    item = cart.items.filter(id=item_id).first()

    return _cart_json(cart, item)


def decrease_quantity(request, item_id):

    cart = CartService.decrease(request, item_id)

    item = cart.items.filter(id=item_id).first()

    return _cart_json(cart, item)


def remove_from_cart(request, item_id):

    cart = CartService.remove(request, item_id)

    return _cart_json(cart)


def mini_cart(request):

    cart = CartSelector.get_cart(request)

    items = [
        {
            "id": item.id,
            "name": item.product.name,
            "quantity": item.quantity,
            "subtotal": str(item.subtotal),
        }
        for item in cart.items.select_related("product").all()
    ]

    return JsonResponse({
        "items": items,
        "total": str(cart.total_price),
        "count": cart.total_items,
    })
