from django.urls import path

from .robots import robots_txt


urlpatterns = [path("", robots_txt, name="robots")]