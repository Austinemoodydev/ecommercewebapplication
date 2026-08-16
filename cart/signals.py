from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from cart.services.cart_service import CartService


@receiver(user_logged_in)
def merge_cart_on_login(sender, request, user, **kwargs):
    CartService.merge_session_cart_into_user(request, user)
