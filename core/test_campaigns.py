from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from notifications.models import Notification, NotificationPreference
from accounts.staff_mfa import VERIFIED_USER_KEY
from accounts.store_roles import STORE_OWNER

from .campaigns import get_active_campaign
from .models import CampaignDelivery, MarketingCampaign
from .tasks import dispatch_campaign


User = get_user_model()


def campaign_data(**overrides):
    now = timezone.now()
    data = {
        "name": "Jamhuri Celebration",
        "holiday_type": "public_holiday",
        "headline": "Happy Jamhuri Day",
        "message": "Celebrate with us throughout the holiday.",
        "starts_at": now - timedelta(hours=1),
        "ends_at": now + timedelta(days=1),
        "is_enabled": True,
        "show_on_website": True,
    }
    data.update(overrides)
    return data


class CampaignVisibilityTests(TestCase):
    def test_only_approved_campaign_is_public(self):
        draft = MarketingCampaign.objects.create(**campaign_data())
        self.assertIsNone(get_active_campaign())

        draft.approved_at = timezone.now()
        draft.save(update_fields=["approved_at", "updated_at"])

        self.assertEqual(get_active_campaign(), draft)
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Happy Jamhuri Day")

    def test_verified_holiday_requires_official_source(self):
        campaign = MarketingCampaign(
            **campaign_data(is_verified_holiday=True, official_source_url="")
        )
        with self.assertRaises(ValidationError):
            campaign.full_clean()

    def test_priority_selects_one_sitewide_campaign(self):
        now = timezone.now()
        low = MarketingCampaign.objects.create(
            **campaign_data(name="Low priority", priority=5, approved_at=now)
        )
        high = MarketingCampaign.objects.create(
            **campaign_data(name="High priority", priority=50, approved_at=now)
        )
        self.assertEqual(get_active_campaign(), high)
        self.assertNotEqual(get_active_campaign(), low)


@override_settings(DEFAULT_FROM_EMAIL="store@example.com")
class CampaignDeliveryTests(TestCase):
    def setUp(self):
        self.opted_in = User.objects.create_user(
            username="marketing-in",
            email="in@example.com",
            phone="0712000001",
            password="StrongPass123!",
        )
        self.opted_out = User.objects.create_user(
            username="marketing-out",
            email="out@example.com",
            phone="0712000002",
            password="StrongPass123!",
        )
        NotificationPreference.objects.create(
            user=self.opted_in,
            marketing_email=True,
            marketing_sms=False,
        )
        NotificationPreference.objects.create(
            user=self.opted_out,
            marketing_email=False,
            marketing_sms=False,
        )
        self.campaign = MarketingCampaign.objects.create(
            **campaign_data(
                approved_at=timezone.now(),
                send_in_app=True,
                send_email=True,
            )
        )

    @patch("core.tasks.send_mail")
    def test_bulk_delivery_respects_marketing_consent_and_is_idempotent(self, send_mail):
        result = dispatch_campaign(self.campaign.pk)

        self.assertEqual(result["email"], 1)
        send_mail.assert_called_once()
        self.assertEqual(
            Notification.objects.filter(
                event_key__startswith=f"campaign:{self.campaign.pk}:"
            ).count(),
            2,
        )
        self.assertEqual(
            CampaignDelivery.objects.get(
                campaign=self.campaign,
                user=self.opted_out,
                channel="email",
            ).status,
            "skipped",
        )

        second = dispatch_campaign(self.campaign.pk)
        self.assertEqual(second["status"], "skipped")
        send_mail.assert_called_once()

    def test_fixed_holiday_generator_creates_unapproved_drafts(self):
        call_command("seed_kenya_holiday_campaigns", year=2030, years=1)
        christmas = MarketingCampaign.objects.get(name="Christmas Day 2030")
        self.assertTrue(christmas.is_verified_holiday)
        self.assertIsNone(christmas.approved_at)


@override_settings(MFA_STAFF_ENFORCEMENT=True)
class CampaignManagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("setup_store_roles")
        cls.owner = User.objects.create_user(
            username="campaign-owner",
            password="StrongPass123!",
            is_staff=True,
        )
        cls.owner.groups.add(Group.objects.get(name=STORE_OWNER))

    def setUp(self):
        self.client.force_login(self.owner)
        session = self.client.session
        session[VERIFIED_USER_KEY] = str(self.owner.pk)
        session.save()

    def test_owner_can_review_and_approve_campaign(self):
        campaign = MarketingCampaign.objects.create(**campaign_data())
        self.assertEqual(self.client.get(reverse("campaign_list")).status_code, 200)
        self.assertEqual(
            self.client.get(reverse("campaign_detail", args=[campaign.pk])).status_code,
            200,
        )

        response = self.client.post(reverse("campaign_approve", args=[campaign.pk]))

        self.assertRedirects(response, reverse("campaign_detail", args=[campaign.pk]))
        campaign.refresh_from_db()
        self.assertEqual(campaign.approved_by, self.owner)
        self.assertEqual(campaign.audit_events.get().action, "approved")
