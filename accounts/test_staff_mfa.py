from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from allauth.mfa.models import Authenticator
from allauth.mfa.totp.internal.auth import (
    format_hotp_value,
    hotp_value,
    yield_hotp_counters_from_time,
)

from .staff_mfa import SETUP_SECRET_KEY, VERIFIED_USER_KEY
from .store_roles import STORE_OWNER


User = get_user_model()


def current_code(secret):
    counter = next(yield_hotp_counters_from_time())
    return format_hotp_value(hotp_value(secret, counter))


@override_settings(
    MFA_STAFF_ENFORCEMENT=True,
    MFA_ENCRYPTION_KEY="unit-test-only-mfa-key",
)
class StaffMFAFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("setup_store_roles")
        cls.staff = User.objects.create_user(
            username="mfa-owner",
            email="mfa-owner@example.com",
            password="StrongPass123!",
            is_staff=True,
            is_active=True,
        )
        cls.staff.groups.add(Group.objects.get(name=STORE_OWNER))

    def test_password_step_does_not_authenticate_before_mfa(self):
        response = self.client.post(reverse("staff_login"), {
            "username": self.staff.username,
            "password": "StrongPass123!",
        })
        self.assertRedirects(response, reverse("staff_mfa_setup"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def _enroll(self):
        self.client.post(reverse("staff_login"), {
            "username": self.staff.username,
            "password": "StrongPass123!",
        })
        response = self.client.get(reverse("staff_mfa_setup"))
        self.assertContains(response, "Scan this QR code")
        secret = self.client.session[SETUP_SECRET_KEY]
        response = self.client.post(
            reverse("staff_mfa_setup"), {"code": current_code(secret)}
        )
        self.assertRedirects(response, reverse("staff_mfa_recovery_codes"))
        return secret

    def test_enrollment_encrypts_secret_and_grants_management_access(self):
        self._enroll()
        authenticator = Authenticator.objects.get(
            user=self.staff, type=Authenticator.Type.TOTP
        )
        self.assertNotIn(SETUP_SECRET_KEY, self.client.session)
        self.assertTrue(authenticator.data["secret"].startswith("gAAAA"))
        self.assertEqual(self.client.session[VERIFIED_USER_KEY], str(self.staff.pk))
        self.assertEqual(self.client.get(reverse("admin_dashboard")).status_code, 200)

    def test_returning_staff_must_supply_valid_totp(self):
        secret = self._enroll()
        self.client.logout()
        response = self.client.post(reverse("staff_login"), {
            "username": self.staff.username,
            "password": "StrongPass123!",
        })
        self.assertRedirects(response, reverse("staff_mfa_challenge"))
        self.assertNotIn("_auth_user_id", self.client.session)

        response = self.client.post(
            reverse("staff_mfa_challenge"), {"code": current_code(secret)}
        )
        self.assertRedirects(response, reverse("admin_dashboard"))
        self.assertEqual(self.client.session[VERIFIED_USER_KEY], str(self.staff.pk))

    def test_force_authenticated_session_without_mfa_marker_is_rejected(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("admin_dashboard"))
        self.assertRedirects(response, reverse("staff_login"))

