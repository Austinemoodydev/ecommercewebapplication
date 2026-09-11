from pathlib import Path
import re
import shutil

ROOT = Path.cwd()

MODELS = ROOT / "payments" / "models.py"
URLS = ROOT / "payments" / "urls.py"
BASE = ROOT / "templates" / "dashboard" / "admin" / "base.html"
CUSTOMER_ORDER = ROOT / "templates" / "dashboard" / "order_detail.html"

PAYMENTS = ROOT / "payments"
TEMPLATES = (
    PAYMENTS
    / "templates"
    / "dashboard"
    / "admin"
    / "returns"
)

TEMPLATES.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# BACKUPS
# ============================================================

for path in [
    MODELS,
    URLS,
    BASE,
    CUSTOMER_ORDER,
]:

    if path.exists():

        backup = Path(
            str(path) + ".phase8abackup"
        )

        if not backup.exists():

            shutil.copy2(
                path,
                backup,
            )


# ============================================================
# 1. EXTEND RETURN / REFUND MODELS
# ============================================================

text = MODELS.read_text(
    encoding="utf-8-sig"
)


# ------------------------------------------------------------
# Add settings import
# ------------------------------------------------------------

if "from django.conf import settings" not in text:

    text = (
        "from django.conf import settings\n"
        + text
    )


# ------------------------------------------------------------
# Refund workflow fields
# ------------------------------------------------------------

if "processed_by = models.ForeignKey(" not in text.split("class RefundRequest")[1].split("class ReturnRequest")[0]:

    marker = '''    staff_note = models.TextField(blank=True)
'''

    addition = '''    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="processed_refunds",
    )

    processed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

'''

    refund_start = text.index(
        "class RefundRequest"
    )

    return_start = text.index(
        "class ReturnRequest"
    )

    before = text[:refund_start]
    refund_block = text[
        refund_start:return_start
    ]
    after = text[return_start:]

    if marker not in refund_block:

        raise RuntimeError(
            "Could not locate RefundRequest staff_note."
        )

    refund_block = refund_block.replace(
        marker,
        marker + addition,
        1,
    )

    text = (
        before
        + refund_block
        + after
    )


# ------------------------------------------------------------
# Return workflow fields
# ------------------------------------------------------------

return_part = text[
    text.index("class ReturnRequest"):
]

if "inventory_restored =" not in return_part:

    marker = '''    staff_note = models.TextField(blank=True)
'''

    addition = '''    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="processed_returns",
    )

    received_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    inventory_restored = models.BooleanField(
        default=False,
    )

'''

    pos = text.index(
        "class ReturnRequest"
    )

    before = text[:pos]
    block = text[pos:]

    if marker not in block:

        raise RuntimeError(
            "Could not locate ReturnRequest staff_note."
        )

    block = block.replace(
        marker,
        marker + addition,
        1,
    )

    text = before + block


# ------------------------------------------------------------
# ReturnRequestItem + audit event
# ------------------------------------------------------------

if "class ReturnRequestItem(" not in text:

    text += r'''


class ReturnRequestItem(models.Model):

    return_request = models.ForeignKey(
        ReturnRequest,
        on_delete=models.CASCADE,
        related_name="items",
    )

    order_item = models.ForeignKey(
        "orders.OrderItem",
        on_delete=models.PROTECT,
        related_name="return_request_items",
    )

    quantity = models.PositiveIntegerField()

    restock = models.BooleanField(
        default=False,
        help_text=(
            "Enable only when the returned item "
            "is suitable for resale."
        ),
    )

    class Meta:
        ordering = ["id"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "return_request",
                    "order_item",
                ],
                name=(
                    "unique_item_per_return_request"
                ),
            ),
        ]

    def clean(self):

        from django.core.exceptions import (
            ValidationError,
        )

        if not self.return_request_id:
            return

        if not self.order_item_id:
            return

        if (
            self.order_item.order_id
            != self.return_request.order_id
        ):

            raise ValidationError(
                "Returned item must belong "
                "to this order."
            )

        if self.quantity <= 0:

            raise ValidationError(
                "Return quantity must be "
                "greater than zero."
            )

        if (
            self.quantity
            > self.order_item.quantity
        ):

            raise ValidationError(
                "Return quantity cannot exceed "
                "the purchased quantity."
            )

    def save(
        self,
        *args,
        **kwargs,
    ):

        self.full_clean()

        return super().save(
            *args,
            **kwargs,
        )

    def __str__(self):

        return (
            f"{self.order_item.product_name} "
            f"x {self.quantity}"
        )


class ReturnRefundEvent(models.Model):

    refund = models.ForeignKey(
        RefundRequest,
        on_delete=models.CASCADE,
        related_name="events",
        null=True,
        blank=True,
    )

    return_request = models.ForeignKey(
        ReturnRequest,
        on_delete=models.CASCADE,
        related_name="events",
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=50,
    )

    message = models.TextField(
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="return_refund_events",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        ordering = [
            "created_at",
            "id",
        ]

    def clean(self):

        from django.core.exceptions import (
            ValidationError,
        )

        linked = int(
            bool(self.refund_id)
        ) + int(
            bool(self.return_request_id)
        )

        if linked != 1:

            raise ValidationError(
                "An event must belong to exactly "
                "one refund or return request."
            )

    def save(
        self,
        *args,
        **kwargs,
    ):

        self.full_clean()

        return super().save(
            *args,
            **kwargs,
        )

    def __str__(self):

        return self.status
'''

MODELS.write_text(
    text,
    encoding="utf-8",
)

print(
    "Return/refund models upgraded."
)


# ============================================================
# 2. CUSTOMER RETURN/REFUND VIEWS
# ============================================================

customer_views = PAYMENTS / "customer_returns.py"

customer_views.write_text(
r'''
from decimal import Decimal

from django.contrib.auth.decorators import (
    login_required,
)

from django.db import transaction

from django.db.models import Sum

from django.http import JsonResponse

from django.shortcuts import (
    get_object_or_404,
    render,
)

from orders.models import Order

from .forms import RefundRequestForm

from .models import (
    RefundRequest,
    ReturnRefundEvent,
    ReturnRequest,
    ReturnRequestItem,
)


@login_required
@transaction.atomic
def request_refund(
    request,
    order_number,
):

    order = get_object_or_404(
        Order.objects.select_for_update(),
        order_number=order_number,
        user=request.user,
    )

    if (
        order.payment_status != "paid"
        or order.status != "delivered"
    ):

        return JsonResponse(
            {
                "success": False,
                "error": (
                    "Refunds are available only "
                    "for paid delivered orders."
                ),
            },
            status=400,
        )


    processed_total = (
        RefundRequest.objects
        .filter(
            order=order,
            status="processed",
        )
        .aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )

    refundable_amount = (
        order.total_amount
        - processed_total
    )


    if refundable_amount <= 0:

        return JsonResponse(
            {
                "success": False,
                "error": (
                    "This order has already been "
                    "fully refunded."
                ),
            },
            status=400,
        )


    if RefundRequest.objects.filter(
        order=order,
        status__in=[
            "requested",
            "approved",
        ],
    ).exists():

        return JsonResponse(
            {
                "success": False,
                "error": (
                    "An active refund request "
                    "already exists."
                ),
            },
            status=400,
        )


    if request.method != "POST":

        form = RefundRequestForm(
            order=order
        )

        form.fields[
            "amount"
        ].initial = refundable_amount

        return render(
            request,
            "payments/refund_request.html",
            {
                "order": order,
                "form": form,
                "refundable_amount": (
                    refundable_amount
                ),
            },
        )


    form = RefundRequestForm(
        request.POST,
        order=order,
    )


    if form.is_valid():

        amount = form.cleaned_data[
            "amount"
        ]

        if amount > refundable_amount:

            form.add_error(
                "amount",
                (
                    "Refund amount exceeds the "
                    "remaining refundable balance."
                ),
            )

        else:

            refund = form.save(
                commit=False
            )

            refund.order = order

            refund.save()

            ReturnRefundEvent.objects.create(
                refund=refund,
                status="requested",
                message=(
                    "Customer submitted "
                    "refund request."
                ),
                created_by=request.user,
            )

            return render(
                request,
                "payments/refund_submitted.html",
                {
                    "refund": refund
                },
            )


    return render(
        request,
        "payments/refund_request.html",
        {
            "order": order,
            "form": form,
            "refundable_amount": (
                refundable_amount
            ),
        },
    )


@login_required
@transaction.atomic
def request_return(
    request,
    order_number,
):

    order = get_object_or_404(
        Order.objects
        .select_for_update()
        .prefetch_related(
            "items"
        ),
        order_number=order_number,
        user=request.user,
    )


    if (
        order.payment_status != "paid"
        or order.status != "delivered"
    ):

        return JsonResponse(
            {
                "success": False,
                "error": (
                    "Returns are available only "
                    "for paid delivered orders."
                ),
            },
            status=400,
        )


    if ReturnRequest.objects.filter(
        order=order,
        status__in=[
            "requested",
            "approved",
        ],
    ).exists():

        return JsonResponse(
            {
                "success": False,
                "error": (
                    "An active return request "
                    "already exists."
                ),
            },
            status=400,
        )


    items = list(
        order.items.select_related(
            "product",
            "variant",
        )
    )


    if request.method == "POST":

        request_type = (
            request.POST.get(
                "request_type",
                ""
            )
        )

        reason = (
            request.POST.get(
                "reason",
                ""
            ).strip()
        )


        if request_type not in {
            "return",
            "replacement",
        }:

            error = (
                "Select Return or Replacement."
            )

        elif not reason:

            error = (
                "Please explain why you are "
                "returning the item."
            )

        else:

            selected = []

            for item in items:

                raw_quantity = (
                    request.POST.get(
                        f"quantity_{item.pk}",
                        "0",
                    )
                )

                try:

                    quantity = int(
                        raw_quantity
                    )

                except (
                    TypeError,
                    ValueError,
                ):

                    quantity = 0


                if quantity < 0:

                    error = (
                        "Return quantity cannot "
                        "be negative."
                    )

                    break


                if quantity > item.quantity:

                    error = (
                        f"You purchased only "
                        f"{item.quantity} of "
                        f"{item.product_name}."
                    )

                    break


                if quantity:

                    selected.append(
                        (
                            item,
                            quantity,
                        )
                    )

            else:

                error = None


            if (
                not error
                and not selected
            ):

                error = (
                    "Select at least one item "
                    "to return."
                )


        if not error:

            return_request = (
                ReturnRequest.objects.create(
                    order=order,
                    request_type=request_type,
                    reason=reason,
                )
            )


            for (
                item,
                quantity,
            ) in selected:

                ReturnRequestItem.objects.create(
                    return_request=(
                        return_request
                    ),
                    order_item=item,
                    quantity=quantity,
                )


            ReturnRefundEvent.objects.create(
                return_request=(
                    return_request
                ),
                status="requested",
                message=(
                    "Customer submitted "
                    f"{return_request.get_request_type_display().lower()} "
                    "request."
                ),
                created_by=request.user,
            )


            return render(
                request,
                "payments/return_submitted.html",
                {
                    "return_request": (
                        return_request
                    )
                },
            )


        return render(
            request,
            "payments/return_request_v2.html",
            {
                "order": order,
                "items": items,
                "error": error,
                "request_type": request_type,
                "reason": reason,
            },
        )


    return render(
        request,
        "payments/return_request_v2.html",
        {
            "order": order,
            "items": items,
        },
    )
'''.strip() + "\n",
encoding="utf-8",
)

print(
    "Customer return/refund workflow created."
)


# ============================================================
# 3. ROUTE CUSTOMER REQUESTS THROUGH NEW SAFE VIEWS
# ============================================================

urls = URLS.read_text(
    encoding="utf-8-sig"
)

if (
    "from . import customer_returns"
    not in urls
):

    urls = urls.replace(
        "from . import views",
        (
            "from . import views\n"
            "from . import customer_returns"
        ),
        1,
    )


urls = re.sub(
    r'''
    path\(
        "refund/<str:order_number>/",
        \s*views\.request_refund,
        \s*name="request_refund"
    \),
    ''',
    '''path(
        "refund/<str:order_number>/",
        customer_returns.request_refund,
        name="request_refund",
    ),''',
    urls,
    count=1,
    flags=re.S | re.X,
)


urls = re.sub(
    r'''
    path\(
        "return/<str:order_number>/",
        \s*views\.request_return,
        \s*name="request_return"
    \),
    ''',
    '''path(
        "return/<str:order_number>/",
        customer_returns.request_return,
        name="request_return",
    ),''',
    urls,
    count=1,
    flags=re.S | re.X,
)


URLS.write_text(
    urls,
    encoding="utf-8",
)

print(
    "Customer routes upgraded."
)


# ============================================================
# 4. ADMIN RETURNS / REFUNDS VIEWS
# ============================================================

admin_views = PAYMENTS / "returns_admin_views.py"

admin_views.write_text(
r'''
from decimal import Decimal

from django.contrib import messages

from django.contrib.admin.views.decorators import (
    staff_member_required,
)

from django.core.paginator import Paginator

from django.db import transaction

from django.db.models import (
    Q,
    Sum,
)

from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from django.utils import timezone

from inventory.services import (
    adjust_product_stock,
    adjust_variant_stock,
)

from orders.models import Order

from .models import (
    RefundRequest,
    ReturnRefundEvent,
    ReturnRequest,
)


@staff_member_required
def returns_refunds_list(
    request,
):

    tab = request.GET.get(
        "tab",
        "returns",
    )

    status = request.GET.get(
        "status",
        "",
    ).strip()

    query = request.GET.get(
        "q",
        "",
    ).strip()


    returns = (
        ReturnRequest.objects
        .select_related(
            "order",
            "order__user",
        )
        .prefetch_related(
            "items",
        )
        .order_by(
            "-created_at"
        )
    )


    refunds = (
        RefundRequest.objects
        .select_related(
            "order",
            "order__user",
        )
        .order_by(
            "-created_at"
        )
    )


    if query:

        lookup = (
            Q(
                order__order_number__icontains=query
            )
            | Q(
                order__full_name__icontains=query
            )
            | Q(
                order__phone__icontains=query
            )
        )

        returns = returns.filter(
            lookup
        )

        refunds = refunds.filter(
            lookup
        )


    if status:

        returns = returns.filter(
            status=status
        )

        refunds = refunds.filter(
            status=status
        )


    counts = {

        "return_requested": (
            ReturnRequest.objects.filter(
                status="requested"
            ).count()
        ),

        "return_approved": (
            ReturnRequest.objects.filter(
                status="approved"
            ).count()
        ),

        "refund_requested": (
            RefundRequest.objects.filter(
                status="requested"
            ).count()
        ),

        "refund_approved": (
            RefundRequest.objects.filter(
                status="approved"
            ).count()
        ),
    }


    queryset = (
        refunds
        if tab == "refunds"
        else returns
    )


    paginator = Paginator(
        queryset,
        25,
    )

    page_obj = paginator.get_page(
        request.GET.get("page")
    )


    return render(
        request,
        "dashboard/admin/returns/list.html",
        {
            "tab": tab,
            "records": (
                page_obj.object_list
            ),
            "page_obj": page_obj,
            "status": status,
            "query": query,
            "counts": counts,
        },
    )


@staff_member_required
def return_detail(
    request,
    pk,
):

    return_request = get_object_or_404(
        ReturnRequest.objects
        .select_related(
            "order",
            "order__user",
            "processed_by",
        )
        .prefetch_related(
            "items__order_item",
            "events__created_by",
        ),
        pk=pk,
    )

    return render(
        request,
        "dashboard/admin/returns/return_detail.html",
        {
            "return_request": (
                return_request
            ),
            "order": return_request.order,
        },
    )


@staff_member_required
@transaction.atomic
def return_review(
    request,
    pk,
):

    return_request = get_object_or_404(
        ReturnRequest.objects
        .select_for_update(),
        pk=pk,
    )


    if request.method != "POST":

        return redirect(
            "admin_return_detail",
            pk=pk,
        )


    action = request.POST.get(
        "action",
        "",
    )

    note = request.POST.get(
        "staff_note",
        "",
    ).strip()


    if (
        return_request.status
        != "requested"
    ):

        messages.error(
            request,
            "Only requested returns can be reviewed.",
        )

        return redirect(
            "admin_return_detail",
            pk=pk,
        )


    if action not in {
        "approve",
        "reject",
    }:

        messages.error(
            request,
            "Invalid action.",
        )

        return redirect(
            "admin_return_detail",
            pk=pk,
        )


    if (
        action == "reject"
        and not note
    ):

        messages.error(
            request,
            "Add a reason before rejecting.",
        )

        return redirect(
            "admin_return_detail",
            pk=pk,
        )


    return_request.status = (
        "approved"
        if action == "approve"
        else "rejected"
    )

    return_request.staff_note = note

    return_request.processed_by = (
        request.user
    )

    return_request.save(
        update_fields=[
            "status",
            "staff_note",
            "processed_by",
            "updated_at",
        ]
    )


    ReturnRefundEvent.objects.create(
        return_request=return_request,
        status=return_request.status,
        message=(
            note
            or (
                "Return request approved."
                if action == "approve"
                else "Return request rejected."
            )
        ),
        created_by=request.user,
    )


    messages.success(
        request,
        (
            "Return approved."
            if action == "approve"
            else "Return rejected."
        ),
    )


    return redirect(
        "admin_return_detail",
        pk=pk,
    )


@staff_member_required
@transaction.atomic
def return_complete(
    request,
    pk,
):

    return_request = get_object_or_404(
        ReturnRequest.objects
        .select_for_update()
        .select_related(
            "order"
        )
        .prefetch_related(
            "items__order_item",
        ),
        pk=pk,
    )


    if request.method != "POST":

        return redirect(
            "admin_return_detail",
            pk=pk,
        )


    if (
        return_request.status
        != "approved"
    ):

        messages.error(
            request,
            "Approve the return before completing it.",
        )

        return redirect(
            "admin_return_detail",
            pk=pk,
        )


    if return_request.inventory_restored:

        messages.error(
            request,
            "Inventory has already been restored.",
        )

        return redirect(
            "admin_return_detail",
            pk=pk,
        )


    restored_any = False


    for item in return_request.items.all():

        should_restock = (
            request.POST.get(
                f"restock_{item.pk}"
            )
            == "1"
        )

        item.restock = should_restock

        item.save(
            update_fields=[
                "restock"
            ]
        )


        if not should_restock:
            continue


        order_item = item.order_item

        reference = (
            f"RETURN-{return_request.pk}-"
            f"{return_request.order.order_number}"
        )


        if order_item.variant_id:

            adjust_variant_stock(
                variant_id=(
                    order_item.variant_id
                ),
                movement_type="return",
                quantity=item.quantity,
                reference=reference,
                notes=(
                    "Customer return accepted "
                    "back into sellable inventory."
                ),
                user=request.user,
            )

        else:

            adjust_product_stock(
                product_id=(
                    order_item.product_id
                ),
                movement_type="return",
                quantity=item.quantity,
                reference=reference,
                notes=(
                    "Customer return accepted "
                    "back into sellable inventory."
                ),
                user=request.user,
            )


        restored_any = True


    return_request.status = (
        "completed"
    )

    return_request.received_at = (
        timezone.now()
    )

    return_request.completed_at = (
        timezone.now()
    )

    return_request.inventory_restored = (
        restored_any
    )

    return_request.processed_by = (
        request.user
    )

    return_request.save(
        update_fields=[
            "status",
            "received_at",
            "completed_at",
            "inventory_restored",
            "processed_by",
            "updated_at",
        ]
    )


    ReturnRefundEvent.objects.create(
        return_request=return_request,
        status="completed",
        message=(
            "Return completed. "
            + (
                "Selected items were restored "
                "to inventory."
                if restored_any
                else (
                    "No items were marked as "
                    "restockable."
                )
            )
        ),
        created_by=request.user,
    )


    messages.success(
        request,
        "Return completed successfully.",
    )


    return redirect(
        "admin_return_detail",
        pk=pk,
    )


@staff_member_required
def refund_detail(
    request,
    pk,
):

    refund = get_object_or_404(
        RefundRequest.objects
        .select_related(
            "order",
            "order__user",
            "processed_by",
        )
        .prefetch_related(
            "events__created_by"
        ),
        pk=pk,
    )

    processed_total = (
        RefundRequest.objects
        .filter(
            order=refund.order,
            status="processed",
        )
        .aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )


    return render(
        request,
        "dashboard/admin/returns/refund_detail.html",
        {
            "refund": refund,
            "order": refund.order,
            "processed_total": (
                processed_total
            ),
        },
    )


@staff_member_required
@transaction.atomic
def refund_review(
    request,
    pk,
):

    refund = get_object_or_404(
        RefundRequest.objects
        .select_for_update()
        .select_related(
            "order"
        ),
        pk=pk,
    )


    if request.method != "POST":

        return redirect(
            "admin_refund_detail",
            pk=pk,
        )


    if refund.status != "requested":

        messages.error(
            request,
            "Only requested refunds can be reviewed.",
        )

        return redirect(
            "admin_refund_detail",
            pk=pk,
        )


    action = request.POST.get(
        "action",
        "",
    )

    note = request.POST.get(
        "staff_note",
        "",
    ).strip()


    if action not in {
        "approve",
        "reject",
    }:

        messages.error(
            request,
            "Invalid action.",
        )

        return redirect(
            "admin_refund_detail",
            pk=pk,
        )


    if (
        action == "reject"
        and not note
    ):

        messages.error(
            request,
            "Add a reason before rejecting.",
        )

        return redirect(
            "admin_refund_detail",
            pk=pk,
        )


    refund.status = (
        "approved"
        if action == "approve"
        else "rejected"
    )

    refund.staff_note = note

    refund.processed_by = (
        request.user
    )

    refund.save(
        update_fields=[
            "status",
            "staff_note",
            "processed_by",
            "updated_at",
        ]
    )


    ReturnRefundEvent.objects.create(
        refund=refund,
        status=refund.status,
        message=(
            note
            or (
                "Refund approved."
                if action == "approve"
                else "Refund rejected."
            )
        ),
        created_by=request.user,
    )


    messages.success(
        request,
        (
            "Refund approved."
            if action == "approve"
            else "Refund rejected."
        ),
    )


    return redirect(
        "admin_refund_detail",
        pk=pk,
    )


@staff_member_required
@transaction.atomic
def refund_process(
    request,
    pk,
):

    refund = get_object_or_404(
        RefundRequest.objects
        .select_for_update()
        .select_related(
            "order"
        ),
        pk=pk,
    )


    if request.method != "POST":

        return redirect(
            "admin_refund_detail",
            pk=pk,
        )


    if refund.status != "approved":

        messages.error(
            request,
            "Approve the refund before processing it.",
        )

        return redirect(
            "admin_refund_detail",
            pk=pk,
        )


    reference = request.POST.get(
        "external_reference",
        "",
    ).strip()


    if not reference:

        messages.error(
            request,
            (
                "Enter the actual M-PESA, bank, "
                "cash or other refund reference."
            ),
        )

        return redirect(
            "admin_refund_detail",
            pk=pk,
        )


    refund.status = "processed"

    refund.external_reference = (
        reference
    )

    refund.processed_by = (
        request.user
    )

    refund.processed_at = (
        timezone.now()
    )

    refund.save(
        update_fields=[
            "status",
            "external_reference",
            "processed_by",
            "processed_at",
            "updated_at",
        ]
    )


    processed_total = (
        RefundRequest.objects
        .filter(
            order=refund.order,
            status="processed",
        )
        .aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )


    if (
        processed_total
        >= refund.order.total_amount
    ):

        refund.order.payment_status = (
            "refunded"
        )

        refund.order.save(
            update_fields=[
                "payment_status",
                "updated_at",
            ]
        )


    ReturnRefundEvent.objects.create(
        refund=refund,
        status="processed",
        message=(
            "Refund recorded with reference "
            f"{reference}."
        ),
        created_by=request.user,
    )


    messages.success(
        request,
        "Refund marked as processed.",
    )


    return redirect(
        "admin_refund_detail",
        pk=pk,
    )
'''.strip() + "\n",
encoding="utf-8",
)

print(
    "Admin returns/refunds views created."
)


# ============================================================
# 5. ADMIN URLS
# ============================================================

admin_urls = PAYMENTS / "returns_admin_urls.py"

admin_urls.write_text(
r'''
from django.urls import path

from . import returns_admin_views as views


urlpatterns = [

    path(
        "",
        views.returns_refunds_list,
        name="admin_returns_refunds",
    ),

    path(
        "returns/<int:pk>/",
        views.return_detail,
        name="admin_return_detail",
    ),

    path(
        "returns/<int:pk>/review/",
        views.return_review,
        name="admin_return_review",
    ),

    path(
        "returns/<int:pk>/complete/",
        views.return_complete,
        name="admin_return_complete",
    ),

    path(
        "refunds/<int:pk>/",
        views.refund_detail,
        name="admin_refund_detail",
    ),

    path(
        "refunds/<int:pk>/review/",
        views.refund_review,
        name="admin_refund_review",
    ),

    path(
        "refunds/<int:pk>/process/",
        views.refund_process,
        name="admin_refund_process",
    ),
]
'''.strip() + "\n",
encoding="utf-8",
)


# ============================================================
# 6. ROOT CONFIG URL
# ============================================================

CONFIG_URLS = ROOT / "config" / "urls.py"

config = CONFIG_URLS.read_text(
    encoding="utf-8-sig"
)

if (
    "payments.returns_admin_urls"
    not in config
):

    marker = "urlpatterns = ["

    route = r'''

    path(
        "dashboard/admin/returns/",
        include("payments.returns_admin_urls"),
    ),
'''

    config = config.replace(
        marker,
        marker + route,
        1,
    )

    CONFIG_URLS.write_text(
        config,
        encoding="utf-8",
    )

print(
    "Admin return/refund URLs added."
)


# ============================================================
# 7. CUSTOMER RETURN ITEM TEMPLATE
# ============================================================

customer_template = (
    PAYMENTS
    / "templates"
    / "payments"
    / "return_request_v2.html"
)

customer_template.parent.mkdir(
    parents=True,
    exist_ok=True,
)

customer_template.write_text(
r'''
{% extends "base.html" %}

{% block content %}

<div class="container py-5">

    <div class="row justify-content-center">

        <div class="col-lg-8">

            <a
                href="{% url 'order_detail' order.order_number %}"
                class="btn btn-outline-secondary btn-sm mb-4"
            >
                &larr; Back to Order
            </a>


            <div class="card shadow-sm">

                <div class="card-body p-4">

                    <h3>
                        Return or Replace Items
                    </h3>

                    <p class="text-muted">
                        Order {{ order.order_number }}
                    </p>


                    {% if error %}

                        <div class="alert alert-danger">
                            {{ error }}
                        </div>

                    {% endif %}


                    <form method="POST">

                        {% csrf_token %}


                        <div class="mb-4">

                            <label class="form-label fw-semibold">
                                Request Type
                            </label>

                            <select
                                name="request_type"
                                class="form-select"
                                required
                            >

                                <option value="">
                                    Select
                                </option>

                                <option
                                    value="return"
                                    {% if request_type == "return" %}
                                        selected
                                    {% endif %}
                                >
                                    Return
                                </option>

                                <option
                                    value="replacement"
                                    {% if request_type == "replacement" %}
                                        selected
                                    {% endif %}
                                >
                                    Replacement
                                </option>

                            </select>

                        </div>


                        <h5 class="mb-3">
                            Select Items
                        </h5>


                        <div class="table-responsive">

                            <table class="table align-middle">

                                <thead>

                                    <tr>

                                        <th>Product</th>

                                        <th>
                                            Purchased
                                        </th>

                                        <th style="width:140px;">
                                            Return Qty
                                        </th>

                                    </tr>

                                </thead>


                                <tbody>

                                    {% for item in items %}

                                        <tr>

                                            <td>

                                                <strong>
                                                    {{ item.product_name }}
                                                </strong>

                                                {% if item.variant_name %}

                                                    <div class="small text-muted">
                                                        {{ item.variant_name }}
                                                    </div>

                                                {% endif %}

                                            </td>


                                            <td>
                                                {{ item.quantity }}
                                            </td>


                                            <td>

                                                <input
                                                    type="number"
                                                    name="quantity_{{ item.pk }}"
                                                    min="0"
                                                    max="{{ item.quantity }}"
                                                    value="0"
                                                    class="form-control"
                                                >

                                            </td>

                                        </tr>

                                    {% endfor %}

                                </tbody>

                            </table>

                        </div>


                        <div class="mb-4">

                            <label class="form-label fw-semibold">
                                Reason
                            </label>

                            <textarea
                                name="reason"
                                rows="5"
                                class="form-control"
                                required
                                placeholder="Explain the problem with the item..."
                            >{{ reason|default:"" }}</textarea>

                        </div>


                        <button
                            class="btn btn-primary"
                        >
                            Submit Request
                        </button>

                    </form>

                </div>

            </div>

        </div>

    </div>

</div>

{% endblock %}
'''.strip() + "\n",
encoding="utf-8",
)


# ============================================================
# 8. ADMIN LIST TEMPLATE
# ============================================================

(TEMPLATES / "list.html").write_text(
r'''
{% extends "dashboard/admin/base.html" %}

{% block title %}
Returns & Refunds
{% endblock %}

{% block page_heading %}
Returns & Refunds
{% endblock %}

{% block admin_content %}

<div class="dashboard-heading">

    <div>

        <h1>
            Returns & Refunds
        </h1>

        <p>
            Review customer returns, replacements
            and refund requests.
        </p>

    </div>

</div>


<div class="row g-3 mb-4">

    <div class="col-md-3">

        <div class="dashboard-card mini-stat">

            <span>
                Returns Waiting
            </span>

            <strong>
                {{ counts.return_requested }}
            </strong>

        </div>

    </div>


    <div class="col-md-3">

        <div class="dashboard-card mini-stat">

            <span>
                Returns Approved
            </span>

            <strong>
                {{ counts.return_approved }}
            </strong>

        </div>

    </div>


    <div class="col-md-3">

        <div class="dashboard-card mini-stat">

            <span>
                Refunds Waiting
            </span>

            <strong>
                {{ counts.refund_requested }}
            </strong>

        </div>

    </div>


    <div class="col-md-3">

        <div class="dashboard-card mini-stat">

            <span>
                Refunds Approved
            </span>

            <strong>
                {{ counts.refund_approved }}
            </strong>

        </div>

    </div>

</div>


<div class="dashboard-card mb-4">

    <div class="d-flex gap-2 mb-3">

        <a
            href="?tab=returns"
            class="
                btn
                {% if tab == 'returns' %}
                    btn-primary
                {% else %}
                    btn-outline-primary
                {% endif %}
            "
        >
            Returns
        </a>

        <a
            href="?tab=refunds"
            class="
                btn
                {% if tab == 'refunds' %}
                    btn-primary
                {% else %}
                    btn-outline-primary
                {% endif %}
            "
        >
            Refunds
        </a>

    </div>


    <form method="GET">

        <input
            type="hidden"
            name="tab"
            value="{{ tab }}"
        >

        <div class="row g-2">

            <div class="col-lg-7">

                <input
                    type="text"
                    name="q"
                    value="{{ query }}"
                    class="form-control"
                    placeholder="Search order, customer or phone..."
                >

            </div>

            <div class="col-lg-3">

                <select
                    name="status"
                    class="form-select"
                >

                    <option value="">
                        All Statuses
                    </option>

                    <option value="requested">
                        Requested
                    </option>

                    <option value="approved">
                        Approved
                    </option>

                    {% if tab == "returns" %}

                        <option value="completed">
                            Completed
                        </option>

                    {% else %}

                        <option value="processed">
                            Processed
                        </option>

                    {% endif %}

                    <option value="rejected">
                        Rejected
                    </option>

                </select>

            </div>

            <div class="col-lg-2">

                <button class="btn btn-primary w-100">
                    Filter
                </button>

            </div>

        </div>

    </form>

</div>


<div class="dashboard-card">

    <div class="table-responsive">

        <table
            class="
                table
                dashboard-table
                align-middle
            "
        >

            <thead>

                <tr>

                    <th>Order</th>

                    <th>Customer</th>

                    {% if tab == "returns" %}
                        <th>Type</th>
                        <th>Items</th>
                    {% else %}
                        <th>Amount</th>
                    {% endif %}

                    <th>Status</th>

                    <th>Date</th>

                    <th class="text-end">
                        Action
                    </th>

                </tr>

            </thead>


            <tbody>

                {% for record in records %}

                    <tr>

                        <td>
                            <strong>
                                {{ record.order.order_number }}
                            </strong>
                        </td>

                        <td>

                            {{ record.order.full_name }}

                            <small class="d-block text-muted">
                                {{ record.order.phone }}
                            </small>

                        </td>


                        {% if tab == "returns" %}

                            <td>
                                {{ record.get_request_type_display }}
                            </td>

                            <td>
                                {{ record.items.count }}
                            </td>

                        {% else %}

                            <td>
                                KES {{ record.amount|floatformat:2 }}
                            </td>

                        {% endif %}


                        <td>

                            {% if record.status == "requested" %}

                                <span class="badge text-bg-warning">
                                    Requested
                                </span>

                            {% elif record.status == "approved" %}

                                <span class="badge text-bg-primary">
                                    Approved
                                </span>

                            {% elif record.status == "rejected" %}

                                <span class="badge text-bg-danger">
                                    Rejected
                                </span>

                            {% else %}

                                <span class="badge text-bg-success">
                                    {{ record.get_status_display }}
                                </span>

                            {% endif %}

                        </td>


                        <td>
                            {{ record.created_at|date:"d M Y H:i" }}
                        </td>


                        <td class="text-end">

                            {% if tab == "returns" %}

                                <a
                                    href="{% url 'admin_return_detail' record.pk %}"
                                    class="btn btn-sm btn-outline-primary"
                                >
                                    Review
                                </a>

                            {% else %}

                                <a
                                    href="{% url 'admin_refund_detail' record.pk %}"
                                    class="btn btn-sm btn-outline-primary"
                                >
                                    Review
                                </a>

                            {% endif %}

                        </td>

                    </tr>

                {% empty %}

                    <tr>

                        <td
                            colspan="7"
                            class="text-center text-muted py-5"
                        >
                            No requests found.
                        </td>

                    </tr>

                {% endfor %}

            </tbody>

        </table>

    </div>

</div>

{% endblock %}
'''.strip() + "\n",
encoding="utf-8",
)


# ============================================================
# 9. RETURN DETAIL TEMPLATE
# ============================================================

(TEMPLATES / "return_detail.html").write_text(
r'''
{% extends "dashboard/admin/base.html" %}

{% block title %}
Return {{ order.order_number }}
{% endblock %}

{% block page_heading %}
Return Request
{% endblock %}

{% block admin_content %}

<div class="dashboard-heading">

    <div>

        <a
            href="{% url 'admin_returns_refunds' %}"
            class="btn btn-sm btn-outline-secondary mb-3"
        >
            &larr; Returns
        </a>

        <h1>
            {{ return_request.get_request_type_display }}
            — {{ order.order_number }}
        </h1>

        <p>
            {{ order.full_name }}
            · {{ order.phone }}
        </p>

    </div>

</div>


<div class="row g-4">

    <div class="col-lg-8">

        <div class="dashboard-card mb-4">

            <h2 class="h5">
                Returned Items
            </h2>

            <div class="table-responsive">

                <table class="table align-middle">

                    <thead>

                        <tr>

                            <th>Product</th>

                            <th>Qty</th>

                            <th>Purchased</th>

                            <th>Restock?</th>

                        </tr>

                    </thead>


                    <tbody>

                        {% for item in return_request.items.all %}

                            <tr>

                                <td>

                                    <strong>
                                        {{ item.order_item.product_name }}
                                    </strong>

                                    {% if item.order_item.variant_name %}

                                        <div class="small text-muted">
                                            {{ item.order_item.variant_name }}
                                        </div>

                                    {% endif %}

                                </td>

                                <td>
                                    {{ item.quantity }}
                                </td>

                                <td>
                                    {{ item.order_item.quantity }}
                                </td>

                                <td>

                                    {% if return_request.status == "approved" %}

                                        <input
                                            form="complete-return-form"
                                            type="checkbox"
                                            name="restock_{{ item.pk }}"
                                            value="1"
                                            class="form-check-input"
                                        >

                                    {% else %}

                                        {% if item.restock %}
                                            Yes
                                        {% else %}
                                            No
                                        {% endif %}

                                    {% endif %}

                                </td>

                            </tr>

                        {% endfor %}

                    </tbody>

                </table>

            </div>

        </div>


        <div class="dashboard-card mb-4">

            <h2 class="h5">
                Customer Reason
            </h2>

            <p class="mb-0">
                {{ return_request.reason }}
            </p>

        </div>


        <div class="dashboard-card">

            <h2 class="h5 mb-3">
                Timeline
            </h2>

            {% for event in return_request.events.all %}

                <div class="border-start ps-3 mb-3">

                    <strong>
                        {{ event.status|title }}
                    </strong>

                    <small class="d-block text-muted">
                        {{ event.created_at|date:"d M Y H:i" }}

                        {% if event.created_by %}
                            · {{ event.created_by.username }}
                        {% endif %}
                    </small>

                    {% if event.message %}
                        <div class="mt-1">
                            {{ event.message }}
                        </div>
                    {% endif %}

                </div>

            {% empty %}

                <p class="text-muted">
                    No timeline entries.
                </p>

            {% endfor %}

        </div>

    </div>


    <div class="col-lg-4">

        <div class="dashboard-card mb-4">

            <h2 class="h5">
                Status
            </h2>

            <span class="badge text-bg-primary">
                {{ return_request.get_status_display }}
            </span>

        </div>


        {% if return_request.status == "requested" %}

            <div class="dashboard-card mb-4">

                <h2 class="h5">
                    Review Request
                </h2>

                <form
                    method="POST"
                    action="{% url 'admin_return_review' return_request.pk %}"
                >

                    {% csrf_token %}

                    <textarea
                        name="staff_note"
                        rows="4"
                        class="form-control mb-3"
                        placeholder="Staff note / rejection reason"
                    ></textarea>

                    <div class="d-grid gap-2">

                        <button
                            name="action"
                            value="approve"
                            class="btn btn-success"
                        >
                            Approve Return
                        </button>

                        <button
                            name="action"
                            value="reject"
                            class="btn btn-outline-danger"
                        >
                            Reject
                        </button>

                    </div>

                </form>

            </div>

        {% endif %}


        {% if return_request.status == "approved" %}

            <div class="dashboard-card">

                <h2 class="h5">
                    Complete Return
                </h2>

                <p class="small text-muted">

                    Tick only items that have physically
                    returned in sellable condition.

                </p>

                <form
                    id="complete-return-form"
                    method="POST"
                    action="{% url 'admin_return_complete' return_request.pk %}"
                >

                    {% csrf_token %}

                    <button
                        class="btn btn-success w-100"
                        onclick="return confirm('Complete this return and restore selected inventory?');"
                    >
                        Complete Return
                    </button>

                </form>

            </div>

        {% endif %}

    </div>

</div>

{% endblock %}
'''.strip() + "\n",
encoding="utf-8",
)


# ============================================================
# 10. REFUND DETAIL TEMPLATE
# ============================================================

(TEMPLATES / "refund_detail.html").write_text(
r'''
{% extends "dashboard/admin/base.html" %}

{% block title %}
Refund {{ order.order_number }}
{% endblock %}

{% block page_heading %}
Refund Request
{% endblock %}

{% block admin_content %}

<div class="dashboard-heading">

    <div>

        <a
            href="{% url 'admin_returns_refunds' %}?tab=refunds"
            class="btn btn-sm btn-outline-secondary mb-3"
        >
            &larr; Refunds
        </a>

        <h1>
            Refund — {{ order.order_number }}
        </h1>

        <p>
            {{ order.full_name }}
            · {{ order.phone }}
        </p>

    </div>

</div>


<div class="row g-4">

    <div class="col-lg-8">

        <div class="dashboard-card mb-4">

            <div class="row g-3">

                <div class="col-md-4">

                    <small class="text-muted">
                        Requested
                    </small>

                    <div class="fs-4 fw-bold">
                        KES {{ refund.amount|floatformat:2 }}
                    </div>

                </div>

                <div class="col-md-4">

                    <small class="text-muted">
                        Order Total
                    </small>

                    <div class="fw-semibold">
                        KES {{ order.total_amount|floatformat:2 }}
                    </div>

                </div>

                <div class="col-md-4">

                    <small class="text-muted">
                        Already Processed
                    </small>

                    <div class="fw-semibold">
                        KES {{ processed_total|floatformat:2 }}
                    </div>

                </div>

            </div>

        </div>


        <div class="dashboard-card mb-4">

            <h2 class="h5">
                Customer Reason
            </h2>

            <p class="mb-0">
                {{ refund.reason }}
            </p>

        </div>


        {% if refund.external_reference %}

            <div class="dashboard-card mb-4">

                <h2 class="h5">
                    Refund Reference
                </h2>

                <code>
                    {{ refund.external_reference }}
                </code>

            </div>

        {% endif %}


        <div class="dashboard-card">

            <h2 class="h5 mb-3">
                Timeline
            </h2>

            {% for event in refund.events.all %}

                <div class="border-start ps-3 mb-3">

                    <strong>
                        {{ event.status|title }}
                    </strong>

                    <small class="d-block text-muted">

                        {{ event.created_at|date:"d M Y H:i" }}

                        {% if event.created_by %}
                            · {{ event.created_by.username }}
                        {% endif %}

                    </small>

                    {% if event.message %}

                        <div class="mt-1">
                            {{ event.message }}
                        </div>

                    {% endif %}

                </div>

            {% empty %}

                <p class="text-muted">
                    No timeline entries.
                </p>

            {% endfor %}

        </div>

    </div>


    <div class="col-lg-4">

        <div class="dashboard-card mb-4">

            <h2 class="h5">
                Status
            </h2>

            <span class="badge text-bg-primary">
                {{ refund.get_status_display }}
            </span>

        </div>


        {% if refund.status == "requested" %}

            <div class="dashboard-card">

                <h2 class="h5">
                    Review Refund
                </h2>

                <form
                    method="POST"
                    action="{% url 'admin_refund_review' refund.pk %}"
                >

                    {% csrf_token %}

                    <textarea
                        name="staff_note"
                        rows="4"
                        class="form-control mb-3"
                        placeholder="Staff note / rejection reason"
                    ></textarea>

                    <div class="d-grid gap-2">

                        <button
                            name="action"
                            value="approve"
                            class="btn btn-success"
                        >
                            Approve
                        </button>

                        <button
                            name="action"
                            value="reject"
                            class="btn btn-outline-danger"
                        >
                            Reject
                        </button>

                    </div>

                </form>

            </div>

        {% endif %}


        {% if refund.status == "approved" %}

            <div class="dashboard-card">

                <h2 class="h5">
                    Record Actual Refund
                </h2>

                <p class="small text-muted">

                    Do this only after the money has
                    actually been returned to the customer.

                </p>

                <form
                    method="POST"
                    action="{% url 'admin_refund_process' refund.pk %}"
                >

                    {% csrf_token %}

                    <label class="form-label">
                        Refund Reference
                    </label>

                    <input
                        type="text"
                        name="external_reference"
                        class="form-control mb-3"
                        placeholder="M-PESA / bank / cash reference"
                        required
                    >

                    <button
                        class="btn btn-success w-100"
                        onclick="return confirm('Confirm that this refund has actually been paid?');"
                    >
                        Mark Refund Processed
                    </button>

                </form>

            </div>

        {% endif %}

    </div>

</div>

{% endblock %}
'''.strip() + "\n",
encoding="utf-8",
)


# ============================================================
# 11. SAFELY ACTIVATE SIDEBAR ITEM
# ============================================================

base = BASE.read_text(
    encoding="utf-8-sig"
)


def replace_sidebar_anchor(
    html,
    label,
    replacement,
):

    pattern = re.compile(
        r'''
        <a\b
        (?:
            (?!</a>).
        )*?
        <span>
        \s*
        '''
        + re.escape(label)
        +
        r'''
        \s*
        </span>
        (?:
            (?!</a>).
        )*?
        </a>
        ''',
        flags=re.S | re.X,
    )

    matches = list(
        pattern.finditer(html)
    )

    if len(matches) != 1:

        raise RuntimeError(
            f"Expected one {label!r} sidebar item; "
            f"found {len(matches)}."
        )

    match = matches[0]

    return (
        html[:match.start()]
        + replacement
        + html[match.end():]
    )


if (
    "{% url 'admin_returns_refunds' %}"
    not in base
):

    replacement = r'''
            <a
                href="{% url 'admin_returns_refunds' %}"
                class="
                    sidebar-link
                    {% if 'admin_return' in request.resolver_match.url_name or 'admin_refund' in request.resolver_match.url_name or request.resolver_match.url_name == 'admin_returns_refunds' %}
                        active
                    {% endif %}
                "
            >

                <i class="bi bi-arrow-counterclockwise"></i>

                <span>
                    Returns & Refunds
                </span>

            </a>
'''

    base = replace_sidebar_anchor(
        base,
        "Returns & Refunds",
        replacement,
    )


BASE.write_text(
    base,
    encoding="utf-8",
)

print(
    "Returns & Refunds sidebar activated safely."
)


# ============================================================
# 12. TESTS
# ============================================================

tests = PAYMENTS / "test_phase8a.py"

tests.write_text(
r'''
from decimal import Decimal

from django.contrib.auth import (
    get_user_model,
)

from django.test import TestCase

from django.urls import reverse

from orders.models import (
    Order,
    OrderItem,
)

from products.models import Product

from payments.models import (
    RefundRequest,
    ReturnRequest,
    ReturnRequestItem,
)


User = get_user_model()


class Phase8ATests(TestCase):

    def setUp(self):

        self.customer = (
            User.objects.create_user(
                username="returncustomer",
                password="pass12345",
                role=User.CUSTOMER,
            )
        )

        self.staff = (
            User.objects.create_user(
                username="returnstaff",
                password="pass12345",
                role=User.ADMIN,
                is_staff=True,
            )
        )

        self.product = (
            Product.objects.create(
                name="Return Test Product",
                slug="return-test-product",
                sku="RET-001",
                price=Decimal("1000.00"),
                stock=10,
                reserved_stock=0,
                is_active=True,
            )
        )

        self.order = Order.objects.create(
            user=self.customer,
            order_number="RETURN-ORDER-001",
            full_name="Return Customer",
            phone="0712345678",
            email="return@example.com",
            county="Nairobi",
            city="Nairobi",
            estate="CBD",
            house_number="1",
            subtotal=Decimal("2000.00"),
            shipping_cost=Decimal("0.00"),
            discount=Decimal("0.00"),
            total_amount=Decimal("2000.00"),
            status="delivered",
            payment_status="paid",
            inventory_status="consumed",
        )

        self.item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            product_name=self.product.name,
            price=Decimal("1000.00"),
            quantity=2,
            subtotal=Decimal("2000.00"),
        )


    def test_customer_can_request_item_return(
        self
    ):

        self.client.login(
            username="returncustomer",
            password="pass12345",
        )

        response = self.client.post(
            reverse(
                "request_return",
                kwargs={
                    "order_number": (
                        self.order.order_number
                    )
                },
            ),
            {
                "request_type": "return",
                "reason": "Item not suitable",
                f"quantity_{self.item.pk}": "1",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        request_obj = (
            ReturnRequest.objects.get(
                order=self.order
            )
        )

        line = (
            ReturnRequestItem.objects.get(
                return_request=request_obj
            )
        )

        self.assertEqual(
            line.quantity,
            1,
        )


    def test_staff_can_approve_return(
        self
    ):

        request_obj = (
            ReturnRequest.objects.create(
                order=self.order,
                request_type="return",
                reason="Test",
            )
        )

        ReturnRequestItem.objects.create(
            return_request=request_obj,
            order_item=self.item,
            quantity=1,
        )

        self.client.login(
            username="returnstaff",
            password="pass12345",
        )

        response = self.client.post(
            reverse(
                "admin_return_review",
                kwargs={
                    "pk": request_obj.pk
                },
            ),
            {
                "action": "approve",
                "staff_note": "Approved",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        request_obj.refresh_from_db()

        self.assertEqual(
            request_obj.status,
            "approved",
        )


    def test_refund_requires_real_reference(
        self
    ):

        refund = RefundRequest.objects.create(
            order=self.order,
            amount=Decimal("500.00"),
            reason="Test refund",
            status="approved",
        )

        self.client.login(
            username="returnstaff",
            password="pass12345",
        )

        response = self.client.post(
            reverse(
                "admin_refund_process",
                kwargs={
                    "pk": refund.pk
                },
            ),
            {
                "external_reference": "",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        refund.refresh_from_db()

        self.assertEqual(
            refund.status,
            "approved",
        )
'''.strip() + "\n",
encoding="utf-8",
)


print()
print("=" * 72)
print("PHASE 8A RETURNS & REFUNDS COMPLETE")
print("=" * 72)
print()
print("Next:")
print("python manage.py makemigrations payments")
print("python manage.py migrate")
print("python manage.py check")
