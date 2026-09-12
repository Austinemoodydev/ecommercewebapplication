from django.db import transaction
from django.db.models.signals import (
    post_save,
)

from django.dispatch import receiver

from payments.models import (
    RefundRequest,
)


@receiver(
    post_save,
    sender=RefundRequest,
)
def create_credit_note_for_processed_refund(
    sender,
    instance,
    **kwargs,
):

    """
    Automatically issue the immutable credit note once a
    refund has genuinely reached 'processed'.

    Important:
    - requested/approved/rejected refunds create nothing;
    - an external refund reference is required;
    - get_or_issue_credit_note() is idempotent;
    - repeated saves cannot create duplicate credit notes.
    """

    if instance.status != "processed":
        return


    if not (
        instance.external_reference
        or ""
    ).strip():

        return


    # Local import avoids application-loading circular imports.
    from orders.credit_note_service import (
        get_or_issue_credit_note,
    )


    from orders.models import (
        CreditNoteDocument,
    )


    existed_before = (
        CreditNoteDocument.objects
        .filter(
            refund_request=instance
        )
        .exists()
    )


    document = get_or_issue_credit_note(
        refund=instance,
        issued_by=instance.processed_by,
    )


    # Only the first successful issuance creates the
    # "credit note issued" notification event.
    if not existed_before:

        def queue_credit_note_notification():

            try:

                from notifications.tasks import (
                    send_credit_note_issued_notification,
                )


                send_credit_note_issued_notification.delay(
                    document.pk
                )

            except Exception:

                # Broker problems must never roll back or
                # invalidate an already processed refund.
                pass


        transaction.on_commit(
            queue_credit_note_notification,
            robust=True,
        )
