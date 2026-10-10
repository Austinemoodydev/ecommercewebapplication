
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
from pathlib import Path
import os
import sys
from dotenv import load_dotenv
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=True) 

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-fallback-for-local-dev-only')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'True') == 'True'
SERVE_MEDIA_LOCALLY = os.environ.get("SERVE_MEDIA_LOCALLY", "False") == "True"

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '127.0.0.1,localhost').split(',')
SITE_URL = os.environ.get("SITE_URL", "http://localhost:8000").rstrip("/")
GOOGLE_SITE_VERIFICATION = os.environ.get("GOOGLE_SITE_VERIFICATION", "")

# AI assistants. The API key is server-side only and is never rendered into
# HTML or returned to the browser.
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_CHAT_MODEL = os.environ.get("OPENAI_CHAT_MODEL", "gpt-4o-mini")
OPENAI_TRANSCRIBE_MODEL = os.environ.get("OPENAI_TRANSCRIBE_MODEL", "gpt-transcribe")
CHATBOT_ENABLED = bool(OPENAI_API_KEY)
CHATBOT_MAX_MESSAGE_CHARS = 600
CHATBOT_MAX_HISTORY_ITEMS = 8
CHATBOT_MAX_AUDIO_BYTES = 5 * 1024 * 1024


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.mfa',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.facebook',
    'allauth.socialaccount.providers.apple',
    'accounts',
    'core',
    'common',
    'django_ratelimit',
    'products',
    'inventory',
    'crm',
    'categories',
    'cart',
    'wishlist',
    'orders',
    'payments',
    'delivery',
    'reviews',
    'dashboard',
    'notifications',
]

MIGRATION_MODULES = {
    "socialaccount": "config.socialaccount_migrations",
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'core.security_middleware.SensitiveCapabilityURLMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'core.error_middleware.ApplicationErrorMiddleware',
    'accounts.staff_access.StoreStaffPermissionMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'builtins': ['core.templatetags.money'],
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'notifications.context_processors.notification_counts',
                "core.context_processors.global_context",
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
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
}


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Africa/Nairobi'

USE_I18N = True

USE_TZ = True




# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

BASE_DIR = Path(__file__).resolve().parent.parent

STATIC_URL = '/static/'

# Directory populated by `python manage.py collectstatic`.
# Source static files remain in the normal app/static directories.
STATIC_ROOT = BASE_DIR / "staticfiles"


STATICFILES_DIRS = [
    BASE_DIR / "static",
]

MEDIA_URL = '/media/'

MEDIA_ROOT = BASE_DIR / "media"

TEMPLATES[0]['DIRS'] = [
    BASE_DIR / "templates"
]
AUTH_USER_MODEL = 'accounts.CustomUser'
SITE_ID = 1
# This project is running on a MySQL server with a 1000-byte index limit.
# 191 characters keeps allauth's unique email index valid with utf8mb4.
ACCOUNT_EMAIL_MAX_LENGTH = 191
SOCIALACCOUNT_UID_MAX_LENGTH = 40

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

LOGIN_REDIRECT_URL = "/"
ACCOUNT_SIGNUP_REDIRECT_URL = "/"
SOCIALACCOUNT_ADAPTER = "accounts.adapters.CustomerOnlySocialAccountAdapter"

# Store-management MFA. Customer and guest-checkout authentication are
# deliberately separate and are not made subject to this policy.
MFA_SUPPORTED_TYPES = ["totp", "recovery_codes"]
MFA_TOTP_ISSUER = os.environ.get("MFA_TOTP_ISSUER", "Online Shop Management")
MFA_RECOVERY_CODES_SHOW_ONCE = True
MFA_TOTP_TOLERANCE = 1
MFA_ADAPTER = "accounts.mfa_adapter.EncryptedMFAAdapter"
MFA_ENCRYPTION_KEY = os.environ.get("MFA_ENCRYPTION_KEY", SECRET_KEY)
# Production/runtime default is mandatory. The bypass exists only so older
# unit tests that intentionally use Django's force_login() can isolate the
# feature under test; dedicated MFA tests turn enforcement back on.
MFA_STAFF_ENFORCEMENT = os.environ.get(
    "MFA_STAFF_ENFORCEMENT",
    "False" if "test" in sys.argv else "True",
).lower() == "true"


# ------------------------------------------------------------
# ORDER / PAYMENT TIMEOUTS
# ------------------------------------------------------------

ORDER_RESERVATION_MINUTES = 30

MPESA_STK_ACTIVE_SECONDS = 120

MPESA_PAYMENT_GRACE_MINUTES = 10

# M-PESA Daraja settings
MPESA_CONSUMER_KEY = os.environ.get("MPESA_CONSUMER_KEY")
MPESA_CONSUMER_SECRET = os.environ.get("MPESA_CONSUMER_SECRET")
MPESA_SHORTCODE = os.environ.get("MPESA_SHORTCODE")
MPESA_PASSKEY = os.environ.get("MPESA_PASSKEY")
MPESA_CALLBACK_URL = os.environ.get("MPESA_CALLBACK_URL")
MPESA_ENV = os.environ.get("MPESA_ENV", "sandbox")
MPESA_TRANSACTION_TYPE = os.environ.get("MPESA_TRANSACTION_TYPE", "CustomerPayBillOnline")




MPESA_CALLBACK_SECRET = os.environ.get("MPESA_CALLBACK_SECRET")

# Production security settings (only active when DEBUG=False)
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(
        os.environ.get(
            "SECURE_HSTS_SECONDS",
            "0",
        )
    )
    SECURE_HSTS_INCLUDE_SUBDOMAINS = (
        os.environ.get(
            "SECURE_HSTS_INCLUDE_SUBDOMAINS",
            "False",
        ).lower()
        == "true"
    )
    SECURE_HSTS_PRELOAD = (
        os.environ.get(
            "SECURE_HSTS_PRELOAD",
            "False",
        ).lower()
        == "true"
    )


CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache"
        if not DEBUG else "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": os.environ.get("CACHE_URL", "redis://localhost:6379/1"),
    }
}

RATELIMIT_USE_CACHE = "default"

SILENCED_SYSTEM_CHECKS = ["django_ratelimit.E003"]

# Celery
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True

CELERY_BEAT_SCHEDULE = {

    "dispatch-due-marketing-campaigns": {
        "task": "core.tasks.dispatch_due_campaigns",
        "schedule": 300.0,
    },

    "expire-unpaid-orders": {

        "task": "orders.tasks.expire_unpaid_orders",

        "schedule": 300.0,
    },
}

# Africa's Talking
AFRICASTALKING_USERNAME = os.environ.get("AFRICASTALKING_USERNAME")
AFRICASTALKING_API_KEY = os.environ.get("AFRICASTALKING_API_KEY")

# Email
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = os.environ.get("EMAIL_HOST_USER")

# OAuth credentials stay in environment variables. Callback URLs are:
# /accounts/social/<provider>/login/callback/
SOCIALACCOUNT_LOGIN_ON_GET = False
SOCIALACCOUNT_EMAIL_REQUIRED = True
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APPS": [{"client_id": os.environ.get("GOOGLE_CLIENT_ID", ""), "secret": os.environ.get("GOOGLE_CLIENT_SECRET", ""), "key": ""}],
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
        "OAUTH_PKCE_ENABLED": True,
        "EMAIL_AUTHENTICATION": True,
    },
    "facebook": {
        "APPS": [{"client_id": os.environ.get("FACEBOOK_CLIENT_ID", ""), "secret": os.environ.get("FACEBOOK_CLIENT_SECRET", ""), "key": ""}],
        "SCOPE": ["email"],
        "FIELDS": ["id", "name", "email"],
    },
    "apple": {
        "APPS": [{"client_id": os.environ.get("APPLE_SERVICE_ID", ""), "secret": os.environ.get("APPLE_KEY_ID", ""), "key": os.environ.get("APPLE_TEAM_ID", "")}],
        "SETTINGS": {"certificate_key": os.environ.get("APPLE_PRIVATE_KEY", "")},
    },
}





# ============================================================
# RETURNS / REFUNDS
# ============================================================

RETURN_WINDOW_DAYS = 14


# ============================================================
# ABANDONED CARTS
# ============================================================

# A cart is considered abandoned only when it still contains
# products, has not produced an order, and has had no genuine
# cart/checkout activity for this many hours.
CART_ABANDONED_AFTER_HOURS = int(
    os.environ.get(
        "CART_ABANDONED_AFTER_HOURS",
        "24",
    )
)


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
