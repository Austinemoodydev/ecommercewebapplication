from django.contrib.auth.decorators import login_required

from django.shortcuts import (
    get_object_or_404,
    render,
)

from orders.models import Order

from orders.guest_access import (
    verify_guest_access_token,
)

from .models import (
    Delivery,
    DeliveryZone,
)


@login_required
def customer_delivery_tracking(
    request,
    order_number,
):

    order = get_object_or_404(
        Order.objects.select_related(
            "user"
        ),
        order_number=order_number,
        user=request.user,
    )

    delivery = get_object_or_404(
        Delivery.objects.select_related(
            "provider",
            "order",
        ),
        order=order,
    )

    events = (
        delivery.events
        .select_related(
            "created_by"
        )
        .order_by(
            "created_at"
        )
    )

    return render(
        request,
        "delivery/customer_tracking.html",
        {
            "order": order,
            "delivery": delivery,
            "events": events,
        },
    )




def guest_delivery_tracking(
    request,
    order_number,
    token,
):

    order = get_object_or_404(
        Order.objects.select_related(
            "user"
        ),
        order_number=order_number,
        user__isnull=True,
        guest_checkout=True,
    )


    if not verify_guest_access_token(
        order,
        token,
    ):

        from django.http import Http404

        raise Http404(
            "Order not found."
        )


    delivery = get_object_or_404(
        Delivery.objects.select_related(
            "provider",
            "order",
        ),
        order=order,
    )


    events = (
        delivery.events
        .select_related(
            "created_by"
        )
        .order_by(
            "created_at"
        )
    )


    return render(
        request,
        "delivery/customer_tracking.html",
        {
            "order": order,
            "delivery": delivery,
            "events": events,
            "is_guest_tracking": True,
            "guest_access_token": token,
        },
    )


@login_required
def available_delivery_options(
    request,
):

    county = request.GET.get(
        "county",
        "",
    ).strip()

    town = request.GET.get(
        "town",
        "",
    ).strip()

    zones = (
        DeliveryZone.objects
        .filter(
            is_active=True
        )
        .select_related(
            "provider"
        )
    )

    if county:

        zones = zones.filter(
            county__iexact=county
        )

    if town:

        zones = zones.filter(
            town__iexact=town
        )

    return render(
        request,
        "delivery/customer_options.html",
        {
            "zones": zones,
            "county": county,
            "town": town,
        },
    )
