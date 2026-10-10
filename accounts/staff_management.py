from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import user_passes_test
from django.db import models
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.views.decorators.http import require_POST

from .models import StaffSecurityEvent
from .staff_access import can_manage_staff, can_manage_staff_member
from .staff_forms import (
    StoreStaffCreateForm,
    StoreStaffUpdateForm,
)
from .store_roles import ROLE_DESCRIPTIONS, SENSITIVE_ROLES, STORE_ROLE_NAMES
from allauth.mfa.models import Authenticator


User = get_user_model()


def staff_admin_required(view_func):

    return user_passes_test(
        can_manage_staff,
        login_url="staff_login",
    )(
        view_func
    )


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return (forwarded.split(",")[0].strip() if forwarded
            else request.META.get("REMOTE_ADDR"))


def _record(request, target, action, details=""):
    StaffSecurityEvent.objects.create(
        actor=request.user, target=target, action=action,
        details=details, ip_address=_client_ip(request),
    )


def _revoke_sessions(user):
    for session in Session.objects.filter(expire_date__gte=timezone.now()):
        if str(session.get_decoded().get("_auth_user_id")) == str(user.pk):
            session.delete()


@staff_admin_required
def staff_list(request):

    staff = (
        User.objects
        .filter(
            is_staff=True,
            is_superuser=False,
        )
        .prefetch_related(
            "groups",
            models.Prefetch(
                "authenticator_set",
                queryset=Authenticator.objects.only("user_id", "type"),
                to_attr="mfa_authenticators",
            ),
        )
        .order_by(
            "first_name",
            "last_name",
            "username",
        )
    )

    for member in staff:
        member.may_be_managed = can_manage_staff_member(request.user, member)
        member.mfa_enabled = any(
            authenticator.type == Authenticator.Type.TOTP
            for authenticator in member.mfa_authenticators
        )

    return render(
        request,
        "accounts/staff_management/list.html",
        {
            "staff_members": staff,
            "store_role_names": STORE_ROLE_NAMES,
            "role_descriptions": ROLE_DESCRIPTIONS,
            "sensitive_roles": SENSITIVE_ROLES,
        },
    )


@staff_admin_required
def staff_create(request):

    if request.method == "POST":

        form = StoreStaffCreateForm(
            request.POST,
            actor=request.user,
        )

        if form.is_valid():

            user = form.save()
            role = form.cleaned_data["role_group"].name
            _record(request, user, StaffSecurityEvent.ACTION_CREATED, f"Assigned role: {role}")

            messages.success(
                request,
                (
                    f"Staff account "
                    f"{user.username} created."
                ),
            )

            return redirect(
                "staff_manage_list"
            )

    else:

        form = StoreStaffCreateForm(actor=request.user)


    return render(
        request,
        "accounts/staff_management/form.html",
        {
            "form": form,
            "title": "Add staff member",
            "submit_label": "Create staff account",
            "role_descriptions": ROLE_DESCRIPTIONS,
            "sensitive_roles": SENSITIVE_ROLES,
        },
    )


@staff_admin_required
def staff_edit(request, pk):

    user = get_object_or_404(
        User,
        pk=pk,
        is_staff=True,
        is_superuser=False,
    )

    if not can_manage_staff_member(request.user, user):
        messages.error(request, "You cannot manage this staff account.")
        return redirect("staff_manage_list")

    if request.method == "POST":

        form = StoreStaffUpdateForm(
            request.POST,
            instance=user,
            actor=request.user,
        )

        if form.is_valid():

            old_role = user.groups.filter(name__in=STORE_ROLE_NAMES).values_list("name", flat=True).first()
            was_active = user.is_active
            form.save()
            new_role = form.cleaned_data["role_group"].name
            if old_role != new_role:
                _record(
                    request, user, StaffSecurityEvent.ACTION_ROLE_CHANGED,
                    f"Role changed from {old_role or 'none'} to {new_role}.",
                )
            else:
                _record(
                    request, user, StaffSecurityEvent.ACTION_UPDATED,
                    "Profile information updated.",
                )
            if was_active != user.is_active:
                status_action = (
                    StaffSecurityEvent.ACTION_REACTIVATED if user.is_active
                    else StaffSecurityEvent.ACTION_SUSPENDED
                )
                _record(request, user, status_action, "Access changed while editing staff profile.")
                if not user.is_active:
                    _revoke_sessions(user)

            messages.success(
                request,
                (
                    f"{user.username} "
                    f"was updated."
                ),
            )

            return redirect(
                "staff_manage_list"
            )

    else:

        form = StoreStaffUpdateForm(
            instance=user,
            actor=request.user,
        )


    return render(
        request,
        "accounts/staff_management/form.html",
        {
            "form": form,
            "staff_member": user,
            "title": "Edit staff member",
            "submit_label": "Save changes",
            "role_descriptions": ROLE_DESCRIPTIONS,
            "sensitive_roles": SENSITIVE_ROLES,
        },
    )


@staff_admin_required
@require_POST
def staff_toggle_active(
    request,
    pk,
):

    user = get_object_or_404(
        User,
        pk=pk,
        is_staff=True,
        is_superuser=False,
    )

    if not can_manage_staff_member(request.user, user):

        messages.error(
            request,
            (
                "You cannot change access for this staff account."
            ),
        )

        return redirect(
            "staff_manage_list"
        )


    user.is_active = not user.is_active

    user.save(
        update_fields=[
            "is_active"
        ]
    )

    action = (StaffSecurityEvent.ACTION_REACTIVATED if user.is_active
              else StaffSecurityEvent.ACTION_SUSPENDED)
    _record(request, user, action, "Access changed from Staff Management.")
    if not user.is_active:
        _revoke_sessions(user)


    if user.is_active:

        message = (
            f"{user.username} was activated."
        )

    else:

        message = (
            f"{user.username} was deactivated."
        )


    messages.success(
        request,
        message,
    )

    return redirect(
        "staff_manage_list"
    )


@staff_admin_required
@require_POST
def staff_reset_mfa(request, pk):
    user = get_object_or_404(
        User,
        pk=pk,
        is_staff=True,
        is_superuser=False,
    )

    if not request.user.has_perm("accounts.reset_staff_mfa"):
        messages.error(request, "You do not have permission to reset staff MFA.")
        return redirect("staff_manage_list")

    if not can_manage_staff_member(request.user, user):
        messages.error(request, "You cannot reset MFA for this protected account.")
        return redirect("staff_manage_list")

    deleted, _ = Authenticator.objects.filter(user=user).delete()
    if deleted:
        _revoke_sessions(user)
        _record(
            request,
            user,
            StaffSecurityEvent.ACTION_MFA_RESET,
            "All authenticators and recovery codes removed; active sessions revoked.",
        )
        messages.success(
            request,
            f"MFA was reset for {user.username}. They must enroll again at next sign-in.",
        )
    else:
        messages.info(request, f"{user.username} has not enrolled in MFA yet.")

    return redirect("staff_manage_list")
