from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.db import transaction
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from django_ratelimit.decorators import ratelimit

from allauth.mfa.adapter import get_adapter
from allauth.mfa.models import Authenticator
from allauth.mfa.recovery_codes.internal.auth import RecoveryCodes
from allauth.mfa.totp.internal.auth import TOTP, generate_totp_secret, validate_totp_code

from .models import StaffSecurityEvent
from .staff_access import can_access_store_management


User = get_user_model()
PENDING_USER_KEY = "staff_mfa_pending_user"
PENDING_BACKEND_KEY = "staff_mfa_pending_backend"
PENDING_NEXT_KEY = "staff_mfa_pending_next"
SETUP_SECRET_KEY = "staff_mfa_setup_secret"
VERIFIED_USER_KEY = "staff_mfa_verified_user"
RECOVERY_CODES_KEY = "staff_mfa_new_recovery_codes"


class OTPForm(forms.Form):
    code = forms.CharField(
        label="Authentication code",
        min_length=6,
        max_length=12,
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-lg text-center",
            "autocomplete": "one-time-code",
            "inputmode": "numeric",
            "autofocus": True,
            "placeholder": "Enter your code",
        }),
    )

    def clean_code(self):
        return "".join(self.cleaned_data["code"].split())


def begin_staff_mfa(request, user, backend, next_url=""):
    """Store only a short pending identity; no authenticated session exists yet."""
    request.session.cycle_key()
    request.session[PENDING_USER_KEY] = user.pk
    request.session[PENDING_BACKEND_KEY] = backend
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        request.session[PENDING_NEXT_KEY] = next_url
    else:
        request.session[PENDING_NEXT_KEY] = reverse("admin_dashboard")


def _pending_user(request):
    user_id = request.session.get(PENDING_USER_KEY)
    if not user_id:
        return None
    try:
        user = User.objects.get(pk=user_id, is_active=True)
    except User.DoesNotExist:
        clear_pending_staff_mfa(request)
        return None
    return user if can_access_store_management(user) else None


def clear_pending_staff_mfa(request):
    for key in (PENDING_USER_KEY, PENDING_BACKEND_KEY, PENDING_NEXT_KEY, SETUP_SECRET_KEY):
        request.session.pop(key, None)


def _complete_login(request, user):
    backend = request.session.get(PENDING_BACKEND_KEY)
    destination = request.session.get(PENDING_NEXT_KEY, reverse("admin_dashboard"))
    clear_pending_staff_mfa(request)
    login(request, user, backend=backend)
    request.session[VERIFIED_USER_KEY] = str(user.pk)
    request.session.cycle_key()
    return destination


def staff_mfa_is_verified(request):
    return bool(
        request.user.is_authenticated
        and request.session.get(VERIFIED_USER_KEY) == str(request.user.pk)
    )


@never_cache
@ratelimit(key="ip", rate="10/m", method="POST", block=True)
@require_http_methods(["GET", "POST"])
def staff_mfa_challenge(request):
    user = _pending_user(request)
    if not user:
        messages.warning(request, "Your secure sign-in session expired. Please sign in again.")
        return redirect("staff_login")

    authenticators = Authenticator.objects.filter(user=user).exclude(
        type=Authenticator.Type.WEBAUTHN
    )
    if not authenticators.filter(type=Authenticator.Type.TOTP).exists():
        return redirect("staff_mfa_setup")

    form = OTPForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        used = None
        for authenticator in authenticators:
            if authenticator.wrap().validate_code(form.cleaned_data["code"]):
                used = authenticator
                break
        if used:
            used.record_usage()
            destination = _complete_login(request, user)
            messages.success(request, "Identity verified. Welcome to the store portal.")
            return redirect(destination)
        form.add_error("code", "That code is incorrect, expired, or has already been used.")

    return render(request, "accounts/staff_mfa_challenge.html", {"form": form})


@never_cache
@ratelimit(key="ip", rate="6/m", method="POST", block=True)
@require_http_methods(["GET", "POST"])
def staff_mfa_setup(request):
    user = _pending_user(request)
    if not user:
        messages.warning(request, "Your secure sign-in session expired. Please sign in again.")
        return redirect("staff_login")
    if Authenticator.objects.filter(user=user, type=Authenticator.Type.TOTP).exists():
        return redirect("staff_mfa_challenge")

    secret = request.session.get(SETUP_SECRET_KEY)
    if not secret:
        secret = generate_totp_secret()
        request.session[SETUP_SECRET_KEY] = secret

    form = OTPForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if not validate_totp_code(secret, form.cleaned_data["code"]):
            form.add_error("code", "The code did not match. Check the phone clock and try again.")
        else:
            with transaction.atomic():
                locked_user = User.objects.select_for_update().get(pk=user.pk)
                if Authenticator.objects.filter(
                    user=locked_user, type=Authenticator.Type.TOTP
                ).exists():
                    messages.info(request, "MFA was already activated. Enter a current code.")
                    return redirect("staff_mfa_challenge")
                TOTP.activate(locked_user, secret)
                recovery = RecoveryCodes.activate(locked_user)
                codes = recovery.get_unused_codes()
                StaffSecurityEvent.objects.create(
                    actor=locked_user,
                    target=locked_user,
                    action=StaffSecurityEvent.ACTION_MFA_ENABLED,
                    details="Authenticator-app MFA enrolled during staff sign-in.",
                    ip_address=request.META.get("REMOTE_ADDR"),
                )
            request.session[RECOVERY_CODES_KEY] = codes
            _complete_login(request, user)
            return redirect("staff_mfa_recovery_codes")

    adapter = get_adapter()
    otp_url = adapter.build_totp_url(user, secret)
    qr_svg = adapter.build_totp_svg(otp_url)
    return render(request, "accounts/staff_mfa_setup.html", {
        "form": form,
        "secret": secret,
        "qr_svg": qr_svg,
        "issuer": settings.MFA_TOTP_ISSUER,
    })


@never_cache
def staff_mfa_recovery_codes(request):
    if not staff_mfa_is_verified(request):
        return redirect("staff_login")
    codes = request.session.pop(RECOVERY_CODES_KEY, None)
    if not codes:
        raise Http404("Recovery codes are only displayed once after MFA setup.")
    return render(request, "accounts/staff_mfa_recovery_codes.html", {"codes": codes})


@require_http_methods(["POST"])
def staff_mfa_cancel(request):
    clear_pending_staff_mfa(request)
    logout(request)
    messages.info(request, "Secure sign-in was cancelled.")
    return redirect("staff_login")
