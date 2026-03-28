"""
URL configuration for dynacuity_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, re_path
from django.http import JsonResponse
from accounts.views import (
    RegisterAPI, LoginAPI, UserAPI, ForgotPasswordAPI, 
    ResetPasswordAPI, GoogleLoginAPI, GameResultAPI, HealthCheckAPI,
    RequestSignupOTPAPI
)

print("DEBUG: Loading dynacuity_backend/urls.py - Flattened Mode")

def debug_catch_all(request, path):
    print(f"DEBUG Catch-all: Received request for path '{path}' [{request.method}]")
    print(f"DEBUG Full Path: {request.path}")
    return JsonResponse({
        "error": "Endpoint not found",
        "captured_path": path,
        "full_path": request.path,
        "method": request.method,
        "available_endpoints": [
            "api/health/",
            "api/auth/register/",
            "api/auth/register/otp/",
            "api/auth/login/",
            "api/auth/google/",
            "api/auth/user/",
            "api/auth/forgot-password/",
            "api/auth/reset-password/",
            "api/results/"
        ],
        "suggestion": "If you are trying to access a static page (e.g. .html), make sure the Proxy server is running on port 3000."
    }, status=404)

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Core API Endpoints
    path('api/health/', HealthCheckAPI.as_view(), name='api-health'),
    path('api/auth/register/', RegisterAPI.as_view(), name='api-register'),
    path('api/auth/register/otp/', RequestSignupOTPAPI.as_view(), name='api-request-signup-otp'),
    path('api/auth/login/', LoginAPI.as_view(), name='api-login'),
    path('api/auth/google/', GoogleLoginAPI.as_view(), name='api-google-login'),
    path('api/auth/user/', UserAPI.as_view(), name='api-user'),
    path('api/auth/forgot-password/', ForgotPasswordAPI.as_view(), name='api-forgot-password'),
    path('api/auth/reset-password/', ResetPasswordAPI.as_view(), name='api-reset-password'),
    path('api/results/', GameResultAPI.as_view(), name='api-game-results'),
]

# Static File Support for Local Development / Fallback
from django.conf import settings
from django.views.static import serve
import os

# Serving static files from DynAcuityWeb as a fallback
urlpatterns += [
    re_path(r'^$', serve, {
        'document_root': r'C:\Users\vishn\AndroidStudioProjects\DynAcuityWeb',
        'path': 'index.html'
    }),
    re_path(r'^(?P<path>.*\.html)$', serve, {
        'document_root': r'C:\Users\vishn\AndroidStudioProjects\DynAcuityWeb',
    }),
    re_path(r'^css/(?P<path>.*)$', serve, {
        'document_root': r'C:\Users\vishn\AndroidStudioProjects\DynAcuityWeb\css',
    }),
    re_path(r'^js/(?P<path>.*)$', serve, {
        'document_root': r'C:\Users\vishn\AndroidStudioProjects\DynAcuityWeb\js',
    }),
    re_path(r'^images/(?P<path>.*)$', serve, {
        'document_root': r'C:\Users\vishn\AndroidStudioProjects\DynAcuityWeb\images',
    }),
    re_path(r'^assets/(?P<path>.*)$', serve, {
        'document_root': r'C:\Users\vishn\AndroidStudioProjects\DynAcuityWeb\assets',
    }),

    # Diagnostic Catch-all for API debugging - MUST BE LAST
    re_path(r'^api/(?P<path>.*)$', debug_catch_all),
]
