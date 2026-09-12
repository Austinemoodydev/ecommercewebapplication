def notification_counts(
    request,
):

    if not request.user.is_authenticated:

        return {
            "notification_unread_count": 0,
        }


    from notifications.models import (
        Notification,
    )


    return {

        "notification_unread_count":
            Notification.objects
            .filter(
                user=request.user,
                read_at__isnull=True,
            )
            .count(),
    }
