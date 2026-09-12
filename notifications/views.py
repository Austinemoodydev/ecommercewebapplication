from django.contrib import messages

from django.contrib.admin.views.decorators import (
    staff_member_required,
)

from django.contrib.auth.decorators import (
    login_required,
)

from django.core.paginator import Paginator

from django.db.models import Q

from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from django.utils import timezone

from django.views.decorators.http import (
    require_POST,
)

from notifications.models import (
    Notification,
)

from notifications.tasks import (
    retry_notification,
)


# ============================================================
# CUSTOMER
# ============================================================

@login_required
def customer_notifications(
    request,
):

    queryset = (
        Notification.objects
        .filter(
            user=request.user
        )
        .order_by(
            "-created_at"
        )
    )


    filter_value = (
        request.GET.get(
            "filter",
            "all",
        )
        .strip()
        .lower()
    )


    if filter_value == "unread":

        queryset = queryset.filter(
            read_at__isnull=True
        )

    elif filter_value == "read":

        queryset = queryset.filter(
            read_at__isnull=False
        )

    elif filter_value == "failed":

        queryset = queryset.filter(
            status="failed"
        )


    paginator = Paginator(
        queryset,
        20,
    )

    page_obj = paginator.get_page(
        request.GET.get(
            "page"
        )
    )


    return render(
        request,
        "notifications/customer_list.html",
        {
            "page_obj":
                page_obj,

            "filter_value":
                filter_value,

            "unread_count":
                Notification.objects
                .filter(
                    user=request.user,
                    read_at__isnull=True,
                )
                .count(),
        },
    )


@login_required
@require_POST
def customer_notification_mark_read(
    request,
    notification_id,
):

    notification = get_object_or_404(
        Notification,
        pk=notification_id,
        user=request.user,
    )


    if notification.read_at is None:

        notification.read_at = (
            timezone.now()
        )

        notification.save(
            update_fields=[
                "read_at",
                "updated_at",
            ]
        )


    return redirect(
        request.POST.get(
            "next"
        )
        or "customer_notifications"
    )


@login_required
@require_POST
def customer_notifications_mark_all_read(
    request,
):

    (
        Notification.objects
        .filter(
            user=request.user,
            read_at__isnull=True,
        )
        .update(
            read_at=timezone.now()
        )
    )


    messages.success(
        request,
        "All notifications marked as read.",
    )


    return redirect(
        "customer_notifications"
    )


# ============================================================
# ADMIN
# ============================================================

@staff_member_required
def admin_notifications(
    request,
):

    queryset = (
        Notification.objects
        .select_related(
            "user"
        )
        .order_by(
            "-created_at"
        )
    )


    status = (
        request.GET.get(
            "status",
            ""
        )
        .strip()
        .lower()
    )


    channel = (
        request.GET.get(
            "channel",
            ""
        )
        .strip()
    )


    search = (
        request.GET.get(
            "q",
            ""
        )
        .strip()
    )


    if status in {
        "pending",
        "sent",
        "failed",
        "partial",
    }:

        queryset = queryset.filter(
            status=status
        )


    if channel:

        queryset = queryset.filter(
            channel=channel
        )


    if search:

        queryset = queryset.filter(

            Q(
                subject__icontains=search
            )

            |

            Q(
                message__icontains=search
            )

            |

            Q(
                user__username__icontains=search
            )

            |

            Q(
                user__email__icontains=search
            )
        )


    paginator = Paginator(
        queryset,
        30,
    )


    page_obj = paginator.get_page(
        request.GET.get(
            "page"
        )
    )


    stats = {

        "total":
            Notification.objects.count(),

        "pending":
            Notification.objects.filter(
                status="pending"
            ).count(),

        "sent":
            Notification.objects.filter(
                status="sent"
            ).count(),

        "failed":
            Notification.objects.filter(
                status="failed"
            ).count(),

        "partial":
            Notification.objects.filter(
                status="partial"
            ).count(),
    }


    return render(
        request,
        "notifications/admin_list.html",
        {
            "page_obj":
                page_obj,

            "stats":
                stats,

            "selected_status":
                status,

            "selected_channel":
                channel,

            "search":
                search,
        },
    )


@staff_member_required
@require_POST
def admin_retry_notification(
    request,
    notification_id,
):

    notification = get_object_or_404(
        Notification,
        pk=notification_id,
        status__in=[
            "failed",
            "partial",
        ],
    )


    if not notification.order_id:

        messages.error(
            request,
            "This notification has no linked "
            "order and cannot be retried automatically.",
        )

        return redirect(
            "admin_notifications"
        )


    retry_notification.delay(
        notification.pk
    )


    messages.success(
        request,
        "Notification retry queued.",
    )


    return redirect(
        "admin_notifications"
    )



# ============================================================
# CUSTOMER NOTIFICATION PREFERENCES
# ============================================================

@login_required
def notification_preferences(
    request,
):

    from notifications.preference_service import (
        get_notification_preferences,
    )


    preferences = (
        get_notification_preferences(
            request.user
        )
    )


    if request.method == "POST":

        preferences.email_enabled = (
            request.POST.get(
                "email_enabled"
            )
            == "on"
        )

        preferences.sms_enabled = (
            request.POST.get(
                "sms_enabled"
            )
            == "on"
        )

        preferences.order_updates = (
            request.POST.get(
                "order_updates"
            )
            == "on"
        )

        preferences.payment_updates = (
            request.POST.get(
                "payment_updates"
            )
            == "on"
        )

        preferences.delivery_updates = (
            request.POST.get(
                "delivery_updates"
            )
            == "on"
        )

        preferences.return_refund_updates = (
            request.POST.get(
                "return_refund_updates"
            )
            == "on"
        )

        preferences.marketing_email = (
            request.POST.get(
                "marketing_email"
            )
            == "on"
        )

        preferences.marketing_sms = (
            request.POST.get(
                "marketing_sms"
            )
            == "on"
        )


        preferences.save()


        # Keep old fields in sync so older project code
        # remains compatible during migration.
        request.user.email_notifications = (
            preferences.email_enabled
        )

        request.user.sms_notifications = (
            preferences.sms_enabled
        )

        request.user.save(
            update_fields=[
                "email_notifications",
                "sms_notifications",
            ]
        )


        messages.success(
            request,
            "Notification preferences updated.",
        )


        return redirect(
            "notification_preferences"
        )


    return render(
        request,
        "notifications/preferences.html",
        {
            "preferences":
                preferences,
        },
    )
