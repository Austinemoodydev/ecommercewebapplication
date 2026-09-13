from django.contrib import admin
from django.contrib.admin.forms import AdminAuthenticationForm
from django.core.exceptions import ValidationError


class SuperuserOnlyAdminAuthenticationForm(
    AdminAuthenticationForm
):

    def confirm_login_allowed(self, user):

        super().confirm_login_allowed(user)

        if not user.is_superuser:

            raise ValidationError(
                (
                    "System administrator access only. "
                    "Store staff must use the Store Staff Login."
                ),
                code="not_system_administrator",
            )


def system_admin_has_permission(request):

    user = request.user

    return bool(
        user.is_authenticated
        and user.is_active
        and user.is_superuser
    )


def configure_system_admin_site():

    # Django normally allows any active is_staff user.
    # This project separates Store Staff from System Admin.
    admin.site.has_permission = (
        system_admin_has_permission
    )

    admin.site.login_form = (
        SuperuserOnlyAdminAuthenticationForm
    )
