from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .staff_access import can_access_store_management
from django.contrib.auth import get_user_model
from django.contrib.auth.views import LoginView
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from django.shortcuts import get_object_or_404, redirect, render
from django.http import Http404
from django.db import transaction
from django.contrib import messages

from .forms import RegisterForm, AddressForm, ProfileForm
from .models import Address

from orders.models import Order

from orders.guest_access import (
    verify_guest_access_token,
)


PENDING_GUEST_ORDER_KEY = (
    "pending_guest_order_claim"
)



def _get_guest_order_for_claim(
    order_number,
    token,
    *,
    lock=False,
):

    queryset = Order.objects


    if lock:

        queryset = (
            queryset.select_for_update()
        )


    order = get_object_or_404(
        queryset,
        order_number=order_number,
        user__isnull=True,
        guest_checkout=True,
    )


    if not verify_guest_access_token(
        order,
        token,
    ):

        raise Http404(
            "Order not found."
        )


    return order



def _store_pending_guest_claim(
    request,
    order_number,
    token,
):

    # Validate BEFORE storing anything
    # in the session.

    _get_guest_order_for_claim(
        order_number,
        token,
    )


    request.session[
        PENDING_GUEST_ORDER_KEY
    ] = {
        "order_number": order_number,
        "token": token,
    }


    request.session.modified = True



@transaction.atomic
def _claim_guest_order(
    user,
    order_number,
    token,
):

    order = _get_guest_order_for_claim(
        order_number,
        token,
        lock=True,
    )


    # Account must be active and email
    # verified before ownership transfer.

    if (
        not user.is_active
        or
        not user.email_verified
    ):

        raise PermissionError(
            "Verify your email before "
            "linking this order."
        )


    order.user = user

    order.guest_checkout = False

    # Destroy the guest credential.
    # The old private URL stops working
    # immediately after this commit.

    order.guest_access_token_hash = ""


    order.save(
        update_fields=[
            "user",
            "guest_checkout",
            "guest_access_token_hash",
            "updated_at",
        ]
    )


    return order



def _claim_pending_order_if_possible(
    request,
    user,
):

    pending = request.session.get(
        PENDING_GUEST_ORDER_KEY
    )


    if not pending:

        return None


    order_number = pending.get(
        "order_number"
    )

    token = pending.get(
        "token"
    )


    if not order_number or not token:

        request.session.pop(
            PENDING_GUEST_ORDER_KEY,
            None,
        )

        return None


    try:

        order = _claim_guest_order(
            user,
            order_number,
            token,
        )

    except (
        Http404,
        PermissionError,
    ):

        return None


    request.session.pop(
        PENDING_GUEST_ORDER_KEY,
        None,
    )


    return order



def register(request):

    claim_order = request.GET.get(
        "claim_order"
    )

    claim_token = request.GET.get(
        "claim_token"
    )


    if claim_order and claim_token:

        _store_pending_guest_claim(
            request,
            claim_order,
            claim_token,
        )


    form = RegisterForm(
        request.POST or None
    )
    if request.method == "POST":
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.email_verified = False
            user.save()
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            verification_url = request.build_absolute_uri(
                reverse("verify_email", kwargs={"uidb64": uid, "token": default_token_generator.make_token(user)})
            )
            send_mail(
                "Verify your OnlineShop email",
                f"Open this link to verify your email address:\n{verification_url}",
                None,
                [user.email],
            )
            return redirect("login")
    return render(
        request,
        "accounts/register.html",
        {
            "form": form
        }
    )


@login_required
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

        if email_changed:
            # A verified status belongs to the old address,
            # never automatically to a replacement address.
            user.email_verified = False

        user.save()

        if email_changed:
            messages.warning(
                request,
                (
                    "Your email address changed. "
                    "The new address must be verified "
                    "before it is treated as verified."
                ),
            )
        else:
            messages.success(
                request,
                "Profile updated successfully.",
            )

        return redirect("profile")

    return render(
        request,
        "accounts/profile.html",
        {"form": form},
    )


def verify_email(request, uidb64, token):
    try:
        user = get_user_model().objects.get(pk=force_str(urlsafe_base64_decode(uidb64)))
    except (TypeError, ValueError, OverflowError, get_user_model().DoesNotExist):
        user = None

    if user is None or not default_token_generator.check_token(user, token):
        return render(request, "accounts/verify_email.html", {"verified": False})

    user.is_active = True
    user.email_verified = True

    user.save(
        update_fields=[
            "is_active",
            "email_verified",
        ]
    )


    claimed_order = (
        _claim_pending_order_if_possible(
            request,
            user,
        )
    )


    return render(
        request,
        "accounts/verify_email.html",
        {
            "verified": True,
            "claimed_order":
                claimed_order,
        },
    )


@login_required
def addresses(request):

    user_addresses = Address.objects.filter(user=request.user)

    return render(
        request,
        "accounts/dashboard/addresses.html",
        {
            "addresses": user_addresses,
        },
    )


@login_required
def add_address(request):

    form = AddressForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user

            if address.is_default:
                Address.objects.filter(user=request.user).update(is_default=False)

            address.save()
            return redirect("addresses")

    return render(
        request,
        "accounts/dashboard/address_form.html",
        {
            "form": form,
        },
    )


@login_required
@require_POST
def delete_address(request, address_id):

    address = get_object_or_404(
        Address,
        id=address_id,
        user=request.user,
    )

    address.delete()

    return redirect("addresses")


@login_required
@require_POST
@transaction.atomic
def set_default_address(request, address_id):

    address = get_object_or_404(
        Address,
        id=address_id,
        user=request.user,
    )

    Address.objects.filter(
        user=request.user
    ).update(
        is_default=False
    )

    address.is_default = True
    address.save(
        update_fields=["is_default"]
    )

    return redirect("addresses")




@method_decorator(ratelimit(key="ip", rate="5/m", method="POST", block=True), name="post")
class RateLimitedLoginView(LoginView):
    template_name = "accounts/login.html"

    def form_valid(self, form):

        user = form.get_user()

        if (
            user.is_staff
            or user.is_superuser
            or getattr(
                user,
                "role",
                None,
            ) == "admin"
        ):

            form.add_error(
                None,
                (
                    "Store staff and system "
                    "administrators must use "
                    "their dedicated login."
                ),
            )

            return self.form_invalid(form)

        return super().form_valid(form)


@method_decorator(
    ratelimit(
        key="ip",
        rate="5/m",
        method="POST",
        block=True,
    ),
    name="dispatch",
)
class StoreStaffLoginView(LoginView):

    template_name = "accounts/staff_login.html"

    def form_valid(self, form):

        user = form.get_user()

        if user.is_superuser:

            form.add_error(
                None,
                (
                    "System administrators must use "
                    "the System Admin login."
                ),
            )

            return self.form_invalid(form)

        if not can_access_store_management(user):

            form.add_error(
                None,
                (
                    "Your account does not have "
                    "an authorized store staff role."
                ),
            )

            return self.form_invalid(form)

        return super().form_valid(form)

    def get_success_url(self):

        return reverse(
            "admin_dashboard"
        )


@ratelimit(
    key="ip",
    rate="10/m",
    method="POST",
    block=True,
)
def claim_guest_order(
    request,
    order_number,
    token,
):

    order = _get_guest_order_for_claim(
        order_number,
        token,
    )


    if not request.user.is_authenticated:

        _store_pending_guest_claim(
            request,
            order_number,
            token,
        )


        if request.method == "POST":

            return redirect(
                (
                    f"{reverse('login')}"
                    f"?next="
                    f"{reverse('claim_guest_order', args=[order_number, token])}"
                )
            )


        return render(
            request,
            "accounts/claim_guest_order.html",
            {
                "order": order,
                "guest_access_token":
                    token,
            },
        )


    if not request.user.email_verified:

        messages.error(
            request,
            (
                "Verify your account email "
                "before linking this order."
            ),
        )


        return render(
            request,
            "accounts/claim_guest_order.html",
            {
                "order": order,
                "guest_access_token":
                    token,
                "requires_verification":
                    True,
            },
            status=403,
        )


    if request.method != "POST":

        return render(
            request,
            "accounts/claim_guest_order.html",
            {
                "order": order,
                "guest_access_token":
                    token,
            },
        )


    try:

        claimed_order = (
            _claim_guest_order(
                request.user,
                order_number,
                token,
            )
        )

    except PermissionError:

        return render(
            request,
            "accounts/claim_guest_order.html",
            {
                "order": order,
                "guest_access_token":
                    token,
                "requires_verification":
                    True,
            },
            status=403,
        )


    request.session.pop(
        PENDING_GUEST_ORDER_KEY,
        None,
    )


    messages.success(
        request,
        (
            f"Order "
            f"{claimed_order.order_number} "
            "has been linked to your account."
        ),
    )


    return redirect(
        "order_detail",
        order_number=(
            claimed_order.order_number
        ),
    )

