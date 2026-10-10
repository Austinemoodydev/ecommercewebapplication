from django.urls import path

from . import campaign_views


urlpatterns = [
    path("", campaign_views.campaign_list, name="campaign_list"),
    path("add/", campaign_views.campaign_create, name="campaign_create"),
    path("<int:pk>/", campaign_views.campaign_detail, name="campaign_detail"),
    path("<int:pk>/edit/", campaign_views.campaign_edit, name="campaign_edit"),
    path("<int:pk>/approve/", campaign_views.campaign_approve, name="campaign_approve"),
    path("<int:pk>/disable/", campaign_views.campaign_disable, name="campaign_disable"),
    path("<int:pk>/send/", campaign_views.campaign_send, name="campaign_send"),
    path("<int:pk>/test/", campaign_views.campaign_test_message, name="campaign_test_message"),
]
