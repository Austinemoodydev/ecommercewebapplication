from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path(
        "claim-order/<str:order_number>/<str:token>/",
        views.claim_guest_order,
        name="claim_guest_order",
    ),
    path("register/", views.register, name="register"),
    path("verify-email/<uidb64>/<token>/", views.verify_email, name="verify_email"),
    path("login/", views.RateLimitedLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="home"), name="logout"),
    path("profile/", views.profile, name="profile"),
    path("password-reset/", auth_views.PasswordResetView.as_view(
        template_name="accounts/reset_password.html",
        email_template_name="accounts/password_reset_email.html",
        subject_template_name="accounts/password_reset_subject.txt",
    ), name="password_reset"),
    path("password-reset/done/", auth_views.PasswordResetDoneView.as_view(
        template_name="accounts/password_reset_done.html",
    ), name="password_reset_done"),
    path("password-reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="accounts/password_reset_confirm.html",
    ), name="password_reset_confirm"),
    path("password-reset/complete/", auth_views.PasswordResetCompleteView.as_view(
        template_name="accounts/password_reset_complete.html",
    ), name="password_reset_complete"),
    path("addresses/", views.addresses, name="addresses"),
    path("addresses/add/", views.add_address, name="add_address"),
    path("addresses/<int:address_id>/delete/", views.delete_address, name="delete_address"),
    path("addresses/<int:address_id>/default/", views.set_default_address, name="set_default_address"),
]
