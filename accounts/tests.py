from django.core import mail
from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from .models import CustomUser


class PasswordResetTests(TestCase):
	def test_user_can_reset_password_from_email_link(self):
		user = CustomUser.objects.create_user(
			username="buyer",
			email="buyer@example.com",
			password="old-password-123",
		)

		response = self.client.post(
			reverse("password_reset"),
			{"email": user.email},
		)

		self.assertRedirects(response, reverse("password_reset_done"))
		self.assertEqual(len(mail.outbox), 1)
		reset_url = next(
			line for line in mail.outbox[0].body.splitlines()
			if "/accounts/password-reset/" in line
		)

		response = self.client.get(reset_url.replace("http://example.com", ""))
		self.assertRedirects(response, response.url)
		confirm_url = response.url

		response = self.client.post(
			confirm_url,
			{"new_password1": "new-password-123", "new_password2": "new-password-123"},
		)

		self.assertRedirects(response, reverse("password_reset_complete"))
		user.refresh_from_db()
		self.assertTrue(user.check_password("new-password-123"))


class EmailVerificationTests(TestCase):
	def test_registration_requires_verification_before_login(self):
		response = self.client.post(reverse("register"), {
			"username": "newbuyer",
			"email": "newbuyer@example.com",
			"phone": "0712345678",
			"password1": "new-password-123",
			"password2": "new-password-123",
		})

		self.assertRedirects(response, reverse("login"))
		user = CustomUser.objects.get(username="newbuyer")
		self.assertFalse(user.is_active)
		self.assertFalse(user.email_verified)
		self.assertEqual(len(mail.outbox), 1)
		verification_url = next(
			line for line in mail.outbox[0].body.splitlines()
			if "/accounts/verify-email/" in line
		)

		response = self.client.get(verification_url.replace("http://testserver", ""))

		self.assertEqual(response.status_code, 200)
		user.refresh_from_db()
		self.assertTrue(user.is_active)
		self.assertTrue(user.email_verified)


class ProfileTests(TestCase):
	def test_customer_can_update_profile_preferences(self):
		user = CustomUser.objects.create_user(username="profile-user", password="test-password")
		self.client.force_login(user)
		response = self.client.post(reverse("profile"), {
			"first_name": "Updated",
			"last_name": "Customer",
			"email": "updated@example.com",
			"phone": "0712345678",
			"email_notifications": "on",
		})
		self.assertRedirects(response, reverse("profile"))
		user.refresh_from_db()
		self.assertEqual(user.first_name, "Updated")
		self.assertTrue(user.email_notifications)
		self.assertFalse(user.sms_notifications)


class LoginRedirectTests(TestCase):
	def test_successful_login_redirects_to_storefront(self):
		user = CustomUser.objects.create_user(username="login-user", password="test-password")

		response = self.client.post(reverse("login"), {
			"username": user.username,
			"password": "test-password",
		})

		self.assertEqual(settings.LOGIN_REDIRECT_URL, "/shop/")
		self.assertRedirects(response, reverse("shop"))
