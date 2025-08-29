# quantum/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # This line handles login, logout, password reset, etc.
    path('accounts/', include('django.contrib.auth.urls')), 
    # This line sends all other requests to your app's urls.py file
    path('', include('core.urls')),
]