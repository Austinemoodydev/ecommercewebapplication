from django.utils import timezone


class CartActivityService:

    @staticmethod
    def mark_activity(
        cart,
        *,
        reset_checkout=True,
        reset_conversion=False,
    ):

        now = timezone.now()

        fields = [
            "last_activity_at",
            "updated_at",
        ]

        cart.last_activity_at = now


        if reset_checkout:

            cart.checkout_started_at = None

            fields.append(
                "checkout_started_at"
            )


        if reset_conversion:

            cart.converted_at = None

            fields.append(
                "converted_at"
            )


        cart.save(
            update_fields=fields
        )


        return cart


    @staticmethod
    def mark_checkout_started(
        cart,
    ):

        now = timezone.now()

        cart.last_activity_at = now

        cart.checkout_started_at = now


        cart.save(
            update_fields=[
                "last_activity_at",
                "checkout_started_at",
                "updated_at",
            ]
        )


        return cart


    @staticmethod
    def mark_converted(
        cart,
    ):

        now = timezone.now()

        cart.last_activity_at = now

        cart.converted_at = now


        cart.save(
            update_fields=[
                "last_activity_at",
                "converted_at",
                "updated_at",
            ]
        )


        return cart
