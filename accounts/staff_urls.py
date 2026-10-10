from django.urls import path

from .views import StoreStaffLoginView
from . import staff_management
from . import staff_mfa


urlpatterns = [

    path(
        "login/",
        StoreStaffLoginView.as_view(),
        name="staff_login",
    ),
    path("mfa/verify/", staff_mfa.staff_mfa_challenge, name="staff_mfa_challenge"),
    path("mfa/setup/", staff_mfa.staff_mfa_setup, name="staff_mfa_setup"),
    path("mfa/recovery-codes/", staff_mfa.staff_mfa_recovery_codes, name="staff_mfa_recovery_codes"),
    path("mfa/cancel/", staff_mfa.staff_mfa_cancel, name="staff_mfa_cancel"),


    path(
        "manage/",
        staff_management.staff_list,
        name="staff_manage_list",
    ),

    path(
        "manage/add/",
        staff_management.staff_create,
        name="staff_manage_create",
    ),

    path(
        "manage/<int:pk>/edit/",
        staff_management.staff_edit,
        name="staff_manage_edit",
    ),

    path(
        "manage/<int:pk>/toggle-active/",
        staff_management.staff_toggle_active,
        name="staff_manage_toggle_active",
    ),
    path(
        "manage/<int:pk>/reset-mfa/",
        staff_management.staff_reset_mfa,
        name="staff_manage_reset_mfa",
    ),
]
