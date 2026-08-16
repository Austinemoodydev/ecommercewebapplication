from wishlist.models import Wishlist


class WishlistSelector:

    @staticmethod
    def user_items(user):

        return Wishlist.objects.select_related(
            "product"
        ).filter(
            user=user
        )

    @staticmethod
    def exists(user, product):

        return Wishlist.objects.filter(
            user=user,
            product=product,
        ).exists()