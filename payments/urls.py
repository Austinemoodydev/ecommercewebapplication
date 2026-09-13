from django.urls import path
from . import views
from . import customer_returns

urlpatterns = [
    path(
        "guest/refund/<str:order_number>/<str:token>/",
        customer_returns.guest_request_refund,
        name="guest_request_refund",
    ),

    path(
        "guest/return/<str:order_number>/<str:token>/",
        customer_returns.guest_request_return,
        name="guest_request_return",
    ),

    path(
        "guest/return/<str:order_number>/<str:token>/<int:pk>/",
        customer_returns.guest_return_detail,
        name="guest_return_detail",
    ),

    path(
        "guest/refund/<str:order_number>/<str:token>/<int:pk>/",
        customer_returns.guest_refund_detail,
        name="guest_refund_detail",
    ),

    path(
        "my-returns/",
        customer_returns.customer_returns_refunds,
        name="customer_returns_refunds",
    ),

    path(
        "my-returns/returns/<int:pk>/",
        customer_returns.customer_return_detail,
        name="customer_return_detail",
    ),

    path(
        "my-returns/refunds/<int:pk>/",
        customer_returns.customer_refund_detail,
        name="customer_refund_detail",
    ),

    path(
        "guest/pay/<str:order_number>/<str:token>/",
        views.initiate_payment,
        name="guest_initiate_payment",
    ),

    path(
        "guest/status/<str:order_number>/<str:token>/",
        views.check_payment_status,
        name="guest_check_payment_status",
    ),

    path("pay/<str:order_number>/", views.initiate_payment, name="initiate_payment"),
    path("callback/", views.mpesa_callback, name="mpesa_callback"),
    path("status/<str:order_number>/", views.check_payment_status, name="check_payment_status"),
    path(
        "refund/<str:order_number>/",
        customer_returns.request_refund,
        name="request_refund",
    ),
    path(
        "return/<str:order_number>/",
        customer_returns.request_return,
        name="request_return",
    ),
]
