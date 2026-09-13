from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys


ROOT = Path.cwd()

if not (ROOT / "manage.py").exists():
    raise SystemExit(
        "ERROR: Run this from the Django project root."
    )


# ============================================================
# BACKUPS
# ============================================================

stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

backup_dir = (
    ROOT
    / ".error_handling_backups"
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


urls_file = ROOT / "config" / "urls.py"
error_views = ROOT / "core" / "error_views.py"
test_file = ROOT / "core" / "test_error_handling.py"

template_dir = (
    ROOT
    / "core"
    / "templates"
    / "errors"
)

template_dir.mkdir(
    parents=True,
    exist_ok=True,
)


for path in [
    urls_file,
    error_views,
    test_file,
]:
    backup(path)


for filename in [
    "400.html",
    "403.html",
    "404.html",
    "500.html",
]:
    backup(
        template_dir / filename
    )


# ============================================================
# 1. ERROR HANDLER VIEWS
# ============================================================

error_views.write_text(
r'''from django.http import HttpResponse
from django.template.loader import get_template


def _error_response(
    template_name,
    *,
    status,
):

    # Render without passing request.
    #
    # This deliberately avoids normal context processors,
    # because some of this project's storefront context
    # processors query the database. A server error page
    # should still render even if the database is unavailable.
    template = get_template(
        template_name
    )

    html = template.render({})

    response = HttpResponse(
        html,
        status=status,
        content_type="text/html; charset=utf-8",
    )

    response["Cache-Control"] = (
        "no-store, no-cache, must-revalidate"
    )

    response["Pragma"] = "no-cache"

    response["X-Robots-Tag"] = (
        "noindex, nofollow"
    )

    return response


def bad_request(
    request,
    exception=None,
):

    return _error_response(
        "errors/400.html",
        status=400,
    )


def permission_denied(
    request,
    exception=None,
):

    return _error_response(
        "errors/403.html",
        status=403,
    )


def page_not_found(
    request,
    exception=None,
):

    return _error_response(
        "errors/404.html",
        status=404,
    )


def server_error(request):

    return _error_response(
        "errors/500.html",
        status=500,
    )
''',
    encoding="utf-8",
)

print(
    "[CREATED] core/error_views.py"
)


# ============================================================
# 2. ERROR TEMPLATES
# ============================================================

base_style = r'''
        :root {
            --blue: #2563eb;
            --blue-dark: #1d4ed8;
            --soft-blue: #eff6ff;
            --orange: #f97316;
            --text: #172033;
            --muted: #64748b;
            --border: #dbeafe;
        }

        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            min-height: 100vh;
            display: grid;
            place-items: center;
            padding: 24px;
            background:
                linear-gradient(
                    135deg,
                    #eff6ff,
                    #ffffff
                );
            color: var(--text);
            font-family:
                Arial,
                Helvetica,
                sans-serif;
        }

        .error-card {
            width: min(620px, 100%);
            background: white;
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 42px 34px;
            text-align: center;
            box-shadow:
                0 18px 50px
                rgba(37, 99, 235, 0.10);
        }

        .code {
            margin: 0;
            color: var(--blue);
            font-size: clamp(4rem, 14vw, 7rem);
            line-height: 1;
            font-weight: 800;
        }

        h1 {
            margin:
                18px 0
                10px;
            font-size: 1.8rem;
        }

        p {
            max-width: 470px;
            margin:
                0 auto
                26px;
            color: var(--muted);
            line-height: 1.6;
        }

        .actions {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 12px;
        }

        a {
            display: inline-block;
            padding: 12px 20px;
            border-radius: 10px;
            text-decoration: none;
            font-weight: 700;
        }

        .primary {
            background: var(--blue);
            color: white;
        }

        .primary:hover {
            background: var(--blue-dark);
        }

        .secondary {
            background: var(--soft-blue);
            color: var(--blue-dark);
        }

        .accent {
            width: 50px;
            height: 5px;
            margin: 0 auto 24px;
            border-radius: 99px;
            background: var(--orange);
        }
'''


pages = {

    "400.html": (
        "400",
        "Bad request",
        (
            "We could not process that request. "
            "Please check the information submitted "
            "and try again."
        ),
    ),

    "403.html": (
        "403",
        "Access denied",
        (
            "You do not have permission to access "
            "this page or perform this action."
        ),
    ),

    "404.html": (
        "404",
        "Page not found",
        (
            "The page you requested does not exist "
            "or may have been moved."
        ),
    ),

    "500.html": (
        "500",
        "Something went wrong",
        (
            "The server could not complete your request. "
            "Please try again shortly."
        ),
    ),
}


for filename, (
    code,
    heading,
    message,
) in pages.items():

    html = f'''<!doctype html>
<html lang="en">

<head>

    <meta charset="utf-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1"
    >

    <meta
        name="robots"
        content="noindex,nofollow"
    >

    <title>
        {code} - {heading}
    </title>

    <style>
{base_style}
    </style>

</head>

<body>

    <main
        class="error-card"
        role="main"
    >

        <div class="accent"></div>

        <p class="code">
            {code}
        </p>

        <h1>
            {heading}
        </h1>

        <p>
            {message}
        </p>

        <div class="actions">

            <a
                class="primary"
                href="/"
            >
                Go to homepage
            </a>

            <a
                class="secondary"
                href="/shop/"
            >
                Continue shopping
            </a>

        </div>

    </main>

</body>

</html>
'''

    (
        template_dir
        / filename
    ).write_text(
        html,
        encoding="utf-8",
    )


print(
    "[CREATED] 400/403/404/500 templates"
)


# ============================================================
# 3. REGISTER PROJECT-LEVEL HANDLERS
# ============================================================

text = urls_file.read_text(
    encoding="utf-8-sig"
)


handler_block = '''
handler400 = "core.error_views.bad_request"
handler403 = "core.error_views.permission_denied"
handler404 = "core.error_views.page_not_found"
handler500 = "core.error_views.server_error"
'''


if (
    'handler404 = "core.error_views.page_not_found"'
    not in text
):

    marker = (
        "configure_system_admin_site()"
    )

    if marker not in text:

        raise SystemExit(
            "ERROR: Could not locate URL configuration marker."
        )

    text = text.replace(
        marker,
        marker
        + "\n"
        + handler_block,
        1,
    )


urls_file.write_text(
    text,
    encoding="utf-8",
)

print(
    "[PATCHED] Project error handlers registered."
)


# ============================================================
# 4. REGRESSION TESTS
# ============================================================

test_file.write_text(
r'''from django.test import (
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
''',
    encoding="utf-8",
)

print(
    "[CREATED] core/test_error_handling.py"
)


# ============================================================
# 5. GITIGNORE BACKUPS
# ============================================================

gitignore = ROOT / ".gitignore"

if gitignore.exists():

    text = gitignore.read_text(
        encoding="utf-8-sig"
    )

    entry = (
        ".error_handling_backups/"
    )

    if entry not in text:

        if not text.endswith("\n"):
            text += "\n"

        text += (
            "\n"
            "# Error handling local backups\n"
            + entry
            + "\n"
        )

        gitignore.write_text(
            text,
            encoding="utf-8",
        )


# ============================================================
# 6. VALIDATION
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
        "core.test_error_handling",
        "-v",
        "2",
    ],

    [
        sys.executable,
        "manage.py",
        "test",
        "core",
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
            "ERROR-HANDLING VALIDATION FAILED"
        )

        print("=" * 72)

        print()
        print(
            "Do not remove DEBUG=False protection."
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
    "DEBUG=FALSE ERROR HANDLING PASSED"
)

print("=" * 72)

print()
print(
    "Protected responses:"
)

print(
    "  400 Bad Request"
)

print(
    "  403 Permission Denied"
)

print(
    "  404 Page Not Found"
)

print(
    "  500 Server Error"
)

print()
print(
    "Verified:"
)

print(
    "  - No Django technical 404 page"
)

print(
    "  - No traceback information"
)

print(
    "  - No exception detail leakage"
)

print(
    "  - Error pages are noindex"
)

print(
    "  - Error pages are no-store"
)

print(
    "  - Error rendering avoids DB-dependent context processors"
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
    "FINAL FULL-SUITE COMMAND:"
)

print(
    "python manage.py test -v 1"
)

