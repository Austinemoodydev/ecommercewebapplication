from django.urls import path

from . import views


urlpatterns = [


    path(
        "<int:pk>/quote/",
        views.delivery_set_quote,
        name="delivery_set_quote",
    ),

    path(
        "zones/",
        views.delivery_zone_list,
        name="delivery_zone_list",
    ),

    path(
        "zones/add/",
        views.delivery_zone_create,
        name="delivery_zone_create",
    ),

    path(
        "zones/<int:pk>/edit/",
        views.delivery_zone_edit,
        name="delivery_zone_edit",
    ),

    path(
        "zones/<int:pk>/toggle/",
        views.delivery_zone_toggle,
        name="delivery_zone_toggle",
    ),

    path(
        "pickup-points/",
        views.pickup_point_list,
        name="delivery_pickup_point_list",
    ),
    path(
        "pickup-points/add/",
        views.pickup_point_create,
        name="delivery_pickup_point_create",
    ),
    path(
        "pickup-points/<int:pk>/edit/",
        views.pickup_point_edit,
        name="delivery_pickup_point_edit",
    ),
    path(
        "pickup-points/<int:pk>/toggle/",
        views.pickup_point_toggle,
        name="delivery_pickup_point_toggle",
    ),


    path(
        "",
        views.delivery_list,
        name="delivery_list",
    ),

    path(
        "providers/",
        views.provider_list,
        name="delivery_provider_list",
    ),

    path(
        "providers/add/",
        views.provider_create,
        name="delivery_provider_create",
    ),

    path(
        "providers/<int:pk>/edit/",
        views.provider_edit,
        name="delivery_provider_edit",
    ),

    path(
        "providers/<int:pk>/toggle/",
        views.provider_toggle,
        name="delivery_provider_toggle",
    ),

    path(
        "order/<str:order_number>/assign/",
        views.delivery_assign,
        name="delivery_assign",
    ),

    path(
        "<int:pk>/",
        views.delivery_detail,
        name="delivery_detail",
    ),

    path(
        "<int:pk>/status/",
        views.delivery_update_status,
        name="delivery_update_status",
    ),

    path(
        "<int:pk>/attempt/",
        views.delivery_add_attempt,
        name="delivery_add_attempt",
    ),
]
