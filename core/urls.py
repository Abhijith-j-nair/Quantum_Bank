# core/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='home'),
    path('signup/', views.signup_view, name='signup'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('transfer/', views.transfer_view, name='transfer'),
    path('scan/', views.scan_and_pay_view, name='scan_and_pay'),
    path('transactions/', views.transaction_list_view, name='transactions'),
    path('api/transactions/<uuid:transaction_id>/', views.api_transaction_detail, name='api_transaction_detail'),
    path('accounts/', views.dashboard_view, name='accounts'),
    path('accounts/create/', views.create_account_view, name='create_account'),
    path('qr_code/<int:account_id>/', views.qr_code_view, name='qr_code'),
    path('pay/<str:account_number>/', views.pay_me_view, name='pay_me'),

    # Paths for the chatbot feature
    path('api/chatbot/', views.chatbot_api_view, name='chatbot_api'),
    path('chatbot/', views.chatbot_view, name='chatbot'),
]