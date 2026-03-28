from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from .serializers import (
    UserSerializer, RegisterSerializer, LoginSerializer, 
    validate_password_rules, RequestSignupOTPSerializer,
    GameResultSerializer
)
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from django.conf import settings
from .models import User, GameResult, PasswordResetOTP, SignupOTP
import random
import requests
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail

class RequestSignupOTPAPI(generics.GenericAPIView):
    serializer_class = RequestSignupOTPSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        # Generate 6-digit OTP
        otp_code = str(random.randint(100000, 999999))
        
        # Delete old OTPs for this email and create new one
        SignupOTP.objects.filter(email=email).delete()
        SignupOTP.objects.create(email=email, otp=otp_code)

        # Send email via SMTP
        subject = "DynAcuity Email Verification Code"
        message = f"Hello,\n\nYour email verification code for signup is: {otp_code}\n\nPlease enter this code in the app to complete your registration."
        
        try:
            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False,
            )
            return Response({"message": f"Verification code sent to {email}."})
        except Exception as e:
            print(f"Email SMTP Error: {str(e)}")
            # Fallback for development: print to console
            print(f"--- DEVELOPMENT OTP FOR {email}: {otp_code} ---")
            return Response({
                "error": "Failed to send email. If this is development, check the server console for the code.",
                "debug_error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class RegisterAPI(generics.GenericAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        print(f"DEBUG: Register attempt received for email: {request.data.get('email')}")
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                "user": UserSerializer(user, context=self.get_serializer_context()).data,
                "token": token.key
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            print(f"ERROR in RegisterAPI: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class HealthCheckAPI(APIView):
    permission_classes = [permissions.AllowAny]
    def get(self, request):
        return Response({"status": "ok", "message": "Server is reachable"})

class LoginAPI(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            "user": UserSerializer(user, context=self.get_serializer_context()).data,
            "token": token.key
        })

class UserAPI(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

class ForgotPasswordAPI(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
            
            # Generate 6-digit OTP
            otp_code = str(random.randint(100000, 999999))
            PasswordResetOTP.objects.create(user=user, otp=otp_code)
            
            # Send email via SMTP
            subject = "DynAcuity Password Reset Code"
            message = f"Hello,\n\nYour password reset code is: {otp_code}\n\nThis code will expire in 15 minutes."

            try:
                send_mail(
                    subject,
                    message,
                    settings.EMAIL_HOST_USER,
                    [email],
                    fail_silently=False,
                )
                return Response({"message": f"Password reset instructions sent to {email}."})
            except Exception as e:
                print(f"Email SMTP Error: {str(e)}")
                return Response({"error": f"Failed to send email: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except User.DoesNotExist:
            return Response({"error": "User with this email does not exist"}, status=status.HTTP_404_NOT_FOUND)

class ResetPasswordAPI(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')
        otp = request.data.get('otp')
        new_password = request.data.get('new_password')

        if not all([email, otp, new_password]):
            return Response({"error": "Email, OTP and new password are required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
            
            # Verify OTP
            time_threshold = timezone.now() - timedelta(minutes=15)
            otp_record = PasswordResetOTP.objects.filter(
                user=user, 
                otp=otp, 
                created_at__gte=time_threshold
            ).order_by('-created_at').first()
            
            if not otp_record:
                return Response({"error": "Invalid or expired reset code"}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                validate_password_rules(new_password)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

            user.set_password(new_password)
            user.save()
            
            # Clear used OTPs
            PasswordResetOTP.objects.filter(user=user).delete()
            
            return Response({"message": "Password successfully reset"})
        except User.DoesNotExist:
            return Response({"error": "User does not exist"}, status=status.HTTP_404_NOT_FOUND)

class GoogleLoginAPI(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        id_token_str = request.data.get('idToken')
        email = request.data.get('email')
        full_name = request.data.get('full_name', 'Google User')
        
        print(f"DEBUG: Google Login attempt. Token provided: {bool(id_token_str)}")
        
        if id_token_str:
            try:
                idinfo = id_token.verify_oauth2_token(
                    id_token_str, 
                    google_requests.Request()
                )
                email = idinfo['email']
                full_name = idinfo.get('name', full_name)
            except ValueError as e:
                if not settings.DEBUG:
                    return Response({"error": "Invalid Google Token"}, status=status.HTTP_400_BAD_REQUEST)

        if not email:
            return Response({"error": "Email is required for Google Login"}, status=status.HTTP_400_BAD_REQUEST)
        
        user, created = User.objects.get_or_create(email=email, defaults={'full_name': full_name})
        token, _ = Token.objects.get_or_create(user=user)
        
        return Response({
            "user": UserSerializer(user).data,
            "token": token.key
        })

class GameResultAPI(generics.ListCreateAPIView):
    serializer_class = GameResultSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return GameResult.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
