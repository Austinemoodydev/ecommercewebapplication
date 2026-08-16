from wishlist.models import Wishlist
from cart.models import Cart


def global_context(request):

    wishlist_count = 0
    cart_count = 0
    cart_total = 0

    if request.user.is_authenticated:

        wishlist_count = Wishlist.objects.filter(
            user=request.user
        ).count()

        cart = Cart.objects.filter(
            user=request.user
        ).first()

        if cart:

            cart_count = cart.items.count()

            cart_total = sum(
                item.subtotal
                for item in cart.items.all()
            )

    return {

        "wishlist_count": wishlist_count,

        "cart_count": cart_count,

        "cart_total": cart_total,

    }