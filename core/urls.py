from django.urls import path
from . import views
from . import chatbot

urlpatterns = [
    path('', views.home, name='home'),
    path('terms/', views.legal_page, {'page': 'terms'}, name='terms'),
    path('privacy/', views.legal_page, {'page': 'privacy'}, name='privacy'),
    path('delivery-policy/', views.legal_page, {'page': 'delivery'}, name='delivery_policy'),
    path('refund-policy/', views.legal_page, {'page': 'refund'}, name='refund_policy'),
    path('cookies/', views.legal_page, {'page': 'cookies'}, name='cookie_policy'),
    path('assistant/chat/', chatbot.customer_chat, name='customer_chat'),
    path('assistant/staff-chat/', chatbot.staff_chat, name='staff_chat'),
    path('assistant/transcribe/', chatbot.customer_transcribe, name='customer_transcribe'),
    path('assistant/staff-transcribe/', chatbot.staff_transcribe, name='staff_transcribe'),
]
