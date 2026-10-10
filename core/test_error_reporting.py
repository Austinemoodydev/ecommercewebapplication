from django.contrib.auth.models import AnonymousUser
from django.http import Http404
from django.test import RequestFactory, TestCase
import json

from .error_middleware import ApplicationErrorMiddleware
from .models import ErrorReport


class ErrorReportingTests(TestCase):
    def setUp(self):
        self.middleware = ApplicationErrorMiddleware(lambda request: None)
        self.factory = RequestFactory()

    def test_html_error_has_reference_and_is_recorded(self):
        request = self.factory.get("/broken-page/")
        request.user = AnonymousUser()
        response = self.middleware.process_exception(request, RuntimeError("Test failure"))
        report = ErrorReport.objects.get()
        self.assertEqual(response.status_code, 500)
        self.assertContains(response, report.reference, status_code=500)
        self.assertEqual(report.path, "/broken-page/")

    def test_ajax_error_returns_safe_json(self):
        request = self.factory.get("/broken-api/", HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        request.user = AnonymousUser()
        response = self.middleware.process_exception(request, ValueError("Private technical detail"))
        payload = json.loads(response.content)
        self.assertEqual(response.status_code, 500)
        self.assertIn("reference", payload)
        self.assertNotIn("Private technical detail", payload["error"])

    def test_expected_client_error_is_left_to_django(self):
        request = self.factory.get("/missing-page/")
        request.user = AnonymousUser()

        response = self.middleware.process_exception(request, Http404("Not found"))

        self.assertIsNone(response)
        self.assertFalse(ErrorReport.objects.exists())
