from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


User = get_user_model()


class LogoutSecurityTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="logout-test-user",
            email="logout@example.com",
            password="StrongPass123!",
            is_active=True,
        )

    def test_logout_get_is_not_used_for_state_change(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("logout")
        )

        self.assertEqual(
            response.status_code,
            405,
        )

        self.assertIn(
            "_auth_user_id",
            self.client.session,
        )

    def test_logout_post_logs_user_out(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("logout"),
            follow=False,
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
        )

    def test_logout_redirects_home(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("logout"),
            follow=False,
        )

        self.assertEqual(
            response.url,
            reverse("home"),
        )
