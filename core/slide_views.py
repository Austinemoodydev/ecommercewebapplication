from django.contrib import messages
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.staff_auth import staff_member_required

from .forms import HomepageSlideForm
from .models import HomepageSlide


def _allowed(request, permission):
    return request.user.is_superuser or request.user.has_perm(permission)


@staff_member_required
def slide_list(request):
    if not _allowed(request, "core.view_homepageslide"):
        return HttpResponseForbidden("You do not have permission to view homepage banners.")
    return render(
        request,
        "dashboard/admin/homepage_slides/list.html",
        {"slides": HomepageSlide.objects.select_related("category", "product")},
    )


@staff_member_required
def slide_create(request):
    if not _allowed(request, "core.add_homepageslide"):
        return HttpResponseForbidden("You do not have permission to add homepage banners.")
    form = HomepageSlideForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        slide = form.save()
        messages.success(request, f'Banner "{slide.internal_name}" was added successfully.')
        return redirect("homepage_slide_list")
    return render(request, "dashboard/admin/homepage_slides/form.html", {"form": form, "title": "Add homepage banner"})


@staff_member_required
def slide_edit(request, pk):
    if not _allowed(request, "core.change_homepageslide"):
        return HttpResponseForbidden("You do not have permission to edit homepage banners.")
    slide = get_object_or_404(HomepageSlide, pk=pk)
    form = HomepageSlideForm(request.POST or None, request.FILES or None, instance=slide)
    if request.method == "POST" and form.is_valid():
        slide = form.save()
        messages.success(request, f'Banner "{slide.internal_name}" was updated successfully.')
        return redirect("homepage_slide_list")
    return render(request, "dashboard/admin/homepage_slides/form.html", {"form": form, "title": "Edit homepage banner", "slide": slide})


@require_POST
@staff_member_required
def slide_toggle(request, pk):
    if not _allowed(request, "core.change_homepageslide"):
        return HttpResponseForbidden("You do not have permission to change homepage banners.")
    slide = get_object_or_404(HomepageSlide, pk=pk)
    slide.is_enabled = not slide.is_enabled
    slide.save(update_fields=["is_enabled", "updated_at"])
    state = "enabled" if slide.is_enabled else "disabled"
    messages.success(request, f'Banner "{slide.internal_name}" was {state}.')
    return redirect("homepage_slide_list")
