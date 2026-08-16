from wishlist.models import Wishlist


class WishlistService:

    @staticmethod
    def toggle(user, product):

        item = Wishlist.objects.filter(
            user=user,
            product=product,
        )

        if item.exists():

            item.delete()

            return False

        Wishlist.objects.create(
            user=user,
            product=product,
        )

        return True