from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys


ROOT = Path.cwd()

if not (ROOT / "manage.py").exists():
    raise SystemExit(
        "ERROR: Run this from the Django project root containing manage.py."
    )


# ============================================================
# BACKUPS
# ============================================================

stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

backup_dir = (
    ROOT
    / ".capability_security_backups"
    / stamp
)

backup_dir.mkdir(
    parents=True,
    exist_ok=True,
)


def backup(path):

    if not path.exists():
        return

    destination = (
        backup_dir
        / path.relative_to(ROOT)
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        path,
        destination,
    )


settings_file = ROOT / "config" / "settings.py"
payments_views = ROOT / "payments" / "views.py"

middleware_file = (
    ROOT
    / "core"
    / "security_middleware.py"
)

test_file = (
    ROOT
    / "core"
    / "test_capability_url_security.py"
)


for path in [
    settings_file,
    payments_views,
    middleware_file,
    test_file,
]:
    backup(path)


# ============================================================
# 1. SENSITIVE CAPABILITY URL MIDDLEWARE
# ============================================================

middleware_file.write_text(
r'''class SensitiveCapabilityURLMiddleware:
    """
    Extra response protection for URLs containing bearer-like
    capability values.

    Current sensitive URL families:

    /checkout/guest/<order>/<token>/...
    /payments/guest/.../<token>/...
    /payments/callback/?token=...

    These URLs must not be cached, indexed, or leaked through
    browser Referer headers.
    """

    SENSITIVE_PREFIXES = (
        "/checkout/guest/",
        "/payments/guest/",
        "/payments/callback/",
    )


    def __init__(self, get_response):

        self.get_response = get_response


    def __call__(self, request):

        response = self.get_response(
            request
        )

        if request.path.startswith(
            self.SENSITIVE_PREFIXES
        ):

            # Capability URLs contain values which effectively
            # grant access to protected functionality.
            response["Cache-Control"] = (
                "private, no-store, no-cache, "
                "must-revalidate, max-age=0"
            )

            response["Pragma"] = (
                "no-cache"
            )

            response["Expires"] = (
                "0"
            )

            # Stronger than the application's normal
            # same-origin policy for these sensitive pages.
            response["Referrer-Policy"] = (
                "no-referrer"
            )

            # Do not let order/payment capability URLs enter
            # search engine indexes.
            response["X-Robots-Tag"] = (
                "noindex, nofollow, noarchive"
            )


        return response
''',
    encoding="utf-8",
)

print(
    "[CREATED] core/security_middleware.py"
)


# ============================================================
# 2. ENABLE MIDDLEWARE
# ============================================================

text = settings_file.read_text(
    encoding="utf-8-sig"
)

middleware_entry = (
    "'core.security_middleware."
    "SensitiveCapabilityURLMiddleware',"
)


if middleware_entry not in text:

    marker = (
        "'django.middleware.security.SecurityMiddleware',"
    )

    if marker not in text:

        raise SystemExit(
            "ERROR: SecurityMiddleware marker not found."
        )

    text = text.replace(
        marker,
        marker
        + "\n    "
        + middleware_entry,
        1,
    )


settings_file.write_text(
    text,
    encoding="utf-8",
)

print(
    "[PATCHED] SensitiveCapabilityURLMiddleware enabled."
)


# ============================================================
# 3. HARDEN M-PESA CALLBACK
# ============================================================

text = payments_views.read_text(
    encoding="utf-8-sig"
)


# ------------------------------------------------------------
# Constant-time comparison
# ------------------------------------------------------------

if "from secrets import compare_digest" not in text:

    marker = "import json"

    if marker not in text:

        raise SystemExit(
            "ERROR: json import not found in payments/views.py."
        )

    text = text.replace(
        marker,
        marker
        + "\n"
        + "from secrets import compare_digest",
        1,
    )


# ------------------------------------------------------------
# require_POST
# ------------------------------------------------------------

if (
    "from django.views.decorators.http import require_POST"
    not in text
):

    marker = (
        "from django.views.decorators.csrf import csrf_exempt"
    )

    if marker not in text:

        raise SystemExit(
            "ERROR: csrf_exempt import not found."
        )

    text = text.replace(
        marker,
        marker
        + "\n"
        + "from django.views.decorators.http import require_POST",
        1,
    )


# ------------------------------------------------------------
# Callback decorator
# ------------------------------------------------------------

old = '''@csrf_exempt
def mpesa_callback(request):
'''

new = '''@csrf_exempt
@require_POST
def mpesa_callback(request):
'''


if old in text:

    text = text.replace(
        old,
        new,
        1,
    )

elif (
    "@csrf_exempt\n"
    "@require_POST\n"
    "def mpesa_callback"
    not in text
):

    raise SystemExit(
        "ERROR: Could not safely add POST-only callback protection."
    )


# ------------------------------------------------------------
# Replace normal string comparison with constant-time comparison
# ------------------------------------------------------------

old = '''    token = request.GET.get("token")

    if (
        not settings.MPESA_CALLBACK_SECRET
        or token != settings.MPESA_CALLBACK_SECRET
    ):

        return JsonResponse(
            {
                "ResultCode": 1,
                "ResultDesc": "Unauthorized",
            },
            status=403,
        )
'''


new = '''    supplied_token = (
        request.GET.get(
            "token",
            "",
        )
        or ""
    )

    expected_token = (
        settings.MPESA_CALLBACK_SECRET
        or ""
    )

    if (
        not expected_token
        or not supplied_token
        or not compare_digest(
            str(supplied_token),
            str(expected_token),
        )
    ):

        return JsonResponse(
            {
                "ResultCode": 1,
                "ResultDesc": "Unauthorized",
            },
            status=403,
        )
'''


if old in text:

    text = text.replace(
        old,
        new,
        1,
    )

elif "compare_digest(" not in text:

    raise SystemExit(
        "ERROR: Could not safely patch callback secret comparison."
    )


payments_views.write_text(
    text,
    encoding="utf-8",
)

print(
    "[PATCHED] M-PESA callback:"
)

print(
    "          - POST only"
)

print(
    "          - constant-time secret comparison"
)


# ============================================================
# 4. SECURITY REGRESSION TESTS
# ============================================================

test_file.write_text(
r'''from django.http import HttpResponse
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
''',
    encoding="utf-8",
)

print(
    "[CREATED] core/test_capability_url_security.py"
)


# ============================================================
# 5. GITIGNORE
# ============================================================

gitignore = ROOT / ".gitignore"

if gitignore.exists():

    text = gitignore.read_text(
        encoding="utf-8-sig"
    )

    entry = (
        ".capability_security_backups/"
    )

    if entry not in text:

        if not text.endswith("\n"):
            text += "\n"

        text += (
            "\n"
            "# Capability URL security backups\n"
            + entry
            + "\n"
        )

        gitignore.write_text(
            text,
            encoding="utf-8",
        )


# ============================================================
# 6. STATIC SAFETY CHECK
# ============================================================

views_text = (
    payments_views.read_text(
        encoding="utf-8"
    )
)


if (
    "token != settings.MPESA_CALLBACK_SECRET"
    in views_text
):

    raise SystemExit(
        "ERROR: Old callback string comparison still exists."
    )


if (
    "@csrf_exempt\n"
    "@require_POST\n"
    "def mpesa_callback"
    not in views_text
):

    raise SystemExit(
        "ERROR: M-PESA callback is not POST-only."
    )


print(
    "[OK] Static callback checks passed."
)


# ============================================================
# 7. VALIDATION
# ============================================================

commands = [

    [
        sys.executable,
        "manage.py",
        "check",
    ],

    [
        sys.executable,
        "manage.py",
        "makemigrations",
        "--check",
        "--dry-run",
    ],

    [
        sys.executable,
        "manage.py",
        "test",
        "core.test_capability_url_security",
        "-v",
        "2",
    ],

    [
        sys.executable,
        "manage.py",
        "test",
        "payments",
        "orders",
        "-v",
        "1",
    ],
]


for command in commands:

    print()
    print("=" * 72)

    print(
        ">",
        " ".join(
            command
        )
    )

    print("=" * 72)

    result = subprocess.run(
        command,
        cwd=ROOT,
    )

    if result.returncode != 0:

        print()
        print("=" * 72)

        print(
            "CAPABILITY URL SECURITY VALIDATION FAILED"
        )

        print("=" * 72)

        print()
        print(
            "Do not weaken the callback or guest-token protections."
        )

        print(
            "Send me the exact failing output."
        )

        print()
        print(
            "Backup directory:"
        )

        print(
            backup_dir
        )

        raise SystemExit(
            result.returncode
        )


print()
print("=" * 72)

print(
    "GUEST + M-PESA CAPABILITY SECURITY PASSED"
)

print("=" * 72)

print()
print(
    "Guest capability URLs:"
)

print(
    "  - private / no-store"
)

print(
    "  - no-referrer"
)

print(
    "  - noindex / noarchive"
)

print()
print(
    "M-PESA callback:"
)

print(
    "  - POST only"
)

print(
    "  - callback secret required"
)

print(
    "  - missing secret fails closed"
)

print(
    "  - constant-time secret comparison"
)

print(
    "  - response cannot be cached"
)

print()
print(
    "UNCHANGED:"
)

print(
    "  - STK Push transaction logic"
)

print(
    "  - callback transaction locking"
)

print(
    "  - duplicate callback protection"
)

print(
    "  - payment amount verification"
)

print(
    "  - order payment state logic"
)

print(
    "  - inventory consumption/release logic"
)

print()
print(
    "Backup directory:"
)

print(
    backup_dir
)

print()
print(
    "FINAL PROJECT GATE:"
)

print(
    "python manage.py test -v 1"
)

