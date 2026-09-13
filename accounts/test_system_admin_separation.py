from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from accounts.store_roles import (
    STORE_OWNER,
)


User = get_user_model()


class SystemAdminSeparationTests(TestCase):

    @classmethod
    def setUpTestData(cls):

        call_command(
            "setup_store_roles"
        )

        cls.store_owner = (
            User.objects.create_user(
                username="store-owner-separation",
                email="store-owner-separation@example.com",
                password="StrongPass123!",
                is_active=True,
                is_staff=True,
                role="admin",
            )
        )

        cls.store_owner.groups.add(
            Group.objects.get(
                name=STORE_OWNER
            )
        )


        cls.regular_staff = (
            User.objects.create_user(
                username="regular-staff-separation",
                email="regular-staff-separation@example.com",
                password="StrongPass123!",
                is_active=True,
                is_staff=True,
                role="admin",
            )
        )


        cls.superuser = (
            User.objects.create_superuser(
                username="system-admin-separation",
                email="system-admin-separation@example.com",
                password="StrongPass123!",
            )
        )


    # ========================================================
    # DJANGO ADMIN
    # ========================================================

    def test_anonymous_can_open_system_admin_login(self):

        response = self.client.get(
            reverse(
                "admin:login"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )


    def test_store_owner_cannot_open_django_admin(self):

        self.client.force_login(
            self.store_owner
        )

        response = self.client.get(
            reverse(
                "admin:index"
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertTrue(
            response.url.startswith(
                reverse(
                    "admin:login"
                )
            )
        )


    def test_plain_is_staff_cannot_open_django_admin(self):

        self.client.force_login(
            self.regular_staff
        )

        response = self.client.get(
            reverse(
                "admin:index"
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertTrue(
            response.url.startswith(
                reverse(
                    "admin:login"
                )
            )
        )


    def test_store_owner_credentials_rejected_by_admin_login(
        self
    ):

        response = self.client.post(
            reverse(
                "admin:login"
            ),
            {
                "username":
                    self.store_owner.username,

                "password":
                    "StrongPass123!",

                "next":
                    reverse(
                        "admin:index"
                    ),
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
        )

        self.assertContains(
            response,
            "System administrator access only",
        )


    def test_superuser_can_open_django_admin(self):

        self.client.force_login(
            self.superuser
        )

        response = self.client.get(
            reverse(
                "admin:index"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )


    # ========================================================
    # STORE STAFF LOGIN
    # ========================================================

    def test_store_owner_can_use_staff_login(self):

        response = self.client.post(
            reverse(
                "staff_login"
            ),
            {
                "username":
                    self.store_owner.username,

                "password":
                    "StrongPass123!",
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "admin_dashboard"
            ),
            fetch_redirect_response=False,
        )


    def test_superuser_cannot_use_staff_login(self):

        response = self.client.post(
            reverse(
                "staff_login"
            ),
            {
                "username":
                    self.superuser.username,

                "password":
                    "StrongPass123!",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
        )

        self.assertContains(
            response,
            "System administrators must use",
        )


    # ========================================================
    # UI
    # ========================================================

    def test_store_owner_does_not_see_django_admin_link(self):

        self.client.force_login(
            self.store_owner
        )

        response = self.client.get(
            reverse(
                "admin_dashboard"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertNotContains(
            response,
            "Django Admin",
        )


    def test_superuser_sees_django_admin_link_on_store_dashboard(
        self
    ):

        self.client.force_login(
            self.superuser
        )

        response = self.client.get(
            reverse(
                "admin_dashboard"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Django Admin",
        )


    # ========================================================
    # THREE LOGIN ENTRANCES
    # ========================================================

    def test_customer_staff_and_system_admin_urls_are_distinct(
        self
    ):

        self.assertEqual(
            reverse(
                "login"
            ),
            "/accounts/login/",
        )

        self.assertEqual(
            reverse(
                "staff_login"
            ),
            "/staff/login/",
        )

        self.assertEqual(
            reverse(
                "admin:login"
            ),
            "/admin/login/",
        )
