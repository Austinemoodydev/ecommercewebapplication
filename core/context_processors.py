from wishlist.models import Wishlist
from cart.models import Cart
from django.conf import settings

from core.store_settings import (
    get_store_settings,
)
from core.campaigns import get_active_campaign


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

            cart_count = sum(
                item.quantity
                for item in cart.items.all()
            )

            cart_total = sum(
                item.subtotal
                for item in cart.items.all()
            )

    elif request.session.session_key:

        cart = Cart.objects.filter(
            session_key=request.session.session_key
        ).first()

        if cart:

            cart_count = sum(
                item.quantity
                for item in cart.items.all()
            )

            cart_total = sum(
                item.subtotal
                for item in cart.items.all()
            )

    store_settings = (
        get_store_settings()
    )
    active_campaign = get_active_campaign()


    return {

        "store_settings":
            store_settings,

        "wishlist_count": wishlist_count,

        "cart_count": cart_count,

        "cart_total": cart_total,
        "google_site_verification": settings.GOOGLE_SITE_VERIFICATION,
        "site_url": settings.SITE_URL,
        "chatbot_enabled": settings.CHATBOT_ENABLED,
        "active_campaign": active_campaign,

    }
