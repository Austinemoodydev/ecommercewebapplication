from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.db.models import Count
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.staff_auth import staff_member_required
from notifications.tasks import _get_sms_client, _normalise_phone

from .campaigns import campaign_recipients
from .forms import CampaignTestMessageForm, MarketingCampaignForm
from .models import CampaignAuditEvent, MarketingCampaign
from .tasks import dispatch_campaign


def _allowed(request, permission):
    return request.user.is_superuser or request.user.has_perm(permission)


def _audit(campaign, request, action, details=""):
    CampaignAuditEvent.objects.create(
        campaign=campaign,
        actor=request.user,
        action=action,
        details=details,
    )


@staff_member_required
def campaign_list(request):
    if not _allowed(request, "core.view_marketingcampaign"):
        return HttpResponseForbidden("You do not have permission to view campaigns.")
    campaigns = MarketingCampaign.objects.select_related("coupon", "approved_by")
    return render(request, "dashboard/admin/campaigns/list.html", {"campaigns": campaigns})


@staff_member_required
def campaign_create(request):
    if not _allowed(request, "core.add_marketingcampaign"):
        return HttpResponseForbidden("You do not have permission to create campaigns.")
    form = MarketingCampaignForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        campaign = form.save(commit=False)
        campaign.created_by = request.user
        campaign.updated_by = request.user
        campaign.save()
        form.save_m2m()
        _audit(campaign, request, "created")
        messages.success(request, "Campaign saved as an unapproved draft.")
        return redirect("campaign_detail", pk=campaign.pk)
    return render(request, "dashboard/admin/campaigns/form.html", {"form": form, "title": "Create Campaign"})


@staff_member_required
def campaign_edit(request, pk):
    campaign = get_object_or_404(MarketingCampaign, pk=pk)
    if not _allowed(request, "core.change_marketingcampaign"):
        return HttpResponseForbidden("You do not have permission to edit campaigns.")
    form = MarketingCampaignForm(request.POST or None, request.FILES or None, instance=campaign)
    if request.method == "POST" and form.is_valid():
        campaign = form.save(commit=False)
        campaign.updated_by = request.user
        campaign.approved_at = None
        campaign.approved_by = None
        campaign.dispatched_at = None
        campaign.save()
        form.save_m2m()
        _audit(campaign, request, "edited", "Approval cleared because campaign content changed.")
        messages.success(request, "Campaign updated. It must be approved again before publication.")
        return redirect("campaign_detail", pk=campaign.pk)
    return render(request, "dashboard/admin/campaigns/form.html", {"form": form, "title": "Edit Campaign", "campaign": campaign})


@staff_member_required
def campaign_detail(request, pk):
    if not _allowed(request, "core.view_marketingcampaign"):
        return HttpResponseForbidden("You do not have permission to view campaigns.")
    campaign = get_object_or_404(
        MarketingCampaign.objects.select_related("coupon", "approved_by").prefetch_related(
            "products", "categories", "audit_events__actor"
        ),
        pk=pk,
    )
    return render(
        request,
        "dashboard/admin/campaigns/detail.html",
        {
            "campaign": campaign,
            "recipient_count": campaign_recipients(campaign).count(),
            "test_form": CampaignTestMessageForm(),
            "delivery_counts": dict(
                campaign.deliveries.values_list("status").annotate(total=Count("id"))
            ) if campaign.pk else {},
        },
    )


@require_POST
@staff_member_required
def campaign_approve(request, pk):
    campaign = get_object_or_404(MarketingCampaign, pk=pk)
    if not _allowed(request, "core.publish_marketingcampaign"):
        return HttpResponseForbidden("You do not have permission to publish campaigns.")
    campaign.full_clean()
    campaign.approved_at = timezone.now()
    campaign.approved_by = request.user
    campaign.save(update_fields=["approved_at", "approved_by", "updated_at"])
    _audit(campaign, request, "approved")
    messages.success(request, "Campaign approved. Website publication follows its schedule.")
    return redirect("campaign_detail", pk=pk)


@require_POST
@staff_member_required
def campaign_disable(request, pk):
    campaign = get_object_or_404(MarketingCampaign, pk=pk)
    if not _allowed(request, "core.publish_marketingcampaign"):
        return HttpResponseForbidden("You do not have permission to disable campaigns.")
    campaign.is_enabled = False
    campaign.save(update_fields=["is_enabled", "updated_at"])
    _audit(campaign, request, "disabled")
    messages.success(request, "Campaign disabled everywhere immediately.")
    return redirect("campaign_detail", pk=pk)


@require_POST
@staff_member_required
def campaign_send(request, pk):
    campaign = get_object_or_404(MarketingCampaign, pk=pk)
    if not _allowed(request, "core.send_marketingcampaign"):
        return HttpResponseForbidden("You do not have permission to send campaigns.")
    if request.POST.get("confirm") != "SEND":
        messages.error(request, "Type SEND to confirm bulk communication.")
        return redirect("campaign_detail", pk=pk)
    if not campaign.approved_at or not campaign.is_enabled:
        messages.error(request, "Approve and enable the campaign before sending it.")
        return redirect("campaign_detail", pk=pk)
    try:
        dispatch_campaign.delay(campaign.pk)
    except Exception:
        messages.error(
            request,
            "Campaign delivery could not be queued. Check that Redis and the Celery worker are running.",
        )
        return redirect("campaign_detail", pk=pk)
    _audit(campaign, request, "bulk_send_queued", f"Audience estimate: {campaign_recipients(campaign).count()}")
    messages.success(request, "Campaign delivery has been queued.")
    return redirect("campaign_detail", pk=pk)


@require_POST
@staff_member_required
def campaign_test_message(request, pk):
    campaign = get_object_or_404(MarketingCampaign, pk=pk)
    if not _allowed(request, "core.send_marketingcampaign"):
        return HttpResponseForbidden("You do not have permission to test campaign delivery.")
    form = CampaignTestMessageForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Enter a valid test email address or phone number.")
        return redirect("campaign_detail", pk=pk)
    try:
        if form.cleaned_data.get("email"):
            send_mail(campaign.headline, campaign.message, settings.DEFAULT_FROM_EMAIL, [form.cleaned_data["email"]])
        if form.cleaned_data.get("phone"):
            _get_sms_client().send(campaign.message[:480], [_normalise_phone(form.cleaned_data["phone"])])
    except Exception:
        messages.error(request, "Test delivery failed. Check the configured email or SMS provider.")
    else:
        _audit(campaign, request, "test_sent")
        messages.success(request, "Test message sent successfully.")
    return redirect("campaign_detail", pk=pk)
