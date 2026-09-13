import csv

from decimal import Decimal

from django.contrib import messages

from accounts.staff_auth import (
    staff_member_required,
)

from django.contrib.auth import (
    get_user_model,
)

from django.core.paginator import (
    Paginator,
)

from django.db.models import (
    Count,
    DecimalField,
    Max,
    Q,
    Sum,
    Value,
)

from django.db.models.functions import (
    Coalesce,
)

from django.http import (
    HttpResponse,
)

from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from orders.models import Order

from .forms import CustomerNoteForm

from .models import CustomerNote


User = get_user_model()


def customer_queryset():

    return (
        User.objects
        .filter(
            role=User.CUSTOMER
        )
        .annotate(

            total_orders=Count(
                "orders",
                distinct=True,
            ),

            paid_orders=Count(
                "orders",
                filter=Q(
                    orders__payment_status=(
                        "paid"
                    )
                ),
                distinct=True,
            ),

            lifetime_spend=Coalesce(
                Sum(
                    "orders__total_amount",
                    filter=Q(
                        orders__payment_status=(
                            "paid"
                        )
                    ),
                ),
                Value(
                    Decimal("0.00")
                ),
                output_field=DecimalField(
                    max_digits=14,
                    decimal_places=2,
                ),
            ),

            last_order_at=Max(
                "orders__created_at"
            ),
        )
    )


# ============================================================
# CUSTOMER LIST
# ============================================================

@staff_member_required
def customer_list(request):

    customers = (
        customer_queryset()
        .order_by(
            "-date_joined"
        )
    )

    query = request.GET.get(
        "q",
        "",
    ).strip()

    status = request.GET.get(
        "status",
        "",
    )

    order_status = request.GET.get(
        "orders",
        "",
    )

    if query:

        customers = (
            customers.filter(
                Q(
                    username__icontains=query
                )
                | Q(
                    first_name__icontains=query
                )
                | Q(
                    last_name__icontains=query
                )
                | Q(
                    email__icontains=query
                )
                | Q(
                    phone__icontains=query
                )
            )
        )

    if status == "active":

        customers = customers.filter(
            is_active=True
        )

    elif status == "inactive":

        customers = customers.filter(
            is_active=False
        )

    elif status == "verified":

        customers = customers.filter(
            email_verified=True
        )

    elif status == "unverified":

        customers = customers.filter(
            email_verified=False
        )

    if order_status == "with_orders":

        customers = customers.filter(
            total_orders__gt=0
        )

    elif order_status == "no_orders":

        customers = customers.filter(
            total_orders=0
        )

    elif order_status == "buyers":

        customers = customers.filter(
            paid_orders__gt=0
        )

    total_customers = (
        User.objects
        .filter(
            role=User.CUSTOMER
        )
        .count()
    )

    active_customers = (
        User.objects
        .filter(
            role=User.CUSTOMER,
            is_active=True,
        )
        .count()
    )

    customers_with_orders = (
        User.objects
        .filter(
            role=User.CUSTOMER,
            orders__isnull=False,
        )
        .distinct()
        .count()
    )

    paying_customers = (
        User.objects
        .filter(
            role=User.CUSTOMER,
            orders__payment_status="paid",
        )
        .distinct()
        .count()
    )

    paginator = Paginator(
        customers,
        25,
    )

    page_obj = paginator.get_page(
        request.GET.get("page")
    )

    return render(
        request,
        (
            "dashboard/admin/"
            "customers/list.html"
        ),
        {
            "customers": (
                page_obj.object_list
            ),
            "page_obj": page_obj,
            "query": query,
            "selected_status": status,
            "selected_orders": (
                order_status
            ),
            "total_customers": (
                total_customers
            ),
            "active_customers": (
                active_customers
            ),
            "customers_with_orders": (
                customers_with_orders
            ),
            "paying_customers": (
                paying_customers
            ),
        },
    )


# ============================================================
# CUSTOMER DETAIL
# ============================================================

@staff_member_required
def customer_detail(
    request,
    pk,
):

    customer = get_object_or_404(
        User,
        pk=pk,
        role=User.CUSTOMER,
    )

    orders = (
        customer.orders
        .select_related(
            "coupon"
        )
        .prefetch_related(
            "items"
        )
        .order_by(
            "-created_at"
        )
    )

    paid_orders = orders.filter(
        payment_status="paid"
    )

    lifetime_spend = (
        paid_orders.aggregate(
            total=Sum(
                "total_amount"
            )
        )["total"]
        or Decimal("0.00")
    )

    total_orders = orders.count()

    paid_order_count = (
        paid_orders.count()
    )

    last_order = (
        orders.first()
    )

    addresses = (
        customer.addresses
        .order_by(
            "-is_default",
            "id",
        )
    )

    notes = (
        CustomerNote.objects
        .filter(
            customer=customer
        )
        .select_related(
            "created_by"
        )
    )

    note_form = (
        CustomerNoteForm()
    )

    paginator = Paginator(
        orders,
        15,
    )

    page_obj = paginator.get_page(
        request.GET.get("page")
    )

    return render(
        request,
        (
            "dashboard/admin/"
            "customers/detail.html"
        ),
        {
            "customer": customer,
            "orders": (
                page_obj.object_list
            ),
            "page_obj": page_obj,
            "addresses": addresses,
            "notes": notes,
            "note_form": note_form,
            "lifetime_spend": (
                lifetime_spend
            ),
            "total_orders": (
                total_orders
            ),
            "paid_order_count": (
                paid_order_count
            ),
            "last_order": last_order,
        },
    )


# ============================================================
# ADD INTERNAL NOTE
# ============================================================

@staff_member_required
def customer_note_add(
    request,
    pk,
):

    customer = get_object_or_404(
        User,
        pk=pk,
        role=User.CUSTOMER,
    )

    if request.method != "POST":

        return redirect(
            "crm_customer_detail",
            pk=customer.pk,
        )

    form = CustomerNoteForm(
        request.POST
    )

    if form.is_valid():

        note = form.save(
            commit=False
        )

        note.customer = customer
        note.created_by = (
            request.user
        )

        note.save()

        messages.success(
            request,
            "Customer note added.",
        )

    else:

        messages.error(
            request,
            (
                "The customer note "
                "could not be saved."
            ),
        )

    return redirect(
        "crm_customer_detail",
        pk=customer.pk,
    )


# ============================================================
# PIN / UNPIN NOTE
# ============================================================

@staff_member_required
def customer_note_toggle_pin(
    request,
    pk,
    note_id,
):

    customer = get_object_or_404(
        User,
        pk=pk,
        role=User.CUSTOMER,
    )

    note = get_object_or_404(
        CustomerNote,
        pk=note_id,
        customer=customer,
    )

    if request.method == "POST":

        note.is_pinned = (
            not note.is_pinned
        )

        note.save(
            update_fields=[
                "is_pinned",
                "updated_at",
            ]
        )

        messages.success(
            request,
            (
                "Note pinned."
                if note.is_pinned
                else "Note unpinned."
            ),
        )

    return redirect(
        "crm_customer_detail",
        pk=customer.pk,
    )


# ============================================================
# DELETE NOTE
# ============================================================

@staff_member_required
def customer_note_delete(
    request,
    pk,
    note_id,
):

    customer = get_object_or_404(
        User,
        pk=pk,
        role=User.CUSTOMER,
    )

    note = get_object_or_404(
        CustomerNote,
        pk=note_id,
        customer=customer,
    )

    if request.method == "POST":

        note.delete()

        messages.success(
            request,
            "Customer note deleted.",
        )

    return redirect(
        "crm_customer_detail",
        pk=customer.pk,
    )


# ============================================================
# ACTIVATE / DEACTIVATE CUSTOMER
# ============================================================

@staff_member_required
def customer_toggle_status(
    request,
    pk,
):

    customer = get_object_or_404(
        User,
        pk=pk,
        role=User.CUSTOMER,
    )

    if request.method != "POST":

        return redirect(
            "crm_customer_detail",
            pk=customer.pk,
        )

    customer.is_active = (
        not customer.is_active
    )

    customer.save(
        update_fields=[
            "is_active"
        ]
    )

    messages.success(
        request,
        (
            f'Customer "{customer.username}" '
            f'is now '
            f'{"active" if customer.is_active else "inactive"}.'
        ),
    )

    return redirect(
        "crm_customer_detail",
        pk=customer.pk,
    )


# ============================================================
# CUSTOMER CSV EXPORT
# ============================================================

@staff_member_required
def customer_export_csv(
    request,
):

    response = HttpResponse(
        content_type=(
            "text/csv; charset=utf-8"
        ),
    )

    response[
        "Content-Disposition"
    ] = (
        'attachment; '
        'filename="customers.csv"'
    )

    response.write(
        "\ufeff"
    )

    writer = csv.writer(
        response
    )

    writer.writerow([
        "Username",
        "First Name",
        "Last Name",
        "Email",
        "Phone",
        "Status",
        "Email Verified",
        "Total Orders",
        "Paid Orders",
        "Lifetime Spend",
        "Joined",
        "Last Order",
    ])

    customers = (
        customer_queryset()
        .order_by(
            "-date_joined"
        )
    )

    for customer in customers:

        writer.writerow([
            customer.username,
            customer.first_name,
            customer.last_name,
            customer.email,
            customer.phone,
            (
                "Active"
                if customer.is_active
                else "Inactive"
            ),
            (
                "Yes"
                if customer.email_verified
                else "No"
            ),
            customer.total_orders,
            customer.paid_orders,
            customer.lifetime_spend,
            customer.date_joined,
            (
                customer.last_order_at
                or ""
            ),
        ])

    return response
