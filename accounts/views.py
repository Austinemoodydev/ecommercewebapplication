from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from django.shortcuts import get_object_or_404, redirect, render

from .forms import RegisterForm, AddressForm
from .models import Address


def register(request):
    form = RegisterForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            return redirect("login")
    return render(
        request,
        "accounts/register.html",
        {
            "form": form
        }
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
