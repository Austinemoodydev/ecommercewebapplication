from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.views.decorators.http import require_POST

from .staff_access import is_store_owner
from .staff_forms import (
    StoreStaffCreateForm,
    StoreStaffUpdateForm,
)
from .store_roles import STORE_ROLE_NAMES


User = get_user_model()


def owner_required(view_func):

    return user_passes_test(
        is_store_owner,
        login_url="staff_login",
    )(
        view_func
    )


@owner_required
def staff_list(request):

    staff = (
        User.objects
        .filter(
            is_staff=True,
            is_superuser=False,
        )
        .prefetch_related(
            "groups"
        )
        .order_by(
            "first_name",
            "last_name",
            "username",
        )
    )

    return render(
        request,
        "accounts/staff_management/list.html",
        {
            "staff_members": staff,
            "store_role_names": STORE_ROLE_NAMES,
        },
    )


@owner_required
def staff_create(request):

    if request.method == "POST":

        form = StoreStaffCreateForm(
            request.POST
        )

        if form.is_valid():

            user = form.save()

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

        form = StoreStaffCreateForm()


    return render(
        request,
        "accounts/staff_management/form.html",
        {
            "form": form,
            "title": "Add staff member",
            "submit_label": "Create staff account",
        },
    )


@owner_required
def staff_edit(request, pk):

    user = get_object_or_404(
        User,
        pk=pk,
        is_staff=True,
        is_superuser=False,
    )

    if request.method == "POST":

        form = StoreStaffUpdateForm(
            request.POST,
            instance=user,
        )

        if form.is_valid():

            form.save()

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
            instance=user
        )


    return render(
        request,
        "accounts/staff_management/form.html",
        {
            "form": form,
            "staff_member": user,
            "title": "Edit staff member",
            "submit_label": "Save changes",
        },
    )


@owner_required
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

    if user.pk == request.user.pk:

        messages.error(
            request,
            (
                "You cannot deactivate "
                "your own account."
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
