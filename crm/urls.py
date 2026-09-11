from django.urls import path

from . import views


urlpatterns = [

    path(
        "",
        views.customer_list,
        name="crm_customer_list",
    ),

    path(
        "export/",
        views.customer_export_csv,
        name="crm_customer_export_csv",
    ),

    path(
        "<int:pk>/",
        views.customer_detail,
        name="crm_customer_detail",
    ),

    path(
        "<int:pk>/status/",
        views.customer_toggle_status,
        name="crm_customer_toggle_status",
    ),

    path(
        "<int:pk>/notes/add/",
        views.customer_note_add,
        name="crm_customer_note_add",
    ),

    path(
        (
            "<int:pk>/notes/"
            "<int:note_id>/pin/"
        ),
        views.customer_note_toggle_pin,
        name="crm_customer_note_toggle_pin",
    ),

    path(
        (
            "<int:pk>/notes/"
            "<int:note_id>/delete/"
        ),
        views.customer_note_delete,
        name="crm_customer_note_delete",
    ),
]
