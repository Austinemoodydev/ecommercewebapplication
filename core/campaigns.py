from django.db.models import Q
from django.utils import timezone

from .models import MarketingCampaign


def get_active_campaign():
    now = timezone.now()
    return (
        MarketingCampaign.objects.filter(
            is_enabled=True,
            approved_at__isnull=False,
            starts_at__lte=now,
            ends_at__gt=now,
        )
        .select_related("coupon")
        .prefetch_related("products", "categories")
        .order_by("-priority", "-starts_at")
        .first()
    )


def campaign_recipients(campaign):
    from django.contrib.auth import get_user_model

    users = get_user_model().objects.filter(is_active=True, is_staff=False)
    if campaign.audience == "previous_buyers":
        users = users.filter(orders__payment_status__in=["paid", "partially_refunded"])
    return users.distinct().order_by("pk")
