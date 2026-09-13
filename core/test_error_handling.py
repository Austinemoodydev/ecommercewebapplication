from django.test import (
    RequestFactory,
    SimpleTestCase,
    override_settings,
)

from core.error_views import (
    bad_request,
    page_not_found,
    permission_denied,
    server_error,
)


class ErrorHandlerViewTests(
    SimpleTestCase
):

    def setUp(self):

        self.request = (
            RequestFactory().get(
                "/broken/"
            )
        )


    def assert_secure_error_response(
        self,
        response,
        *,
        expected_status,
        expected_code,
    ):

        self.assertEqual(
            response.status_code,
            expected_status,
        )

        content = (
            response.content.decode(
                "utf-8"
            )
        )

        self.assertIn(
            expected_code,
            content,
        )

        self.assertNotIn(
            "Traceback",
            content,
        )

        self.assertNotIn(
            "Exception Value",
            content,
        )

        self.assertNotIn(
            "Local vars",
            content,
        )

        self.assertEqual(
            response["X-Robots-Tag"],
            "noindex, nofollow",
        )

        self.assertIn(
            "no-store",
            response["Cache-Control"],
        )


    def test_400_handler(self):

        response = bad_request(
            self.request,
            Exception("secret internal detail"),
        )

        self.assert_secure_error_response(
            response,
            expected_status=400,
            expected_code="400",
        )

        self.assertNotContains(
            response,
            "secret internal detail",
            status_code=400,
        )


    def test_403_handler(self):

        response = permission_denied(
            self.request,
            Exception("private permission detail"),
        )

        self.assert_secure_error_response(
            response,
            expected_status=403,
            expected_code="403",
        )

        self.assertNotContains(
            response,
            "private permission detail",
            status_code=403,
        )


    def test_404_handler(self):

        response = page_not_found(
            self.request,
            Exception("private URL detail"),
        )

        self.assert_secure_error_response(
            response,
            expected_status=404,
            expected_code="404",
        )

        self.assertNotContains(
            response,
            "private URL detail",
            status_code=404,
        )


    def test_500_handler(self):

        response = server_error(
            self.request
        )

        self.assert_secure_error_response(
            response,
            expected_status=500,
            expected_code="500",
        )


class DebugFalseIntegrationTests(
    SimpleTestCase
):

    @override_settings(
        DEBUG=False,
        ALLOWED_HOSTS=[
            "testserver",
        ],
        SECURE_SSL_REDIRECT=False,
    )
    def test_unknown_url_uses_custom_404_page(
        self
    ):

        response = self.client.get(
            (
                "/this-page-definitely-"
                "does-not-exist-927451/"
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.assertContains(
            response,
            "Page not found",
            status_code=404,
        )

        self.assertNotContains(
            response,
            "Using the URLconf defined in",
            status_code=404,
        )

        self.assertNotContains(
            response,
            "Traceback",
            status_code=404,
        )

        self.assertEqual(
            response["X-Robots-Tag"],
            "noindex, nofollow",
        )


    @override_settings(
        DEBUG=False,
        ALLOWED_HOSTS=[
            "testserver",
        ],
        SECURE_SSL_REDIRECT=False,
    )
    def test_404_does_not_expose_settings(
        self
    ):

        response = self.client.get(
            "/missing-private-page/"
        )

        content = (
            response.content.decode(
                "utf-8"
            )
        )

        sensitive_markers = [
            "SECRET_KEY",
            "DATABASES",
            "DB_PASSWORD",
            "MPESA_CONSUMER_SECRET",
            "GOOGLE_CLIENT_SECRET",
        ]

        for marker in sensitive_markers:

            with self.subTest(
                marker=marker
            ):

                self.assertNotIn(
                    marker,
                    content,
                )
