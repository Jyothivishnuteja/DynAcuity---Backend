from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from .serializers import (
    UserSerializer,
    RegisterSerializer,
    LoginSerializer,
    validate_password_rules,
    RequestSignupOTPSerializer,
    GameResultSerializer,
)

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from django.conf import settings
from .models import (
    User,
    GameResult,
    PasswordResetOTP,
    SignupOTP,
)

import random
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail


# ============================================================
# SIGNUP OTP
# ============================================================

class RequestSignupOTPAPI(generics.GenericAPIView):
    serializer_class = RequestSignupOTPSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        # Generate 6-digit OTP
        otp_code = str(random.randint(100000, 999999))

        # Delete old OTPs
        SignupOTP.objects.filter(email=email).delete()

        # Create new OTP
        SignupOTP.objects.create(
            email=email,
            otp=otp_code
        )

        subject = "DynAcuity Email Verification Code"

        message = (
            f"Hello,\n\n"
            f"Your email verification code for signup is: {otp_code}\n\n"
            f"Please enter this code in the app to complete your registration."
        )

        try:

            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False,
            )

            return Response(
                {
                    "message": f"Verification code sent to {email}."
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:

            print("Email SMTP Error:", str(e))

            print(
                f"--- DEVELOPMENT OTP FOR {email}: {otp_code} ---"
            )

            return Response(
                {
                    "error": "Failed to send email.",
                    "debug_error": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================================================
# REGISTER
# ============================================================

class RegisterAPI(generics.GenericAPIView):

    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):

        print(
            f"DEBUG: Register attempt received for email: "
            f"{request.data.get('email')}"
        )

        try:

            serializer = self.get_serializer(
                data=request.data
            )

            serializer.is_valid(
                raise_exception=True
            )

            user = serializer.save()

            token, created = Token.objects.get_or_create(
                user=user
            )

            return Response(
                {
                    "user": UserSerializer(
                        user,
                        context=self.get_serializer_context()
                    ).data,

                    "token": token.key,
                },
                status=status.HTTP_201_CREATED
            )

        except Exception as e:

            print(
                "ERROR in RegisterAPI:",
                str(e)
            )

            return Response(
                {
                    "error": str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )


# ============================================================
# HEALTH CHECK
# ============================================================

class HealthCheckAPI(APIView):

    permission_classes = [
        permissions.AllowAny
    ]

    def get(self, request):

        return Response(
            {
                "status": "ok",
                "message": "Server is reachable"
            }
        )


# ============================================================
# LOGIN
# ============================================================

class LoginAPI(generics.GenericAPIView):

    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):

        serializer = self.get_serializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        user = serializer.validated_data

        token, created = Token.objects.get_or_create(
            user=user
        )

        return Response(
            {
                "user": UserSerializer(
                    user,
                    context=self.get_serializer_context()
                ).data,

                "token": token.key,
            }
        )


# ============================================================
# USER
# ============================================================

class UserAPI(generics.RetrieveUpdateAPIView):

    permission_classes = [
        permissions.IsAuthenticated
    ]

    serializer_class = UserSerializer

    def get_object(self):

        return self.request.user


# ============================================================
# FORGOT PASSWORD
# ============================================================

class ForgotPasswordAPI(APIView):

    permission_classes = [
        permissions.AllowAny
    ]

    def post(self, request):

        email = request.data.get("email")

        # ----------------------------------------------------
        # Validate email
        # ----------------------------------------------------

        if not email:

            return Response(
                {
                    "error": "Email is required"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:

            # ------------------------------------------------
            # Find user
            # ------------------------------------------------

            user = User.objects.get(
                email=email
            )

            # ------------------------------------------------
            # Generate OTP
            # ------------------------------------------------

            otp_code = str(
                random.randint(
                    100000,
                    999999
                )
            )

            # ------------------------------------------------
            # Delete old OTPs
            # ------------------------------------------------

            PasswordResetOTP.objects.filter(
                user=user
            ).delete()

            # ------------------------------------------------
            # Create new OTP
            # ------------------------------------------------

            PasswordResetOTP.objects.create(
                user=user,
                otp=otp_code
            )

            # ------------------------------------------------
            # Email
            # ------------------------------------------------

            subject = (
                "DynAcuity Password Reset Code"
            )

            message = (
                f"Hello,\n\n"
                f"Your password reset code is: "
                f"{otp_code}\n\n"
                f"This code will expire in 15 minutes.\n\n"
                f"If you did not request this code, "
                f"please ignore this email."
            )

            # ------------------------------------------------
            # Send email
            # ------------------------------------------------

            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False,
            )

            return Response(
                {
                    "message": (
                        "Password reset instructions "
                        "sent successfully."
                    )
                },
                status=status.HTTP_200_OK
            )

        # ----------------------------------------------------
        # User does not exist
        # ----------------------------------------------------

        except User.DoesNotExist:

            return Response(
                {
                    "error": (
                        "User with this email "
                        "does not exist"
                    )
                },
                status=status.HTTP_404_NOT_FOUND
            )

        # ----------------------------------------------------
        # Any other error
        # ----------------------------------------------------

        except Exception as e:

            print(
                "ERROR in ForgotPasswordAPI:",
                str(e)
            )

            return Response(
                {
                    "error": (
                        "Failed to process "
                        "password reset request."
                    ),

                    "debug_error": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================================================
# RESET PASSWORD
# ============================================================

class ResetPasswordAPI(APIView):

    permission_classes = [
        permissions.AllowAny
    ]

    def post(self, request):

        email = request.data.get("email")
        otp = request.data.get("otp")
        new_password = request.data.get(
            "new_password"
        )

        # ----------------------------------------------------
        # Validate fields
        # ----------------------------------------------------

        if not all(
            [
                email,
                otp,
                new_password
            ]
        ):

            return Response(
                {
                    "error": (
                        "Email, OTP and new password "
                        "are required"
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:

            user = User.objects.get(
                email=email
            )

            # ------------------------------------------------
            # OTP expiration
            # ------------------------------------------------

            time_threshold = (
                timezone.now()
                - timedelta(minutes=15)
            )

            otp_record = (
                PasswordResetOTP.objects
                .filter(
                    user=user,
                    otp=otp,
                    created_at__gte=time_threshold
                )
                .order_by("-created_at")
                .first()
            )

            # ------------------------------------------------
            # Invalid OTP
            # ------------------------------------------------

            if not otp_record:

                return Response(
                    {
                        "error": (
                            "Invalid or expired "
                            "reset code"
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # ------------------------------------------------
            # Validate password
            # ------------------------------------------------

            try:

                validate_password_rules(
                    new_password
                )

            except Exception as e:

                return Response(
                    {
                        "error": str(e)
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # ------------------------------------------------
            # Change password
            # ------------------------------------------------

            user.set_password(
                new_password
            )

            user.save()

            # ------------------------------------------------
            # Delete used OTP
            # ------------------------------------------------

            PasswordResetOTP.objects.filter(
                user=user
            ).delete()

            return Response(
                {
                    "message": (
                        "Password successfully reset"
                    )
                },
                status=status.HTTP_200_OK
            )

        except User.DoesNotExist:

            return Response(
                {
                    "error": "User does not exist"
                },
                status=status.HTTP_404_NOT_FOUND
            )


# ============================================================
# GOOGLE LOGIN
# ============================================================

class GoogleLoginAPI(APIView):

    permission_classes = [
        AllowAny
    ]

    def post(
        self,
        request,
        *args,
        **kwargs
    ):

        id_token_str = request.data.get(
            "idToken"
        )

        email = request.data.get(
            "email"
        )

        full_name = request.data.get(
            "full_name",
            "Google User"
        )

        print(
            "DEBUG: Google Login attempt. "
            f"Token provided: {bool(id_token_str)}"
        )

        # ----------------------------------------------------
        # Verify Google token
        # ----------------------------------------------------

        if id_token_str:

            try:

                idinfo = id_token.verify_oauth2_token(
                    id_token_str,
                    google_requests.Request()
                )

                email = idinfo["email"]

                full_name = idinfo.get(
                    "name",
                    full_name
                )

            except ValueError:

                if not settings.DEBUG:

                    return Response(
                        {
                            "error": (
                                "Invalid Google Token"
                            )
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

        # ----------------------------------------------------
        # Validate email
        # ----------------------------------------------------

        if not email:

            return Response(
                {
                    "error": (
                        "Email is required "
                        "for Google Login"
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ----------------------------------------------------
        # Create / get user
        # ----------------------------------------------------

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "full_name": full_name
            }
        )

        # ----------------------------------------------------
        # Create / get token
        # ----------------------------------------------------

        token, _ = Token.objects.get_or_create(
            user=user
        )

        return Response(
            {
                "user": UserSerializer(
                    user
                ).data,

                "token": token.key,
            }
        )


# ============================================================
# GAME RESULTS
# ============================================================

class GameResultAPI(
    generics.ListCreateAPIView
):

    serializer_class = GameResultSerializer

    permission_classes = [
        permissions.IsAuthenticated
    ]

    def get_queryset(self):

        return (
            GameResult.objects
            .filter(
                user=self.request.user
            )
            .order_by("-created_at")
        )

    def perform_create(
        self,
        serializer
    ):

        serializer.save(
            user=self.request.user
        )
