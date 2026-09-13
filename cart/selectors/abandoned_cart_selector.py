from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from cart.models import Cart


class AbandonedCartSelector:

    @staticmethod
    def cutoff():

        hours = getattr(
            settings,
            "CART_ABANDONED_AFTER_HOURS",
            24,
        )


        return (
            timezone.now()
            - timedelta(
                hours=hours
            )
        )


    @classmethod
    def abandoned(
        cls,
        *,
        cutoff=None,
    ):

        if cutoff is None:

            cutoff = cls.cutoff()


        return (
            Cart.objects
            .filter(
                converted_at__isnull=True,
                last_activity_at__lte=cutoff,
                items__isnull=False,
            )
            .select_related(
                "user"
            )
            .distinct()
            .order_by(
                "last_activity_at"
            )
        )
