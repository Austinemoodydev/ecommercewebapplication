from unittest.mock import patch

from django.test import TestCase

from accounts.models import CustomUser
from notifications.models import Notification
from notifications.tasks import send_order_status_notification
from orders.models import Order


class NotificationTests(TestCase):
	def test_failed_delivery_is_recorded(self):
		user = CustomUser.objects.create_user(username="notify-user", email="notify@example.com")
		order = Order.objects.create(
			user=user, order_number="ORDER-NOTIFY", full_name="Notify User",
			phone="0712345678", county="Nairobi", city="Nairobi", estate="Estate",
			house_number="1", subtotal=10, total_amount=10, status="shipped",
		)

		with patch("notifications.tasks.send_mail", side_effect=RuntimeError("SMTP unavailable")), \
				patch("notifications.tasks._get_sms_client", side_effect=RuntimeError("SMS unavailable")):
			with self.assertRaises(RuntimeError):
				send_order_status_notification.run(order.id)

		notification = Notification.objects.get(order_id=order.id)
		self.assertEqual(notification.status, "failed")
		self.assertEqual(notification.attempts, 1)
from django.test import TestCase

# Create your tests here.
