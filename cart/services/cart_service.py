from cart.models import Cart, CartItem
from cart.selectors.cart_selector import CartSelector


class CartService:

    @staticmethod
    def add(request, product, variant=None):

        cart = CartSelector.get_cart(request)

        item = cart.items.filter(product=product, variant=variant).first()
        created = item is None
        if created:
            item = CartItem.objects.create(cart=cart, product=product, variant=variant)

        if not created:
            available_stock = variant.available_stock if variant else product.available_stock
            if item.quantity < available_stock:
                item.quantity += 1
                item.save()

        return cart

    @staticmethod
    def increase(request, item_id):

        cart = CartSelector.get_cart(request)

        item = cart.items.filter(id=item_id).first()

        available_stock = item.variant.available_stock if item and item.variant else item.product.available_stock if item else 0
        if item and item.quantity < available_stock:
            item.quantity += 1
            item.save()

        return cart

    @staticmethod
    def decrease(request, item_id):

        cart = CartSelector.get_cart(request)

        item = cart.items.filter(id=item_id).first()

        if item:
            if item.quantity > 1:
                item.quantity -= 1
                item.save()
            else:
                item.delete()

        return cart

    @staticmethod
    def remove(request, item_id):

        cart = CartSelector.get_cart(request)

        cart.items.filter(id=item_id).delete()

        return cart

    @staticmethod
    def merge_session_cart_into_user(request, user):

        session_key = request.session.session_key

        if not session_key:
            return

        session_cart = Cart.objects.filter(
            session_key=session_key,
            user__isnull=True,
        ).first()

        if not session_cart:
            return

        user_cart, _ = Cart.objects.get_or_create(user=user)

        for item in session_cart.items.all():

            existing = user_cart.items.filter(product=item.product, variant=item.variant).first()

            if existing:
                combined_qty = existing.quantity + item.quantity
                available_stock = item.variant.available_stock if item.variant else item.product.available_stock
                existing.quantity = min(combined_qty, available_stock) if available_stock else combined_qty
                existing.save()
            else:
                item.cart = user_cart
                item.save()

        session_cart.delete()
