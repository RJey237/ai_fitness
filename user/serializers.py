from .models import CustomUser
from rest_framework import serializers
import phonenumbers
from utils.exceptions import BaseApiException


class RegisterSerializer(serializers.ModelSerializer):
    password1 = serializers.CharField(write_only = True, min_length = 8)
    password2 = serializers.CharField(write_only = True, min_length = 8)
    
    class Meta:
        model = CustomUser
        fields = ['username','password1','password2','phone']
        
    def validate(self,data):
        if data['password1'] != data['password2']:
            raise serializers.ValidationError({'password' : 'Password did not match'})
        if data['phone']:
            try:
                phone_number = phonenumbers.parse(data['phone'],None)
                if not phonenumbers.is_valid_number(phone_number):
                    raise serializers.ValidationError("Invalid phone number format.")
            except phonenumbers.NumberParseException:
                    raise serializers.ValidationError("Invalid phone number.")
        return data 

    
    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            username = validated_data['username'],
            password = validated_data['password1'],
            phone = validated_data['phone']
        )
        return user
        
class VerifySerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    code = serializers.IntegerField()
    
    
    def validate(self, data):
        user_id = data['user_id']
        if not CustomUser.objects.filter(id = user_id).exists():
            raise serializers.ValidationError('user not found')
        return data 
    
    
    def save(self, **kwargs):
        code = self.validated_data.get('code')
        user_id = self.validated_data.get("user_id")
        
        
        if  code != 123456:
            raise BaseApiException("code did not match")
        
        user = CustomUser.objects.get(id =user_id)
        user.is_verified = True
        user.save()
        return{'message':"user activated"}

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields= ['first_name','last_name','phone','email_verified','is_verified']
    