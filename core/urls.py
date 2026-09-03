from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('terms/', views.legal_page, {'page': 'terms'}, name='terms'),
    path('privacy/', views.legal_page, {'page': 'privacy'}, name='privacy'),
    path('delivery-policy/', views.legal_page, {'page': 'delivery'}, name='delivery_policy'),
    path('refund-policy/', views.legal_page, {'page': 'refund'}, name='refund_policy'),
    path('cookies/', views.legal_page, {'page': 'cookies'}, name='cookie_policy'),
]
