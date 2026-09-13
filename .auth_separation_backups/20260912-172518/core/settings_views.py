from django.contrib import messages

from django.contrib.admin.views.decorators import (
    staff_member_required,
)

from django.shortcuts import (
    redirect,
    render,
)

from django.views.decorators.http import (
    require_http_methods,
)

from .forms import StoreSettingsForm

from .store_settings import (
    get_store_settings,
)


@staff_member_required
@require_http_methods(
    [
        "GET",
        "POST",
    ]
)
def admin_store_settings(
    request,
):

    settings_obj = (
        get_store_settings()
    )


    form = StoreSettingsForm(
        request.POST or None,
        instance=settings_obj,
    )


    if (
        request.method == "POST"
        and form.is_valid()
    ):

        store_settings = (
            form.save(
                commit=False
            )
        )

        store_settings.updated_by = (
            request.user
        )

        store_settings.save()


        messages.success(
            request,
            "Store settings updated successfully.",
        )


        return redirect(
            "admin_store_settings"
        )


    return render(
        request,
        "dashboard/admin/settings.html",
        {
            "form":
                form,

            "store_settings":
                settings_obj,
        },
    )
