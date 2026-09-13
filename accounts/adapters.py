from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import redirect


class CustomerOnlySocialAccountAdapter(
    DefaultSocialAccountAdapter
):

    """
    Social login is customer-only.

    Staff and superusers must use their
    dedicated authentication entrances.
    """

    def _existing_user_for_social_login(
        self,
        sociallogin,
    ):

        user = sociallogin.user

        if getattr(user, "pk", None):
            return user

        email = (
            getattr(user, "email", "")
            or ""
        ).strip()

        if not email:

            email = (
                sociallogin
                .account
                .extra_data
                .get("email", "")
                or ""
            ).strip()

        if not email:
            return None

        User = get_user_model()

        return User.objects.filter(
            email__iexact=email
        ).first()


    def pre_social_login(
        self,
        request,
        sociallogin,
    ):

        super().pre_social_login(
            request,
            sociallogin,
        )

        existing = (
            self._existing_user_for_social_login(
                sociallogin
            )
        )

        if existing and (
            existing.is_staff
            or existing.is_superuser
            or getattr(
                existing,
                "role",
                None,
            ) == "admin"
        ):

            messages.error(
                request,
                (
                    "This email belongs to a staff or "
                    "system administrator account. "
                    "For security, privileged accounts "
                    "cannot use customer Google sign-in. "
                    "Use the appropriate staff/admin portal, "
                    "or use a separate customer account "
                    "for shopping."
                ),
            )

            raise ImmediateHttpResponse(
                redirect("login")
            )


    def save_user(
        self,
        request,
        sociallogin,
        form=None,
    ):

        user = super().save_user(
            request,
            sociallogin,
            form=form,
        )

        # Google has verified the Google
        # account email. Keep this project's
        # custom verification flag synchronized.
        if (
            sociallogin.account.provider
            == "google"
            and user.email
            and not user.email_verified
        ):

            user.email_verified = True

            user.save(
                update_fields=[
                    "email_verified",
                ]
            )

        return user
