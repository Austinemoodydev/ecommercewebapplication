import json
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.staff_mfa import VERIFIED_USER_KEY
from accounts.store_roles import STORE_OWNER
from categories.models import Category
from orders.models import Order, OrderItem
from products.models import Product


User = get_user_model()


def fake_client(answer="Safe answer"):
    client = MagicMock()
    client.moderations.create.return_value = SimpleNamespace(
        results=[SimpleNamespace(flagged=False)]
    )
    client.responses.create.return_value = SimpleNamespace(output_text=answer)
    return client


class CustomerChatbotTests(TestCase):
    def post(self, message):
        return self.client.post(
            reverse("customer_chat"),
            data=json.dumps({"message": message}),
            content_type="application/json",
        )

    @override_settings(CHATBOT_ENABLED=False, OPENAI_API_KEY="")
    def test_unconfigured_assistant_fails_safely(self):
        response = self.post("Find a laptop")
        self.assertEqual(response.status_code, 503)
        self.assertNotContains(response, "OPENAI_API_KEY", status_code=503)

    @override_settings(CHATBOT_ENABLED=True)
    def test_storefront_chatbot_has_review_first_voice_input(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, 'class="ai-chat__mic"')
        self.assertContains(response, 'class="ai-chat__speak"')
        self.assertContains(response, 'data-voice-endpoint="/assistant/transcribe/"')
        self.assertContains(response, "Speak your question")
        self.assertContains(response, 'maxlength="600"')

    @override_settings(
        CHATBOT_ENABLED=True,
        OPENAI_API_KEY="test",
        OPENAI_TRANSCRIBE_MODEL="gpt-transcribe",
    )
    @patch("core.chatbot.OpenAI")
    def test_voice_recording_is_transcribed_server_side(self, openai):
        client = MagicMock()
        client.audio.transcriptions.create.return_value = SimpleNamespace(
            text="Show me affordable laptops"
        )
        openai.return_value = client
        response = self.client.post(
            reverse("customer_transcribe"),
            {"audio": SimpleUploadedFile("voice.webm", b"mock-audio", content_type="audio/webm")},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["transcript"], "Show me affordable laptops")
        self.assertEqual(client.audio.transcriptions.create.call_args.kwargs["model"], "gpt-transcribe")

    @override_settings(CHATBOT_ENABLED=True, OPENAI_API_KEY="test")
    def test_voice_rejects_unsupported_uploads(self):
        response = self.client.post(
            reverse("customer_transcribe"),
            {"audio": SimpleUploadedFile("voice.exe", b"unsafe", content_type="application/octet-stream")},
        )
        self.assertEqual(response.status_code, 400)

    @override_settings(CHATBOT_ENABLED=True, OPENAI_API_KEY="test", OPENAI_CHAT_MODEL="test-model")
    @patch("core.chatbot.OpenAI")
    def test_response_is_stateless_bounded_and_has_no_tools(self, openai):
        client = fake_client("Here is a suitable product.")
        openai.return_value = client
        response = self.post("Find a laptop")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["reply"], "Here is a suitable product.")
        kwargs = client.responses.create.call_args.kwargs
        self.assertFalse(kwargs["store"])
        self.assertLessEqual(kwargs["max_output_tokens"], 300)
        self.assertNotIn("tools", kwargs)

    @override_settings(CHATBOT_ENABLED=True, OPENAI_API_KEY="test")
    def test_rejects_oversized_input_before_api_call(self):
        response = self.post("x" * 601)
        self.assertEqual(response.status_code, 400)


@override_settings(
    CHATBOT_ENABLED=True,
    OPENAI_API_KEY="test",
    OPENAI_CHAT_MODEL="test-model",
    MFA_STAFF_ENFORCEMENT=True,
)
class StaffChatbotTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("setup_store_roles")
        cls.owner = User.objects.create_user(
            username="chat-owner", password="StrongPass123!", is_staff=True
        )
        cls.owner.groups.add(Group.objects.get(name=STORE_OWNER))
        cls.customer = User.objects.create_user(
            username="chat-customer", password="StrongPass123!"
        )

    def test_customer_cannot_access_staff_assistant(self):
        self.client.force_login(self.customer)
        response = self.client.post(
            reverse("staff_chat"),
            data=json.dumps({"message": "Show sales"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 302)

    @patch("core.chatbot.OpenAI")
    def test_staff_requires_mfa_session_and_then_gets_read_only_answer(self, openai):
        self.client.force_login(self.owner)
        denied = self.client.post(
            reverse("staff_chat"),
            data=json.dumps({"message": "Show sales"}),
            content_type="application/json",
        )
        self.assertEqual(denied.status_code, 403)

        session = self.client.session
        session[VERIFIED_USER_KEY] = str(self.owner.pk)
        session.save()
        client = fake_client("Review the analytics page.")
        openai.return_value = client
        response = self.client.post(
            reverse("staff_chat"),
            data=json.dumps({"message": "Show sales"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["reply"], "Review the analytics page.")
        self.assertNotIn("tools", client.responses.create.call_args.kwargs)

    @patch("core.chatbot.OpenAI")
    def test_owner_receives_aggregate_business_insights_without_customer_identity(self, openai):
        category = Category.objects.create(name="Insights", slug="insights")
        product = Product.objects.create(
            category=category,
            name="Insight Product",
            slug="insight-product",
            description="Test product",
            price=Decimal("1500.00"),
            cost_price=Decimal("900.00"),
            stock=2,
            low_stock_threshold=5,
            image="products/test.jpg",
        )
        order = Order.objects.create(
            user=self.customer,
            order_number="INSIGHT-001",
            full_name="Private Customer Name",
            phone="0712000000",
            email="private@example.com",
            county="Migori",
            city="Rongo",
            estate="Town Centre",
            house_number="1",
            subtotal=Decimal("3000.00"),
            total_amount=Decimal("3250.00"),
            status="processing",
            payment_status="paid",
        )
        OrderItem.objects.create(
            order=order,
            product=product,
            product_name=product.name,
            price=Decimal("1500.00"),
            unit_cost_at_sale=Decimal("900.00"),
            cost_subtotal_at_sale=Decimal("1800.00"),
            quantity=2,
            subtotal=Decimal("3000.00"),
        )

        self.client.force_login(self.owner)
        session = self.client.session
        session[VERIFIED_USER_KEY] = str(self.owner.pk)
        session.save()
        client = fake_client("Sales increased; review stock and fulfilment.")
        openai.return_value = client

        response = self.client.post(
            reverse("staff_chat"),
            data=json.dumps({"message": "What decisions should I make this month?"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        request_input = client.responses.create.call_args.kwargs["input"][-1]["content"]
        self.assertIn("AGGREGATED BUSINESS INSIGHTS", request_input)
        self.assertIn("average order value", request_input)
        self.assertIn("Top products by revenue", request_input)
        self.assertIn("Fulfilment backlog", request_input)
        self.assertNotIn("Private Customer Name", request_input)
        self.assertNotIn("private@example.com", request_input)
