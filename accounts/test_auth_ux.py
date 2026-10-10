from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


User = get_user_model()


class AuthenticationUXTests(TestCase):

    def test_customer_login_has_registration(self):

        response = self.client.get(
            reverse("login")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Create an account",
        )

        self.assertContains(
            response,
            "Continue with Google",
        )

        self.assertContains(response, "Everything you need, in one secure place.")
        self.assertContains(response, 'method="post"')
        self.assertContains(response, reverse("google_login"))

        self.assertNotContains(
            response,
            "Store Staff Login",
        )


    def test_register_page_exists(self):

        response = self.client.get(
            reverse("register")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Create your account",
        )

        self.assertContains(
            response,
            "Terms &amp; Conditions",
        )


    def test_staff_login_has_no_public_registration(self):

        response = self.client.get(
            reverse("staff_login")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Store Portal",
        )

        self.assertContains(
            response,
            "Public staff registration is disabled",
        )

        self.assertNotContains(
            response,
            "Create an account",
        )

    def test_google_login_starts_with_post_and_targets_homepage(self):
        response = self.client.post(
            reverse("google_login"),
            {"next": reverse("home")},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("https://accounts.google.com/"))
        self.assertIn("redirect_uri=", response.url)


    def test_customer_cannot_use_staff_login(self):

        customer = User.objects.create_user(
            username="auth-ux-customer",
            email="auth-ux@example.com",
            password="StrongPass123!",
            is_active=True,
            is_staff=False,
        )

        response = self.client.post(
            reverse("staff_login"),
            {
                "username": customer.username,
                "password": "StrongPass123!",
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
