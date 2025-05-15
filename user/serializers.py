from .models import CustomUser, Bmi
from rest_framework import serializers
import phonenumbers
# from utils.exceptions import BaseApiException # Assuming this is your custom exception
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer # For custom login serializer
from django.contrib.auth import get_user_model

User = get_user_model() # Use this instead of CustomUser directly if CustomUser is your AUTH_USER_MODEL

class RegisterSerializer(serializers.ModelSerializer):
    password1 = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, min_length=8)
    email = serializers.EmailField(required=True) # Added email, assuming it's part of your registration
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User # Use User (get_user_model())
        fields = ['username', 'email', 'password1', 'password2', 'phone', 'first_name', 'last_name']

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value

    def validate(self, data):
        if data['password1'] != data['password2']:
            raise serializers.ValidationError({'password': 'Password did not match'})
        if data.get('phone'): # Check if phone exists
            try:
                phone_number = phonenumbers.parse(data['phone'], None)
                if not phonenumbers.is_valid_number(phone_number):
                    raise serializers.ValidationError("Invalid phone number format.")
                data['phone'] = phonenumbers.format_number(phone_number, phonenumbers.PhoneNumberFormat.E164)
            except phonenumbers.NumberParseException:
                raise serializers.ValidationError("Invalid phone number.")
        return data

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'], # Save email
            password=validated_data['password1'],
        )
        # Save optional fields
        user.phone = validated_data.get('phone')
        user.first_name = validated_data.get('first_name', '')
        user.last_name = validated_data.get('last_name', '')
        user.save()
        return user

class VerifySerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    code = serializers.IntegerField()

    def validate_user_id(self, value): # Renamed from validate to validate_user_id for clarity
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError('user not found')
        return value

    def save(self, **kwargs):
        code = self.validated_data.get('code')
        user_id = self.validated_data.get("user_id")

        if code != 123456: # Replace with secure OTP
            # from utils.exceptions import BaseApiException # Or use DRF's ValidationError
            raise serializers.ValidationError({"code": "Code did not match"})
        
        user = User.objects.get(id=user_id)
        # user.is_verified = True # Assuming 'is_verified' is a field on your User model
        # user.save(update_fields=['is_verified'])
        return {'message': "user activated"}

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User # Use User (get_user_model())
        fields = ['id', "first_name", 'last_name', 'phone', 'username', 'email'] # Removed 'is_verified' for now

class BmiSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bmi
        fields = ['height', 'weight', 'gender', 'birth_date']

# --- ADD THIS CUSTOM LOGIN SERIALIZER ---
class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims to the token if needed
        # token['username'] = user.username
        return token

    def validate(self, attrs):
        data = super().validate(attrs) # Gets 'refresh' and 'access' tokens

        # Add the user's profile data, nested under the 'user' key
        user_profile_data = UserProfileSerializer(self.user, context=self.context).data
        data['user'] = user_profile_data
        return data