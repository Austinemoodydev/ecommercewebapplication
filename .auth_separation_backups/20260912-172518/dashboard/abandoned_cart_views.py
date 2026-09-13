from decimal import Decimal

from django.contrib.admin.views.decorators import (
    staff_member_required,
)

from django.core.paginator import Paginator

from django.db.models import (
    Prefetch,
    Q,
)

from django.shortcuts import (
    get_object_or_404,
    render,
)

from django.utils import timezone


from cart.models import (
    Cart,
    CartItem,
)

from cart.selectors.abandoned_cart_selector import (
    AbandonedCartSelector,
)


def _cart_items_queryset():

    return (
        CartItem.objects
        .select_related(
            "product",
            "variant",
        )
        .order_by(
            "created_at",
            "id",
        )
    )



def _decorate_cart(
    cart,
    *,
    now=None,
):

    if now is None:
        now = timezone.now()


    items = list(
        cart.items.all()
    )


    cart.admin_items = items

    cart.admin_item_count = sum(
        item.quantity
        for item in items
    )


    cart.admin_value = sum(
        (
            item.subtotal
            for item in items
        ),
        Decimal("0.00"),
    )


    if cart.last_activity_at:

        age = (
            now
            - cart.last_activity_at
        )

        total_seconds = max(
            int(age.total_seconds()),
            0,
        )

        cart.admin_age_hours = (
            total_seconds // 3600
        )

        cart.admin_age_days = (
            cart.admin_age_hours // 24
        )

    else:

        cart.admin_age_hours = 0
        cart.admin_age_days = 0


    cart.admin_customer_type = (
        "Customer"
        if cart.user_id
        else
        "Guest"
    )


    if cart.user_id:

        cart.admin_identity = (
            cart.user.get_full_name()
            or
            cart.user.email
            or
            cart.user.username
        )

    else:

        cart.admin_identity = (
            "Guest session"
        )


    return cart



def _base_abandoned_queryset():

    return (
        AbandonedCartSelector
        .abandoned()
        .select_related(
            "user"
        )
        .prefetch_related(
            Prefetch(
                "items",
                queryset=(
                    _cart_items_queryset()
                ),
            )
        )
    )



@staff_member_required
def admin_abandoned_cart_list(
    request,
):

    queryset = (
        _base_abandoned_queryset()
    )


    customer_type = (
        request.GET.get(
            "type",
            "",
        ).strip()
    )


    checkout_state = (
        request.GET.get(
            "checkout",
            "",
        ).strip()
    )


    search = (
        request.GET.get(
            "q",
            "",
        ).strip()
    )


    if customer_type == "customer":

        queryset = queryset.filter(
            user__isnull=False
        )


    elif customer_type == "guest":

        queryset = queryset.filter(
            user__isnull=True
        )


    if checkout_state == "started":

        queryset = queryset.filter(
            checkout_started_at__isnull=False
        )


    elif checkout_state == "not_started":

        queryset = queryset.filter(
            checkout_started_at__isnull=True
        )


    if search:

        queryset = queryset.filter(
            Q(
                user__username__icontains=
                    search
            )
            |
            Q(
                user__email__icontains=
                    search
            )
            |
            Q(
                user__first_name__icontains=
                    search
            )
            |
            Q(
                user__last_name__icontains=
                    search
            )
            |
            Q(
                session_key__icontains=
                    search
            )
            |
            Q(
                items__product__name__icontains=
                    search
            )
            |
            Q(
                items__product__sku__icontains=
                    search
            )
        ).distinct()


    queryset = queryset.order_by(
        "last_activity_at",
        "pk",
    )


    all_abandoned = list(
        _base_abandoned_queryset()
    )


    now = timezone.now()


    total_value = Decimal(
        "0.00"
    )

    registered_count = 0
    guest_count = 0
    checkout_started_count = 0


    for cart in all_abandoned:

        _decorate_cart(
            cart,
            now=now,
        )


        total_value += (
            cart.admin_value
        )


        if cart.user_id:

            registered_count += 1

        else:

            guest_count += 1


        if cart.checkout_started_at:

            checkout_started_count += 1


    paginator = Paginator(
        queryset,
        25,
    )


    page = paginator.get_page(
        request.GET.get("page")
    )


    for cart in page.object_list:

        _decorate_cart(
            cart,
            now=now,
        )


    context = {
        "page_obj":
            page,

        "carts":
            page.object_list,

        "total_abandoned":
            len(all_abandoned),

        "total_value":
            total_value,

        "registered_count":
            registered_count,

        "guest_count":
            guest_count,

        "checkout_started_count":
            checkout_started_count,

        "selected_type":
            customer_type,

        "selected_checkout":
            checkout_state,

        "search":
            search,
    }


    return render(
        request,
        (
            "dashboard/admin/"
            "abandoned_carts/list.html"
        ),
        context,
    )



@staff_member_required
def admin_abandoned_cart_detail(
    request,
    pk,
):

    abandoned_ids = (
        AbandonedCartSelector
        .abandoned()
        .values_list(
            "pk",
            flat=True,
        )
    )


    cart = get_object_or_404(
        Cart.objects
        .select_related(
            "user"
        )
        .prefetch_related(
            Prefetch(
                "items",
                queryset=(
                    _cart_items_queryset()
                ),
            )
        ),
        pk=pk,
        pk__in=abandoned_ids,
    )


    _decorate_cart(
        cart
    )


    return render(
        request,
        (
            "dashboard/admin/"
            "abandoned_carts/detail.html"
        ),
        {
            "cart": cart,
        },
    )
