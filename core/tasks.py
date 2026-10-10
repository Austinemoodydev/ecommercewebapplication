import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from notifications.models import Notification
from notifications.preference_service import email_allowed, sms_allowed
from notifications.tasks import _get_sms_client, _normalise_phone

from .campaigns import campaign_recipients
from .models import CampaignAuditEvent, CampaignDelivery, MarketingCampaign


logger = logging.getLogger(__name__)


def _record(campaign, user, channel, status, error=""):
    CampaignDelivery.objects.update_or_create(
        campaign=campaign,
        user=user,
        channel=channel,
        defaults={
            "status": status,
            "error": error[:2000],
            "sent_at": timezone.now() if status == "sent" else None,
        },
    )


@shared_task
def dispatch_campaign(campaign_id):
    with transaction.atomic():
        campaign = MarketingCampaign.objects.select_for_update().get(pk=campaign_id)
        if not campaign.is_enabled or not campaign.approved_at:
            return {"status": "skipped", "reason": "Campaign is not approved and enabled."}
        if campaign.dispatched_at:
            return {"status": "skipped", "reason": "Campaign was already dispatched."}
        # Claim the campaign before contacting external providers so two workers
        # cannot send the same bulk communication concurrently.
        campaign.dispatched_at = timezone.now()
        campaign.save(update_fields=["dispatched_at", "updated_at"])

    counts = {"in_app": 0, "email": 0, "sms": 0, "skipped": 0, "failed": 0}
    for user in campaign_recipients(campaign).iterator(chunk_size=200):
        if campaign.send_in_app:
            Notification.objects.get_or_create(
                event_key=f"campaign:{campaign.pk}:user:{user.pk}:in_app",
                defaults={
                    "user": user,
                    "channel": "in_app",
                    "category": "marketing",
                    "subject": campaign.headline,
                    "message": campaign.message,
                    "sms_message": "",
                    "status": "sent",
                    "sent_at": timezone.now(),
                },
            )
            _record(campaign, user, "in_app", "sent")
            counts["in_app"] += 1

        if campaign.send_email:
            if user.email and email_allowed(user, "marketing"):
                try:
                    send_mail(
                        campaign.headline,
                        campaign.message,
                        settings.DEFAULT_FROM_EMAIL,
                        [user.email],
                        fail_silently=False,
                    )
                    _record(campaign, user, "email", "sent")
                    counts["email"] += 1
                except Exception as exc:
                    logger.exception("Campaign email delivery failed")
                    _record(campaign, user, "email", "failed", str(exc))
                    counts["failed"] += 1
            else:
                _record(campaign, user, "email", "skipped", "No email or marketing consent.")
                counts["skipped"] += 1

        if campaign.send_sms:
            if user.phone and sms_allowed(user, "marketing"):
                try:
                    _get_sms_client().send(
                        campaign.message[:480],
                        [_normalise_phone(user.phone)],
                    )
                    _record(campaign, user, "sms", "sent")
                    counts["sms"] += 1
                except Exception as exc:
                    logger.exception("Campaign SMS delivery failed")
                    _record(campaign, user, "sms", "failed", str(exc))
                    counts["failed"] += 1
            else:
                _record(campaign, user, "sms", "skipped", "No phone or marketing consent.")
                counts["skipped"] += 1

    CampaignAuditEvent.objects.create(
        campaign=campaign,
        action="bulk_send_completed",
        details=str(counts),
    )
    return counts


@shared_task
def dispatch_due_campaigns():
    now = timezone.now()
    ids = list(
        MarketingCampaign.objects.filter(
            is_enabled=True,
            approved_at__isnull=False,
            dispatched_at__isnull=True,
            starts_at__lte=now,
            ends_at__gt=now,
        )
        .filter(Q(send_in_app=True) | Q(send_email=True) | Q(send_sms=True))
        .values_list("pk", flat=True)
    )
    for campaign_id in ids:
        dispatch_campaign.delay(campaign_id)
    return len(ids)
