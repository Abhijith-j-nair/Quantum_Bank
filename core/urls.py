# core/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # This makes the dashboard your site's homepage
    path('', views.dashboard_view, name='home'),
    
    # This is the specific URL for the signup page
    path('signup/', views.signup_view, name='signup'),

    # Core banking features
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('transfer/', views.transfer_view, name='transfer'),
    path('transactions/', views.transaction_list_view, name='transactions'),
    path('api/transactions/<uuid:transaction_id>/', views.api_transaction_detail, name='api_transaction_detail'),
    path('accounts/', views.dashboard_view, name='accounts'),
    path('accounts/create/', views.create_account_view, name='create_account'),
    path('qr_code/<int:account_id>/', views.qr_code_view, name='qr_code'),
    path('pay/<str:account_number>/', views.pay_me_view, name='pay_me'),
    # commented out until you create these views
    # path('profile/', views.profile_view, name='profile'),
    # path('api/transfer/', views.api_transfer, name='api_transfer'),
]