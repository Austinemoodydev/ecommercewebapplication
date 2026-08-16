from cart.models import Cart


class CartSelector:

    @staticmethod
    def get_cart(request):

        if request.user.is_authenticated:
            cart, _ = Cart.objects.get_or_create(user=request.user)
            return cart

        if not request.session.session_key:
            request.session.create()

        cart, _ = Cart.objects.get_or_create(
            session_key=request.session.session_key
        )
        return cart
