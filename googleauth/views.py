# # user/views.py

# import requests
# from django.conf import settings
# from django.shortcuts import redirect
# from rest_framework.viewsets import ViewSet
# from rest_framework.response import Response
# from rest_framework.decorators import action
# from rest_framework.authtoken.models import Token

# from user.models import CustomUser

# class GoogleLoginViewSet(ViewSet):
#     @action(detail=False,methods=['GET'])
#     def test(self,request):
#         return Response({"hello":"hello"})
#     @action(detail=False, methods=['get'])
#     def login(self, request):
#         google_auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
#         params = {
#             'client_id': settings.GOOGLE_CLIENT_ID,
#             'redirect_uri': settings.GOOGLE_REDIRECT_URI,
#             'response_type': 'code',
#             'scope': 'openid profile email',
#             'access_type': 'offline',
#             'state': 'secure_random_state',
#             'prompt': 'consent',
#         }
#         url = f"{google_auth_url}?{requests.compat.urlencode(params)}"
#         return redirect(url)


# # class GoogleCallbackViewSet(ViewSet):
# #     @action(detail=False, methods=['get'])
# #     def callback(self, request):
# #         code = request.GET.get('code')
# #         if not code:
# #             return Response({"error": "No code provided"}, status=400)

# #         # Exchange code for tokens
# #         token_url = "https://oauth2.googleapis.com/token"
# #         data = {
# #             'code': code,
# #             'client_id': settings.GOOGLE_CLIENT_ID,
# #             'client_secret': settings.GOOGLE_CLIENT_SECRET,
# #             'redirect_uri': settings.GOOGLE_REDIRECT_URI,
# #             'grant_type': 'authorization_code',
# #         }
# #         token_response = requests.post(token_url, data=data)
# #         token_info = token_response.json()

# #         access_token = token_info.get('access_token')
# #         if not access_token:
# #             return Response({"error": "Failed to obtain access token"}, status=400)

# #         # Get user info
# #         user_info_url = "https://www.googleapis.com/oauth2/v3/userinfo"
# #         headers = {'Authorization': f'Bearer {access_token}'}
# #         user_info_response = requests.get(user_info_url, headers=headers)
# #         user_info = user_info_response.json()

# #         email = user_info.get('email')
# #         if not email:
# #             return Response({"error": "Google user info missing"}, status=400)

# #         # Create or get user
# #         user, created = CustomUser.objects.get_or_create(
# #             email=email,
# #             defaults={
# #                 "username": email.split('@')[0],  # Generate username from email or use a different method
# #                 "first_name": user_info.get("given_name", ""),
# #                 "last_name": user_info.get("family_name", ""),
# #             }
# #         )

# #         # Optionally, store additional user information, like profile image and phone
# #         user.profile_image = user_info.get("picture", "")  # For example, Google provides a picture URL
# #         user.save()

# #         # Create token
# #         token, _ = Token.objects.get_or_create(user=user)

# #         return Response({
# #             "message": "User authenticated successfully",
# #             "user": {
# #                 "email": user.email,
# #                 "first_name": user.first_name,
# #                 "last_name": user.last_name,
# #             },
# #             "token": token.key
# #         })




# user/views.py
# user/views.py (or googleauth/views.py)

import requests
import logging # Import logging
import secrets # For state generation

from django.conf import settings
from django.shortcuts import redirect, reverse # Import reverse
from django.contrib.auth import login # Import Django's login
from django.contrib.auth.models import BaseUserManager # For setting unusable password

from rest_framework.viewsets import ViewSet
from rest_framework.response import Response # Still needed for error responses
from rest_framework.decorators import action
# Simple JWT tokens are not directly returned to the browser in this flow
# from rest_framework_simplejwt.tokens import RefreshToken

# Assuming your CustomUser model is here:
from user.models import CustomUser # ADJUST IMPORT PATH IF NEEDED

logger = logging.getLogger(__name__)

class GoogleLoginViewSet(ViewSet):
    @action(detail=False, methods=['get'], url_path='login')
    def login_start(self, request):
        """Initiates the Google OAuth2 login flow."""
        google_auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
        state = secrets.token_urlsafe(16)
        request.session['oauth_state'] = state
        params = {
            'client_id': settings.GOOGLE_CLIENT_ID,
            'redirect_uri': settings.GOOGLE_REDIRECT_URI,
            'response_type': 'code',
            'scope': 'openid profile email',
            'access_type': 'offline',
            'state': state,
            'prompt': 'consent',
        }
        url = f"{google_auth_url}?{requests.compat.urlencode(params)}"
        logger.info(f"Redirecting user to Google for authentication. State: {state}")
        return redirect(url)

    # test action (optional)
    @action(detail=False, methods=['GET'])
    def test(self,request):
         if not request.user.is_authenticated:
             return Response({"error": "Authentication required via session"}, status=401)
         return Response({"hello": f"hello Django session authenticated user {request.user.email}!"})


class GoogleCallbackViewSet(ViewSet):
    @action(detail=False, methods=['get'], url_path='callback')
    def callback_handler(self, request):
        """Handles the callback from Google and logs the user into Django session."""
        code = request.GET.get('code')
        received_state = request.GET.get('state')

        # --- State Validation ---
        expected_state = request.session.pop('oauth_state', None)
        if not received_state or not expected_state or received_state != expected_state:
            logger.warning("Invalid OAuth state parameter received.")
            # Redirect to a login or error page
            # return redirect(reverse('login_page_name')) # Replace with your login/error page URL name
            return Response({"error": "Invalid state parameter. Security check failed."}, status=400) # Or redirect

        if not code:
            logger.error("No authorization code provided in Google callback.")
            # return redirect(reverse('login_page_name'))
            return Response({"error": "No code provided"}, status=400) # Or redirect

        # --- Exchange Code for Tokens (Server-to-Server) ---
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            'code': code,
            'client_id': settings.GOOGLE_CLIENT_ID,
            'client_secret': settings.GOOGLE_CLIENT_SECRET,
            'redirect_uri': settings.GOOGLE_REDIRECT_URI,
            'grant_type': 'authorization_code',
        }
        try:
            token_response = requests.post(token_url, data=data, timeout=10)
            token_response.raise_for_status()
            token_info = token_response.json()
        except requests.exceptions.RequestException as e:
             logger.error(f"Failed to exchange code for token: {e}", exc_info=True)
             # return redirect(reverse('login_page_name'))
             # Return Response for now, consistent with original error handling
             return Response({"error": f"Failed to exchange code for token: {e}"}, status=400)

        access_token = token_info.get('access_token')
        if not access_token:
            logger.error("No access token received from Google.")
            # return redirect(reverse('login_page_name'))
            return Response({"error": "Failed to obtain access token from Google"}, status=400)

        # --- Get User Info ---
        try:
            user_info_url = "https://www.googleapis.com/oauth2/v3/userinfo"
            headers = {'Authorization': f'Bearer {access_token}'}
            user_info_response = requests.get(user_info_url, headers=headers, timeout=10)
            user_info_response.raise_for_status()
            user_info = user_info_response.json()
        except requests.exceptions.RequestException as e:
             logger.error(f"Failed to fetch user info from Google: {e}", exc_info=True)
             # return redirect(reverse('login_page_name'))
             return Response({"error": f"Failed to fetch user info from Google: {e}"}, status=400)

        email = user_info.get('email')
        if not email:
            logger.error("Email not found in Google user info.")
            # return redirect(reverse('login_page_name'))
            return Response({"error": "Email not found in Google user info"}, status=400)
        if not user_info.get('email_verified'):
            logger.warning(f"Google email {email} is not verified.")
            # return redirect(reverse('login_page_name'))
            return Response({"error": "Google email is not verified"}, status=400)

        # --- User Handling and Login ---
        try:
            defaults = {
                "username": user_info.get('name', email.split('@')[0]), # Handle potential username conflicts if needed
                "first_name": user_info.get("given_name", ""),
                "last_name": user_info.get("family_name", ""),
                "is_active": True,
                # Assuming profile_image field exists and you want to store the URL
                # Change 'profile_image_url' if your field name is different
                # "profile_image_url": user_info.get("picture", ""), # If storing URL
            }
            user, created = CustomUser.objects.update_or_create(
                email=email,
                defaults=defaults
            )

            # --- Set Unusable Password (Important!) ---
            if created or not user.has_usable_password():
                 user.set_password(BaseUserManager().make_random_password())
                 user.save(update_fields=['password']) # Save the password immediately or include in later save
                 logger.info(f"{'Created new user' if created else 'Set unusable password for existing user'}: {email}")

            # Optional: Update other fields if user existed
            if not created:
                 # Example: Update name or picture if they changed in Google
                 needs_save = False
                 if user.first_name != defaults['first_name'] or user.last_name != defaults['last_name']:
                     user.first_name = defaults['first_name']
                     user.last_name = defaults['last_name']
                     needs_save = True
                 # Add picture update logic if desired
                 if needs_save:
                      user.save(update_fields=['first_name', 'last_name'])


            # --- **** LOGIN TO DJANGO SESSION **** ---
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            logger.info(f"User {user.email} successfully logged into Django session via Google.")
            # -----------------------------------------

            # --- **** REDIRECT TO CHAT VIEW **** ---
            # ** Replace 'chat' with the actual name from your urls.py **
            target_url_name = 'chat'
            try:
                destination = reverse(target_url_name)
                logger.info(f"Redirecting authenticated user to '{target_url_name}' ({destination})")
                return redirect(destination) # SUCCESS! Redirect to chat page
            except Exception as reverse_e:
                 logger.error(f"Could not reverse URL name '{target_url_name}': {reverse_e}. Redirecting to root.")
                 return redirect('/') # Fallback redirect
            # -------------------------------------

        except Exception as e:
            logger.exception(f"Error during user processing/login for email {email}: {e}")
            # return redirect(reverse('login_page_name')) # Redirect on error
            # Return error response for now
            return Response({"error": f"An error occurred during user processing: {e}"}, status=500)