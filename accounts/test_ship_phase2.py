from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.forms import RegisterForm
from accounts.models import Address


User = get_user_model()


class Phase2AccountSecurityTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="phase2-user",
            email="verified@example.com",
            password="StrongPass123!",
            email_verified=True,
            is_active=True,
        )

        self.other = User.objects.create_user(
            username="phase2-other",
            email="other@example.com",
            password="StrongPass123!",
            email_verified=True,
            is_active=True,
        )

    def _address(self, user, **extra):
        data = {
            "user": user,
            "full_name": "Test Customer",
            "phone": "0712345678",
            "county": "Nairobi",
            "city": "Nairobi",
            "estate": "CBD",
            "house_number": "10",
            "landmark": "",
            "is_default": False,
        }

        data.update(extra)

        return Address.objects.create(**data)

    def test_registration_rejects_duplicate_email_case_insensitively(self):

        form = RegisterForm(
            data={
                "username": "new-user",
                "email": "VERIFIED@EXAMPLE.COM",
                "phone": "0711111111",
                "password1": "StrongPass987!",
                "password2": "StrongPass987!",
            }
        )

        self.assertFalse(form.is_valid())

        self.assertIn(
            "email",
            form.errors,
        )

    def test_changing_verified_email_removes_verified_status(self):

        self.client.force_login(self.user)

        response = self.client.post(
            reverse("profile"),
            data={
                "first_name": "Phase",
                "last_name": "Two",
                "email": "new-email@example.com",
                "phone": "0712345678",
                "email_notifications": "on",
                "sms_notifications": "on",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.user.refresh_from_db()

        self.assertEqual(
            self.user.email,
            "new-email@example.com",
        )

        self.assertFalse(
            self.user.email_verified
        )

    def test_profile_rejects_another_users_email(self):

        self.client.force_login(self.user)

        response = self.client.post(
            reverse("profile"),
            data={
                "first_name": "Phase",
                "last_name": "Two",
                "email": "OTHER@EXAMPLE.COM",
                "phone": "0712345678",
                "email_notifications": "on",
                "sms_notifications": "on",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.user.refresh_from_db()

        self.assertEqual(
            self.user.email,
            "verified@example.com",
        )

        self.assertTrue(
            self.user.email_verified
        )

    def test_address_delete_rejects_get(self):

        address = self._address(
            self.user
        )

        self.client.force_login(self.user)

        response = self.client.get(
            reverse(
                "delete_address",
                args=[address.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            405,
        )

        self.assertTrue(
            Address.objects.filter(
                pk=address.pk
            ).exists()
        )

    def test_address_delete_post_works_for_owner(self):

        address = self._address(
            self.user
        )

        self.client.force_login(self.user)

        response = self.client.post(
            reverse(
                "delete_address",
                args=[address.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertFalse(
            Address.objects.filter(
                pk=address.pk
            ).exists()
        )

    def test_user_cannot_delete_another_users_address(self):

        address = self._address(
            self.other
        )

        self.client.force_login(self.user)

        response = self.client.post(
            reverse(
                "delete_address",
                args=[address.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.assertTrue(
            Address.objects.filter(
                pk=address.pk
            ).exists()
        )

    def test_default_address_rejects_get(self):

        address = self._address(
            self.user
        )

        self.client.force_login(self.user)

        response = self.client.get(
            reverse(
                "set_default_address",
                args=[address.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            405,
        )

        address.refresh_from_db()

        self.assertFalse(
            address.is_default
        )

    def test_user_cannot_make_another_users_address_default(self):

        mine = self._address(
            self.user,
            is_default=True,
        )

        theirs = self._address(
            self.other,
            is_default=False,
        )

        self.client.force_login(self.user)

        response = self.client.post(
            reverse(
                "set_default_address",
                args=[theirs.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        mine.refresh_from_db()
        theirs.refresh_from_db()

        self.assertTrue(
            mine.is_default
        )

        self.assertFalse(
            theirs.is_default
        )

    def test_setting_default_address_updates_only_owner(self):

        old_default = self._address(
            self.user,
            is_default=True,
        )

        new_default = self._address(
            self.user,
            is_default=False,
        )

        other_default = self._address(
            self.other,
            is_default=True,
        )

        self.client.force_login(self.user)

        response = self.client.post(
            reverse(
                "set_default_address",
                args=[new_default.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        old_default.refresh_from_db()
        new_default.refresh_from_db()
        other_default.refresh_from_db()

        self.assertFalse(
            old_default.is_default
        )

        self.assertTrue(
            new_default.is_default
        )

        self.assertTrue(
            other_default.is_default
        )
