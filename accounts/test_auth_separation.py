from accounts.store_roles import STORE_OWNER
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse


User = get_user_model()


class AuthenticationSeparationTests(TestCase):

    def setUp(self):

        self.customer = User.objects.create_user(
            username="customer-auth-test",
            email="customer-auth@example.com",
            password="StrongPass123!",
            is_active=True,
            is_staff=False,
        )

        self.staff = User.objects.create_user(
            username="staff-auth-test",
            email="staff-auth@example.com",
            password="StrongPass123!",
            is_active=True,
            is_staff=True,
            role="admin",
        )

        store_owner_group, _ = Group.objects.get_or_create(
            name=STORE_OWNER,
        )

        self.staff.groups.add(
            store_owner_group
        )

        store_manager_group, _ = (
            Group.objects.get_or_create(
                name="Store Manager"
            )
        )

        self.staff.groups.add(
            store_manager_group
        )

        self.superuser = (
            User.objects.create_superuser(
                username="system-auth-test",
                email="system-auth@example.com",
                password="StrongPass123!",
            )
        )


    def test_customer_login_lands_on_shop(self):

        response = self.client.post(
            reverse("login"),
            {
                "username":
                    self.customer.username,
                "password":
                    "StrongPass123!",
            },
        )

        self.assertRedirects(
            response,
            reverse("shop"),
            fetch_redirect_response=False,
        )


    def test_staff_cannot_use_customer_login(self):

        response = self.client.post(
            reverse("login"),
            {
                "username":
                    self.staff.username,
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


    def test_staff_login_accepts_staff(self):

        response = self.client.post(
            reverse("staff_login"),
            {
                "username":
                    self.staff.username,
                "password":
                    "StrongPass123!",
            },
        )

        self.assertRedirects(
            response,
            reverse("admin_dashboard"),
            fetch_redirect_response=False,
        )


    def test_customer_cannot_use_staff_login(self):

        response = self.client.post(
            reverse("staff_login"),
            {
                "username":
                    self.customer.username,
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


    def test_store_dashboard_uses_staff_login(self):

        response = self.client.get(
            reverse("admin_dashboard")
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertTrue(
            response.url.startswith(
                reverse("staff_login")
            )
        )


    def test_customer_cannot_open_store_dashboard(self):

        self.client.force_login(
            self.customer
        )

        response = self.client.get(
            reverse("admin_dashboard")
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertTrue(
            response.url.startswith(
                reverse("staff_login")
            )
        )


    def test_customer_login_redirect_setting(self):

        self.assertEqual(
            settings.LOGIN_REDIRECT_URL,
            "/shop/",
        )

        self.assertEqual(
            settings.ACCOUNT_SIGNUP_REDIRECT_URL,
            "/shop/",
        )


    def test_customer_only_social_adapter(self):

        self.assertEqual(
            settings.SOCIALACCOUNT_ADAPTER,
            (
                "accounts.adapters."
                "CustomerOnlySocialAccountAdapter"
            ),
        )
