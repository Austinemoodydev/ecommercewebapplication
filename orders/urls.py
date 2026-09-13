from django.urls import path
from . import views
from . import document_views

from delivery.customer_views import (
    guest_delivery_tracking,
)

urlpatterns = [
    path("", views.checkout, name="checkout"),
    path(
        "guest/<str:order_number>/<str:token>/confirmation/",
        views.guest_order_confirmation,
        name="guest_order_confirmation",
    ),
    path(
        "guest/<str:order_number>/<str:token>/",
        views.guest_order_detail,
        name="guest_order_detail",
    ),
    path(
        "guest/<str:order_number>/<str:token>/track/",
        guest_delivery_tracking,
        name="guest_delivery_tracking",
    ),

    path(
        "guest/<str:order_number>/<str:token>/invoice/",
        document_views.guest_invoice,
        name="guest_order_invoice",
    ),

    path(
        "guest/<str:order_number>/<str:token>/receipt/",
        document_views.guest_receipt,
        name="guest_order_receipt",
    ),
    path("confirmation/<str:order_number>/", views.order_confirmation, name="order_confirmation"),
    path("<str:order_number>/cancel/", views.cancel_order, name="cancel_order"),
    path("apply-coupon/", views.apply_coupon, name="apply_coupon"),
    path("remove-coupon/", views.remove_coupon, name="remove_coupon"),
]
