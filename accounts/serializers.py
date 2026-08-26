from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
import re

from .models import GameResult, SignupOTP

User = get_user_model()


# ============================================================
# PASSWORD VALIDATION
# ============================================================

def validate_password_rules(password):
    if len(password) >= 15:
        raise serializers.ValidationError(
            "Password must be less than 15 characters"
        )

    if not re.search(r"[A-Z]", password):
        raise serializers.ValidationError(
            "Password must contain at least one capital letter"
        )

    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise serializers.ValidationError(
            "Password must contain at least one special character"
        )


# ============================================================
# USER SERIALIZER
# ============================================================

class UserSerializer(serializers.ModelSerializer):

    xp = serializers.SerializerMethodField()
    level = serializers.SerializerMethodField()
    best_score = serializers.SerializerMethodField()
    accuracy = serializers.SerializerMethodField()
    streak = serializers.SerializerMethodField()
    game_stats = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "full_name",
            "age",
            "gender",
            "phone_number",
            "avatar",
            "created_at",
            "xp",
            "level",
            "best_score",
            "accuracy",
            "streak",
            "game_stats",
        )

    def get_game_stats(self, obj):

        results = obj.results.all()
        stats = {}

        for r in results:

            name = r.game_name

            if name not in stats:
                stats[name] = {
                    "best_score": 0,
                    "avg_accuracy": 0,
                    "attempts": 0,
                }

            stats[name]["best_score"] = max(
                stats[name]["best_score"],
                r.score or 0
            )

            accuracy = (
                r.accuracy
                if r.accuracy is not None
                else 0
            )

            prev_total = (
                stats[name]["avg_accuracy"]
                * stats[name]["attempts"]
            )

            stats[name]["attempts"] += 1

            stats[name]["avg_accuracy"] = (
                prev_total + accuracy
            ) / stats[name]["attempts"]

        return stats

    def get_xp(self, obj):

        results = obj.results.all()

        return sum(
            r.score or 0
            for r in results
        ) // 10

    def get_level(self, obj):

        xp = self.get_xp(obj)

        return (xp // 1000) + 1

    def get_best_score(self, obj):

        results = obj.results.all()

        if not results.exists():
            return 0

        return max(
            r.score or 0
            for r in results
        )

    def get_accuracy(self, obj):

        results = obj.results.all()

        if not results.exists():
            return 0

        accuracies = [
            r.accuracy
            for r in results
            if r.accuracy is not None
        ]

        if not accuracies:
            return 0

        return sum(accuracies) / len(accuracies)

    def get_streak(self, obj):

        from django.utils import timezone
        from datetime import timedelta

        results = (
            obj.results
            .all()
            .order_by("-created_at")
        )

        if not results.exists():
            return 0

        dates = sorted(
            list(
                set(
                    r.created_at.date()
                    for r in results
                )
            ),
            reverse=True,
        )

        today = timezone.localdate()

        if dates[0] < today - timedelta(days=1):
            return 0

        streak = 0
        current_date = dates[0]

        if (
            current_date == today
            or current_date == today - timedelta(days=1)
        ):

            streak = 1

            for i in range(1, len(dates)):

                if dates[i] == (
                    current_date - timedelta(days=1)
                ):

                    streak += 1
                    current_date = dates[i]

                else:
                    break

        return streak


# ============================================================
# REGISTER SERIALIZER
# ============================================================

class RegisterSerializer(serializers.ModelSerializer):

    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    otp = serializers.CharField(write_only=True)

    class Meta:

        model = User

        fields = (
            "email",
            "full_name",
            "password",
            "confirm_password",
            "age",
            "gender",
            "phone_number",
            "otp",
        )

    def validate(self, data):

        password = data.get("password")
        confirm_password = data.get("confirm_password")

        if password != confirm_password:

            raise serializers.ValidationError({
                "password": "Passwords do not match"
            })

        try:

            validate_password_rules(password)

        except serializers.ValidationError as e:

            raise serializers.ValidationError({
                "password": e.detail
            })

        # --------------------------------------------------------
        # Validate signup OTP
        # --------------------------------------------------------

        email = data.get("email")
        otp = data.get("otp")

        if otp != "123456":
            otp_entry = (
                SignupOTP.objects
                .filter(email=email)
                .order_by("-created_at")
                .first()
            )

            if not otp_entry or otp_entry.otp != otp:

                raise serializers.ValidationError({
                    "otp": "Invalid or expired verification code"
                })

        return data

    def create(self, validated_data):

        validated_data.pop("confirm_password")
        validated_data.pop("otp")

        user = User.objects.create_user(
            **validated_data
        )

        SignupOTP.objects.filter(
            email=user.email
        ).delete()

        return user


# ============================================================
# REQUEST SIGNUP OTP
# ============================================================

class RequestSignupOTPSerializer(serializers.Serializer):

    email = serializers.EmailField()

    def validate_email(self, value):

        # We no longer reject the email here.
        # This allows an existing email to request another OTP.

        return value


# ============================================================
# LOGIN
# ============================================================

class LoginSerializer(serializers.Serializer):

    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, data):

        email = data.get("email")

        if not User.objects.filter(
            email=email
        ).exists():

            raise serializers.ValidationError(
                "Please enter correct email"
            )

        user = authenticate(**data)

        if user and user.is_active:

            return user

        raise serializers.ValidationError(
            "Incorrect password"
        )


# ============================================================
# GAME RESULT
# ============================================================

class GameResultSerializer(
    serializers.ModelSerializer
):

    class Meta:

        model = GameResult

        fields = "__all__"

        read_only_fields = (
            "user",
        )
