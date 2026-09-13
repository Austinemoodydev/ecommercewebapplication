from django.http import HttpResponse
from django.test import (
    RequestFactory,
    SimpleTestCase,
    override_settings,
)
from django.urls import reverse

from core.security_middleware import (
    SensitiveCapabilityURLMiddleware,
)


class SensitiveCapabilityHeaderTests(
    SimpleTestCase
):

    def setUp(self):

        self.factory = (
            RequestFactory()
        )

        self.middleware = (
            SensitiveCapabilityURLMiddleware(
                lambda request: HttpResponse(
                    "OK"
                )
            )
        )


    def assert_sensitive_headers(
        self,
        path,
    ):

        request = (
            self.factory.get(
                path
            )
        )

        response = (
            self.middleware(
                request
            )
        )

        self.assertIn(
            "no-store",
            response[
                "Cache-Control"
            ],
        )

        self.assertIn(
            "private",
            response[
                "Cache-Control"
            ],
        )

        self.assertEqual(
            response[
                "Referrer-Policy"
            ],
            "no-referrer",
        )

        self.assertEqual(
            response[
                "Pragma"
            ],
            "no-cache",
        )

        self.assertIn(
            "noindex",
            response[
                "X-Robots-Tag"
            ],
        )


    def test_guest_order_url_is_sensitive(
        self
    ):

        self.assert_sensitive_headers(
            (
                "/checkout/guest/"
                "ORD-123/"
                "secret-token/"
            )
        )


    def test_guest_payment_url_is_sensitive(
        self
    ):

        self.assert_sensitive_headers(
            (
                "/payments/guest/pay/"
                "ORD-123/"
                "secret-token/"
            )
        )


    def test_callback_url_is_sensitive(
        self
    ):

        self.assert_sensitive_headers(
            (
                "/payments/callback/"
                "?token=callback-secret"
            )
        )


    def test_normal_shop_page_is_not_forced_no_referrer(
        self
    ):

        request = (
            self.factory.get(
                "/shop/"
            )
        )

        response = (
            self.middleware(
                request
            )
        )

        self.assertNotIn(
            "Referrer-Policy",
            response,
        )

        self.assertNotIn(
            "X-Robots-Tag",
            response,
        )


class MpesaCallbackSecurityTests(
    SimpleTestCase
):

    @override_settings(
        MPESA_CALLBACK_SECRET=(
            "very-long-test-callback-secret"
        )
    )
    def test_callback_rejects_get_requests(
        self
    ):

        url = (
            reverse(
                "mpesa_callback"
            )
            + "?token="
            + "very-long-test-callback-secret"
        )

        response = (
            self.client.get(
                url
            )
        )

        self.assertEqual(
            response.status_code,
            405,
        )


    @override_settings(
        MPESA_CALLBACK_SECRET=(
            "very-long-test-callback-secret"
        )
    )
    def test_callback_rejects_missing_secret(
        self
    ):

        response = (
            self.client.post(
                reverse(
                    "mpesa_callback"
                ),
                data=b"{}",
                content_type=(
                    "application/json"
                ),
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        self.assertEqual(
            response.json()[
                "ResultDesc"
            ],
            "Unauthorized",
        )


    @override_settings(
        MPESA_CALLBACK_SECRET=(
            "very-long-test-callback-secret"
        )
    )
    def test_callback_rejects_wrong_secret(
        self
    ):

        url = (
            reverse(
                "mpesa_callback"
            )
            + "?token=wrong-secret"
        )

        response = (
            self.client.post(
                url,
                data=b"{}",
                content_type=(
                    "application/json"
                ),
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )


    @override_settings(
        MPESA_CALLBACK_SECRET=(
            "very-long-test-callback-secret"
        )
    )
    def test_authorized_callback_reaches_payload_validation(
        self
    ):

        url = (
            reverse(
                "mpesa_callback"
            )
            + "?token="
            + "very-long-test-callback-secret"
        )

        response = (
            self.client.post(
                url,
                data=b"not-valid-json",
                content_type=(
                    "application/json"
                ),
            )
        )

        # Authorization succeeded.
        # The callback then rejected only the payload.
        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.json()[
                "ResultDesc"
            ],
            "Invalid payload",
        )


    @override_settings(
        MPESA_CALLBACK_SECRET=(
            "very-long-test-callback-secret"
        )
    )
    def test_callback_response_has_sensitive_headers(
        self
    ):

        url = (
            reverse(
                "mpesa_callback"
            )
            + "?token=wrong-secret"
        )

        response = (
            self.client.post(
                url,
                data=b"{}",
                content_type=(
                    "application/json"
                ),
            )
        )

        self.assertEqual(
            response[
                "Referrer-Policy"
            ],
            "no-referrer",
        )

        self.assertIn(
            "no-store",
            response[
                "Cache-Control"
            ],
        )

        self.assertIn(
            "noindex",
            response[
                "X-Robots-Tag"
            ],
        )


    @override_settings(
        MPESA_CALLBACK_SECRET=""
    )
    def test_callback_fails_closed_when_secret_missing(
        self
    ):

        response = (
            self.client.post(
                reverse(
                    "mpesa_callback"
                ),
                data=b"{}",
                content_type=(
                    "application/json"
                ),
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )
