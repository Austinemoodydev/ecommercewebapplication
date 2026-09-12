from notifications.models import (
    NotificationPreference,
)


TRANSACTIONAL_CATEGORIES = {
    "general",
    "orders",
    "payments",
    "delivery",
    "returns",
}


def get_notification_preferences(
    user,
):

    """
    Lazily migrate the legacy CustomUser notification
    switches into the richer preference model.
    """

    preferences, _ = (
        NotificationPreference.objects
        .get_or_create(
            user=user,
            defaults={
                "email_enabled":
                    getattr(
                        user,
                        "email_notifications",
                        True,
                    ),

                "sms_enabled":
                    getattr(
                        user,
                        "sms_notifications",
                        True,
                    ),
            },
        )
    )


    return preferences


def category_enabled(
    preferences,
    category,
):

    if category == "orders":
        return preferences.order_updates

    if category == "payments":
        return preferences.payment_updates

    if category == "delivery":
        return preferences.delivery_updates

    if category == "returns":
        return preferences.return_refund_updates

    if category == "marketing":
        return True

    return True


def email_allowed(
    user,
    category,
):

    preferences = (
        get_notification_preferences(
            user
        )
    )


    if category == "marketing":

        return (
            preferences.email_enabled
            and
            preferences.marketing_email
        )


    return (
        preferences.email_enabled
        and
        category_enabled(
            preferences,
            category,
        )
    )


def sms_allowed(
    user,
    category,
):

    preferences = (
        get_notification_preferences(
            user
        )
    )


    if category == "marketing":

        return (
            preferences.sms_enabled
            and
            preferences.marketing_sms
        )


    return (
        preferences.sms_enabled
        and
        category_enabled(
            preferences,
            category,
        )
    )
