from django.urls import path
from .views import (
    RegisterAPI, LoginAPI, UserAPI, ForgotPasswordAPI, 
    ResetPasswordAPI, GoogleLoginAPI, GameResultAPI, HealthCheckAPI,
    RequestSignupOTPAPI
)

print("DEBUG: Loading accounts/urls.py")

urlpatterns = [
    path('health/', HealthCheckAPI.as_view(), name='health-check'),
    path('auth/register/', RegisterAPI.as_view(), name='register'),
    path('auth/register/otp/', RequestSignupOTPAPI.as_view(), name='request-signup-otp'),
    path('auth/login/', LoginAPI.as_view(), name='login'),
    path('auth/google/', GoogleLoginAPI.as_view(), name='google-login'),
    path('auth/user/', UserAPI.as_view(), name='user'),
    path('auth/forgot-password/', ForgotPasswordAPI.as_view(), name='forgot-password'),
    path('auth/reset-password/', ResetPasswordAPI.as_view(), name='reset-password'),
    path('results/', GameResultAPI.as_view(), name='game-results'),
]
