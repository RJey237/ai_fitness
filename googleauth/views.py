# user/views.py

import requests
from django.conf import settings
from django.shortcuts import redirect
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.authtoken.models import Token
from user.models import CustomUser

class GoogleLoginViewSet(ViewSet):
    @action(detail=False, methods=['get'])
    def login(self, request):
        google_auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
        params = {
            'client_id': settings.GOOGLE_CLIENT_ID,
            'redirect_uri': settings.GOOGLE_REDIRECT_URI,
            'response_type': 'code',
            'scope': 'openid profile email',
            'access_type': 'offline',
            'state': 'secure_random_state',
            'prompt': 'consent',
        }
        url = f"{google_auth_url}?{requests.compat.urlencode(params)}"
        return redirect(url)


class GoogleCallbackViewSet(ViewSet):
    @action(detail=False, methods=['get'])
    def callback(self, request):
        code = request.GET.get('code')
        if not code:
            return Response({"error": "No code provided"}, status=400)

        # Exchange code for tokens
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            'code': code,
            'client_id': settings.GOOGLE_CLIENT_ID,
            'client_secret': settings.GOOGLE_CLIENT_SECRET,
            'redirect_uri': settings.GOOGLE_REDIRECT_URI,
            'grant_type': 'authorization_code',
        }
        token_response = requests.post(token_url, data=data)
        token_info = token_response.json()

        access_token = token_info.get('access_token')
        if not access_token:
            return Response({"error": "Failed to obtain access token"}, status=400)

        # Get user info
        user_info_url = "https://www.googleapis.com/oauth2/v3/userinfo"
        headers = {'Authorization': f'Bearer {access_token}'}
        user_info_response = requests.get(user_info_url, headers=headers)
        user_info = user_info_response.json()

        email = user_info.get('email')
        if not email:
            return Response({"error": "Google user info missing"}, status=400)

        # Create or get user
        user, created = CustomUser.objects.get_or_create(
            email=email,
            defaults={
                "username": email.split('@')[0],  # Generate username from email or use a different method
                "first_name": user_info.get("given_name", ""),
                "last_name": user_info.get("family_name", ""),
            }
        )

        # Optionally, store additional user information, like profile image and phone
        user.profile_image = user_info.get("picture", "")  # For example, Google provides a picture URL
        user.save()

        # Create token
        token, _ = Token.objects.get_or_create(user=user)

        return Response({
            "message": "User authenticated successfully",
            "user": {
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
            },
            "token": token.key
        })
