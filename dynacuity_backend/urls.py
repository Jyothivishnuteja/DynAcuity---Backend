"""
URL configuration for dynacuity_backend project.
"""

from django.contrib import admin
from django.urls import path, re_path
from django.http import JsonResponse

from accounts.views import (
    RegisterAPI,
    LoginAPI,
    UserAPI,
    ForgotPasswordAPI,
    ResetPasswordAPI,
    GoogleLoginAPI,
    GameResultAPI,
    HealthCheckAPI,
    RequestSignupOTPAPI,
)


print("DEBUG: Loading dynacuity_backend/urls.py")


# ============================================================
# API DEBUG CATCH-ALL
# ============================================================

def debug_catch_all(request, path):
    print(
        f"DEBUG Catch-all: Received request for "
        f"path '{path}' [{request.method}]"
    )

    print(
        f"DEBUG Full Path: {request.path}"
    )

    return JsonResponse(
        {
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
                "api/results/",
            ],
        },
        status=404,
    )


# ============================================================
# URL PATTERNS
# ============================================================

urlpatterns = [

    # --------------------------------------------------------
    # Django Admin
    # --------------------------------------------------------

    path(
        "admin/",
        admin.site.urls
    ),


    # --------------------------------------------------------
    # Health Check
    # --------------------------------------------------------

    path(
        "api/health/",
        HealthCheckAPI.as_view(),
        name="api-health"
    ),


    # --------------------------------------------------------
    # Authentication
    # --------------------------------------------------------

    path(
        "api/auth/register/",
        RegisterAPI.as_view(),
        name="api-register"
    ),

    path(
        "api/auth/register/otp/",
        RequestSignupOTPAPI.as_view(),
        name="api-request-signup-otp"
    ),

    path(
        "api/auth/login/",
        LoginAPI.as_view(),
        name="api-login"
    ),

    path(
        "api/auth/google/",
        GoogleLoginAPI.as_view(),
        name="api-google-login"
    ),

    path(
        "api/auth/user/",
        UserAPI.as_view(),
        name="api-user"
    ),

    path(
        "api/auth/forgot-password/",
        ForgotPasswordAPI.as_view(),
        name="api-forgot-password"
    ),

    path(
        "api/auth/reset-password/",
        ResetPasswordAPI.as_view(),
        name="api-reset-password"
    ),


    # --------------------------------------------------------
    # Game Results
    # --------------------------------------------------------

    path(
        "api/results/",    
        GameResultAPI.as_view(),
        name="api-game-results"
    ),


    # --------------------------------------------------------
    # API DEBUG CATCH-ALL
    # MUST BE LAST
    # --------------------------------------------------------

    re_path(
        r"^api/(?P<path>.*)$",
        debug_catch_all
    ),
]
