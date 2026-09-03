from django.contrib.auth.decorators import login_required
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

from .forms import RegisterForm, AddressForm, ProfileForm
from .models import Address


def register(request):
    form = RegisterForm(request.POST or None)
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
    form = ProfileForm(request.POST or None, request.FILES or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("profile")
    return render(request, "accounts/profile.html", {"form": form})


def verify_email(request, uidb64, token):
    try:
        user = get_user_model().objects.get(pk=force_str(urlsafe_base64_decode(uidb64)))
    except (TypeError, ValueError, OverflowError, get_user_model().DoesNotExist):
        user = None

    if user is None or not default_token_generator.check_token(user, token):
        return render(request, "accounts/verify_email.html", {"verified": False})

    user.is_active = True
    user.email_verified = True
    user.save(update_fields=["is_active", "email_verified"])
    return render(request, "accounts/verify_email.html", {"verified": True})


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
def delete_address(request, address_id):

    address = get_object_or_404(Address, id=address_id, user=request.user)
    address.delete()

    return redirect("addresses")


@login_required
def set_default_address(request, address_id):

    address = get_object_or_404(Address, id=address_id, user=request.user)

    Address.objects.filter(user=request.user).update(is_default=False)

    address.is_default = True
    address.save()

    return redirect("addresses")




@method_decorator(ratelimit(key="ip", rate="5/m", method="POST", block=True), name="post")
class RateLimitedLoginView(LoginView):
    template_name = "accounts/login.html"
