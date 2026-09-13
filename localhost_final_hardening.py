from pathlib import Path
import subprocess
import sys
import shutil
from datetime import datetime

ROOT = Path.cwd()

if not (ROOT / "manage.py").exists():
    raise SystemExit(
        "ERROR: Open the VS Code terminal in the Django project root first."
    )

STAMP = datetime.now().strftime("%Y%m%d-%H%M%S")
BACKUP = ROOT / ".hardening_backups" / STAMP
BACKUP.mkdir(parents=True, exist_ok=True)

print("=" * 70)
print("ONLINE SHOP — LOCALHOST HARDENING")
print("=" * 70)
print("Project:", ROOT)
print("Backup:", BACKUP)
print()


def backup_file(relative_path):
    source = ROOT / relative_path

    if not source.exists():
        raise RuntimeError(
            f"Required file not found: {relative_path}"
        )

    destination = BACKUP / relative_path
    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        source,
        destination,
    )


def read(relative_path):
    path = ROOT / relative_path

    if not path.exists():
        raise RuntimeError(
            f"Required file not found: {relative_path}"
        )

    return path.read_text(
        encoding="utf-8-sig"
    )


def write(relative_path, content):
    backup_file(relative_path)

    path = ROOT / relative_path

    path.write_text(
        content,
        encoding="utf-8",
    )

    print(
        "[PATCHED]",
        relative_path,
    )


# ============================================================
# FIX 1
# VERIFIED EMAIL MUST BECOME UNVERIFIED AFTER EMAIL CHANGE
# ============================================================

path = "accounts/views.py"
text = read(path)

old = '''@login_required
def profile(request):
    form = ProfileForm(
        request.POST or None,
        request.FILES or None,
        instance=request.user,
    )

    if request.method == "POST" and form.is_valid():

        old_email = (
            request.user.email or ""
        ).strip().lower()

        user = form.save(commit=False)

        new_email = (
            user.email or ""
        ).strip().lower()

        email_changed = (
            old_email != new_email
        )
'''

new = '''@login_required
def profile(request):

    # IMPORTANT:
    # Capture the database value BEFORE ModelForm validation.
    #
    # ModelForm.is_valid() updates fields on the model instance.
    # Reading request.user.email afterwards can therefore return
    # the NEW email instead of the original email.
    original_email = (
        request.user.email or ""
    ).strip().lower()

    form = ProfileForm(
        request.POST or None,
        request.FILES or None,
        instance=request.user,
    )

    if request.method == "POST" and form.is_valid():

        user = form.save(commit=False)

        new_email = (
            user.email or ""
        ).strip().lower()

        email_changed = (
            original_email != new_email
        )
'''

if old in text:

    text = text.replace(
        old,
        new,
        1,
    )

    write(
        path,
        text,
    )

elif "original_email =" in text:

    print(
        "[ALREADY FIXED]",
        path,
    )

else:

    raise RuntimeError(
        "Could not safely identify profile email-change code."
    )


# ============================================================
# FIX 2
# REMOVE DUPLICATE RegisterForm clean_email METHOD IF PRESENT
# ============================================================

path = "accounts/forms.py"
text = read(path)

start = text.find(
    "class RegisterForm"
)

end = text.find(
    "class AddressForm"
)

if start == -1 or end == -1:

    raise RuntimeError(
        "RegisterForm/AddressForm could not be identified."
    )

register_section = text[
    start:end
]

needle = "    def clean_email(self):"

count = register_section.count(
    needle
)

if count > 1:

    first = register_section.find(
        needle
    )

    second = register_section.find(
        needle,
        first + len(needle),
    )

    next_class_or_end = len(
        register_section
    )

    cleaned = (
        register_section[:second].rstrip()
        + "\n\n"
    )

    text = (
        text[:start]
        + cleaned
        + text[end:]
    )

    write(
        path,
        text,
    )

    print(
        "[FIXED] duplicate RegisterForm.clean_email"
    )

else:

    print(
        "[OK] RegisterForm clean_email count:",
        count,
    )


# ============================================================
# FIX 3
# ADDRESS ACTIONS MUST BE POST + CSRF
# ============================================================

path = "templates/accounts/dashboard/addresses.html"

if (ROOT / path).exists():

    text = read(path)

    old_default = '''<a href="{% url 'set_default_address' address.id %}" class="btn btn-outline-success btn-sm">
                            Make Default
                        </a>'''

    new_default = '''<form method="post"
                              action="{% url 'set_default_address' address.id %}"
                              class="d-inline">
                            {% csrf_token %}
                            <button type="submit"
                                    class="btn btn-outline-success btn-sm">
                                Make Default
                            </button>
                        </form>'''

    old_delete = '''<a href="{% url 'delete_address' address.id %}" class="btn btn-outline-danger btn-sm"
                           onclick="return confirm('Delete this address?');">
                            Delete
                        </a>'''

    new_delete = '''<form method="post"
                              action="{% url 'delete_address' address.id %}"
                              class="d-inline"
                              onsubmit="return confirm('Delete this address?');">
                            {% csrf_token %}
                            <button type="submit"
                                    class="btn btn-outline-danger btn-sm">
                                Delete
                            </button>
                        </form>'''

    changed = False

    if old_default in text:

        text = text.replace(
            old_default,
            new_default,
            1,
        )

        changed = True

    if old_delete in text:

        text = text.replace(
            old_delete,
            new_delete,
            1,
        )

        changed = True

    if changed:

        write(
            path,
            text,
        )

    else:

        print(
            "[OK] Address frontend already appears POST-safe."
        )


# ============================================================
# FIX 4
# STATIC URL NORMALIZATION
# ============================================================

path = "config/settings.py"
text = read(path)

if "STATIC_URL = 'static/'" in text:

    text = text.replace(
        "STATIC_URL = 'static/'",
        "STATIC_URL = '/static/'",
        1,
    )

    write(
        path,
        text,
    )

elif 'STATIC_URL = "static/"' in text:

    text = text.replace(
        'STATIC_URL = "static/"',
        'STATIC_URL = "/static/"',
        1,
    )

    write(
        path,
        text,
    )

else:

    print(
        "[OK] STATIC_URL already normalized."
    )


# ============================================================
# FIX 5
# DATABASE SETTINGS -> ENVIRONMENT VARIABLES
# LOCALHOST DEFAULTS REMAIN THE SAME
# ============================================================

path = "config/settings.py"
text = read(path)

old = """DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'onlinestore',
        'USER': 'root',
        'PASSWORD': '',
        'HOST': 'localhost',
        'PORT': '3306',
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES,NO_ENGINE_SUBSTITUTION'",
        },
    }
}"""

new = '''DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",

        # Localhost defaults continue working.
        # Production values can later be supplied through .env.
        "NAME": os.environ.get(
            "DB_NAME",
            "onlinestore",
        ),

        "USER": os.environ.get(
            "DB_USER",
            "root",
        ),

        "PASSWORD": os.environ.get(
            "DB_PASSWORD",
            "",
        ),

        "HOST": os.environ.get(
            "DB_HOST",
            "localhost",
        ),

        "PORT": os.environ.get(
            "DB_PORT",
            "3306",
        ),

        "OPTIONS": {
            "charset": "utf8mb4",

            "init_command": (
                "SET sql_mode="
                "'STRICT_TRANS_TABLES,"
                "NO_ENGINE_SUBSTITUTION'"
            ),
        },
    }
}'''

if old in text:

    text = text.replace(
        old,
        new,
        1,
    )

    write(
        path,
        text,
    )

elif '"DB_NAME"' in text:

    print(
        "[OK] Database configuration already environment-driven."
    )

else:

    print(
        "[NOTICE] Database block differs from inspected version."
    )
    print(
        "         It was NOT modified automatically."
    )


# ============================================================
# FIX 6
# CSRF TRUSTED ORIGINS ENV SUPPORT
# ============================================================

path = "config/settings.py"
text = read(path)

if "CSRF_TRUSTED_ORIGINS =" not in text:

    addition = '''

# Deployment origins are intentionally empty on localhost.
# Example production value:
# CSRF_TRUSTED_ORIGINS=https://example.com,https://www.example.com
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "CSRF_TRUSTED_ORIGINS",
        "",
    ).split(",")
    if origin.strip()
]

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
'''

    text += addition

    write(
        path,
        text,
    )

else:

    print(
        "[OK] CSRF_TRUSTED_ORIGINS already configured."
    )


# ============================================================
# FIX 7
# SAFE HSTS DEFAULT
# DO NOT PRELOAD A DOMAIN BEFORE WE ACTUALLY HAVE ONE
# ============================================================

path = "config/settings.py"
text = read(path)

changed = False

if "SECURE_HSTS_SECONDS = 31536000" in text:

    text = text.replace(
        "SECURE_HSTS_SECONDS = 31536000  # 1 year",
        '''SECURE_HSTS_SECONDS = int(
        os.environ.get(
            "SECURE_HSTS_SECONDS",
            "0",
        )
    )''',
        1,
    )

    changed = True

if "SECURE_HSTS_INCLUDE_SUBDOMAINS = True" in text:

    text = text.replace(
        "SECURE_HSTS_INCLUDE_SUBDOMAINS = True",
        '''SECURE_HSTS_INCLUDE_SUBDOMAINS = (
        os.environ.get(
            "SECURE_HSTS_INCLUDE_SUBDOMAINS",
            "False",
        ).lower()
        == "true"
    )''',
        1,
    )

    changed = True

if "SECURE_HSTS_PRELOAD = True" in text:

    text = text.replace(
        "SECURE_HSTS_PRELOAD = True",
        '''SECURE_HSTS_PRELOAD = (
        os.environ.get(
            "SECURE_HSTS_PRELOAD",
            "False",
        ).lower()
        == "true"
    )''',
        1,
    )

    changed = True

if changed:

    write(
        path,
        text,
    )

else:

    print(
        "[OK] HSTS does not appear hardcoded."
    )


# ============================================================
# FIX 8
# .env.example
# ============================================================

env_example = ROOT / ".env.example"

if not env_example.exists():

    env_example.write_text(
'''# ==========================================================
# LOCALHOST
# ==========================================================

DEBUG=True

SECRET_KEY=replace-with-local-secret

ALLOWED_HOSTS=127.0.0.1,localhost

SITE_URL=http://127.0.0.1:8000


# ==========================================================
# DATABASE
# ==========================================================

DB_NAME=onlinestore
DB_USER=root
DB_PASSWORD=
DB_HOST=localhost
DB_PORT=3306


# ==========================================================
# REDIS / CELERY
# ==========================================================

CACHE_URL=redis://localhost:6379/1

CELERY_BROKER_URL=redis://localhost:6379/0

CELERY_RESULT_BACKEND=redis://localhost:6379/0


# ==========================================================
# M-PESA
# KEEP SANDBOX ON LOCALHOST
# ==========================================================

MPESA_ENV=sandbox

MPESA_CONSUMER_KEY=

MPESA_CONSUMER_SECRET=

MPESA_SHORTCODE=

MPESA_PASSKEY=

MPESA_CALLBACK_URL=

MPESA_CALLBACK_SECRET=


# ==========================================================
# EMAIL
# ==========================================================

EMAIL_HOST_USER=

EMAIL_HOST_PASSWORD=


# ==========================================================
# SMS
# ==========================================================

AFRICASTALKING_USERNAME=

AFRICASTALKING_API_KEY=


# ==========================================================
# SOCIAL AUTH
# ==========================================================

GOOGLE_CLIENT_ID=

GOOGLE_CLIENT_SECRET=

FACEBOOK_CLIENT_ID=

FACEBOOK_CLIENT_SECRET=

APPLE_SERVICE_ID=

APPLE_KEY_ID=

APPLE_TEAM_ID=

APPLE_PRIVATE_KEY=


# ==========================================================
# FUTURE PRODUCTION
# DO NOT CONFIGURE UNTIL A DOMAIN EXISTS
# ==========================================================

CSRF_TRUSTED_ORIGINS=

SECURE_HSTS_SECONDS=0

SECURE_HSTS_INCLUDE_SUBDOMAINS=False

SECURE_HSTS_PRELOAD=False
''',
        encoding="utf-8",
    )

    print(
        "[CREATED] .env.example"
    )

else:

    print(
        "[OK] .env.example already exists."
    )


# ============================================================
# FIX 9
# GITIGNORE HARDENING
# ============================================================

path = ".gitignore"

text = read(path)

required = [
    ".env",
    "*.sql",
    "config/dbfile/*.sql",
    "staticfiles/",
    ".hardening_backups/",
]

lines = text.splitlines()

for entry in required:

    if entry not in lines:

        lines.append(
            entry
        )

text = (
    "\n".join(lines).strip()
    + "\n"
)

write(
    path,
    text,
)


# ============================================================
# GIT SECRET/DB TRACKING CHECK
# ============================================================

print()
print("=" * 70)
print("GIT SENSITIVE FILE CHECK")
print("=" * 70)

try:

    output = subprocess.check_output(
        [
            "git",
            "ls-files",
        ],
        cwd=ROOT,
        text=True,
        stderr=subprocess.STDOUT,
    )

    tracked = output.splitlines()

    unsafe = [
        filename
        for filename in tracked
        if (
            filename == ".env"
            or filename.lower().endswith(
                ".sql"
            )
            or filename.lower().endswith(
                "db.sqlite3"
            )
        )
    ]

    if unsafe:

        print(
            "WARNING: Git still tracks:"
        )

        for filename in unsafe:

            print(
                " -",
                filename,
            )

        print()
        print(
            "These files must be removed from Git tracking "
            "before production."
        )

    else:

        print(
            "PASS: no .env / SQL dump / db.sqlite3 "
            "is tracked by Git."
        )

except Exception as exc:

    print(
        "Git inspection could not run:",
        type(exc).__name__,
    )


# ============================================================
# AUTOMATED LOCALHOST GATE
# ============================================================

print()
print("=" * 70)
print("RUNNING AUTOMATED LOCALHOST GATE")
print("=" * 70)


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
        "accounts.test_ship_phase2",
        "-v",
        "2",
    ],

    [
        sys.executable,
        "manage.py",
        "test",
        "accounts",
        "-v",
        "1",
    ],

    [
        sys.executable,
        "manage.py",
        "test",
        "delivery",
        "payments",
        "orders",
        "-v",
        "1",
    ],

    [
        sys.executable,
        "manage.py",
        "collectstatic",
        "--noinput",
    ],

    [
        sys.executable,
        "manage.py",
        "test",
        "-v",
        "1",
    ],
]


for command in commands:

    print()
    print(
        ">",
        " ".join(command),
    )

    print(
        "-" * 70
    )

    result = subprocess.run(
        command,
        cwd=ROOT,
    )

    if result.returncode != 0:

        print()
        print("=" * 70)
        print("STOPPED — A TEST/CHECK FAILED")
        print("=" * 70)

        print(
            "Nothing else will be changed by this script."
        )

        print(
            "Backups are here:"
        )

        print(
            BACKUP
        )

        raise SystemExit(
            result.returncode
        )


print()
print("=" * 70)
print("AUTOMATED LOCALHOST GATE PASSED")
print("=" * 70)

print()
print(
    "Django checks passed."
)

print(
    "Migration drift check passed."
)

print(
    "Authentication regression tests passed."
)

print(
    "Order/payment/delivery regression tests passed."
)

print(
    "collectstatic passed."
)

print(
    "Full Django test suite passed."
)

print()
print(
    "NO production deployment was performed."
)

print(
    "NO production payment credentials were used."
)

print()
print(
    "Backup directory:"
)

print(
    BACKUP
)

print()
print(
    "Next step is FINAL LOCALHOST MANUAL QA:"
)

print(
    "customer browser flow + admin browser flow + "
    "M-Pesa sandbox + email/SMS + mobile QA + backup restore."
)
