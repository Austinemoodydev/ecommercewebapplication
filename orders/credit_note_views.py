from django.conf import settings
from django.contrib import messages

from django.contrib.admin.views.decorators import (
    staff_member_required,
)

from django.contrib.auth.decorators import (
    login_required,
)

from django.core.mail import send_mail

from django.db.models import F

from django.http import Http404

from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from django.utils import timezone

from django.views.decorators.http import (
    require_POST,
)

from orders.credit_note_service import (
    get_or_issue_credit_note,
)

from orders.models import (
    CreditNoteDocument,
)

from payments.models import (
    RefundRequest,
)


def _render_credit_note(
    request,
    document,
):

    return render(
        request,
        "orders/documents/credit_note.html",
        {
            "document":
                document,

            "snapshot":
                document.snapshot,

            "order":
                document.order,

            "is_credit_note":
                True,

            "credit_note_email_url_name":
                (
                    "admin_credit_note_email"
                    if request.user.is_staff
                    else
                    "customer_credit_note_email"
                ),
        },
    )


def _customer_refund(
    request,
    refund_id,
):

    return get_object_or_404(
        RefundRequest.objects
        .select_related(
            "order",
            "processed_by",
        ),
        pk=refund_id,
        order__user=request.user,
        status="processed",
    )


def _admin_refund(
    refund_id,
):

    return get_object_or_404(
        RefundRequest.objects
        .select_related(
            "order",
            "processed_by",
        ),
        pk=refund_id,
        status="processed",
    )


@login_required
def customer_credit_note(
    request,
    refund_id,
):

    refund = _customer_refund(
        request,
        refund_id,
    )


    try:

        document = (
            get_or_issue_credit_note(
                refund=refund,
                issued_by=request.user,
            )
        )

    except ValueError:
        raise Http404


    return _render_credit_note(
        request,
        document,
    )


@staff_member_required
def admin_credit_note(
    request,
    refund_id,
):

    refund = _admin_refund(
        refund_id
    )


    try:

        document = (
            get_or_issue_credit_note(
                refund=refund,
                issued_by=request.user,
            )
        )

    except ValueError:
        raise Http404


    return _render_credit_note(
        request,
        document,
    )


def _credit_note_url(
    request,
    document,
):

    from django.urls import reverse


    route = (
        "admin_credit_note"
        if request.user.is_staff
        else "customer_credit_note"
    )


    return reverse(
        route,
        args=[
            document.refund_request_id
        ],
    )


def _send_credit_note_email(
    request,
    document,
):

    snapshot = document.snapshot

    recipient = (
        snapshot[
            "order"
        ]
        .get(
            "email",
            "",
        )
        .strip()
    )


    if not recipient:

        messages.error(
            request,
            "This order has no customer "
            "email address.",
        )

        return


    url = (
        request.build_absolute_uri(
            _credit_note_url(
                request,
                document,
            )
        )
    )


    subject = (
        f"Credit Note "
        f"{document.document_number}"
    )


    body = (
        f"Hello "
        f"{snapshot['order']['full_name']},\n\n"

        f"A refund credit note has been "
        f"issued for order "
        f"{snapshot['order']['order_number']}.\n\n"

        f"Credit note: "
        f"{document.document_number}\n"

        f"Refund amount: KES "
        f"{snapshot['refund']['amount']}\n"

        f"Refund reference: "
        f"{snapshot['refund']['external_reference']}\n\n"

        f"View credit note:\n"
        f"{url}\n"
    )


    send_mail(
        subject=subject,
        message=body,

        from_email=getattr(
            settings,
            "DEFAULT_FROM_EMAIL",
            None,
        ),

        recipient_list=[
            recipient
        ],

        fail_silently=False,
    )


    (
        CreditNoteDocument.objects
        .filter(
            pk=document.pk
        )
        .update(
            email_count=(
                F("email_count")
                + 1
            ),

            last_emailed_at=(
                timezone.now()
            ),
        )
    )


    messages.success(
        request,
        "Credit note emailed successfully.",
    )


@login_required
@require_POST
def customer_credit_note_email(
    request,
    refund_id,
):

    refund = _customer_refund(
        request,
        refund_id,
    )


    try:

        document = (
            get_or_issue_credit_note(
                refund=refund,
                issued_by=request.user,
            )
        )

    except ValueError:
        raise Http404


    _send_credit_note_email(
        request,
        document,
    )


    return redirect(
        _credit_note_url(
            request,
            document,
        )
    )


@staff_member_required
@require_POST
def admin_credit_note_email(
    request,
    refund_id,
):

    refund = _admin_refund(
        refund_id
    )


    try:

        document = (
            get_or_issue_credit_note(
                refund=refund,
                issued_by=request.user,
            )
        )

    except ValueError:
        raise Http404


    _send_credit_note_email(
        request,
        document,
    )


    return redirect(
        _credit_note_url(
            request,
            document,
        )
    )
