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



# googleauth/views.py (or user/views.py - choose one and be consistent)
import requests
import logging
import secrets

from django.conf import settings
from django.shortcuts import redirect, reverse
from django.contrib.auth import login

from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework.decorators import action

# ADJUST IMPORT PATH IF NEEDED (e.g., from users.models import CustomUser)
from user.models import CustomUser  # Assuming CustomUser is in user/models.py


logger = logging.getLogger(__name__)


class GoogleLoginViewSet(ViewSet):
    @action(detail=False, methods=['get'], url_path='login')
    def login_start(self, request):
        """Initiates the Google OAuth2 login flow."""
        google_auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
        state = secrets.token_urlsafe(16)
        request.session['oauth_state'] = state  # Store state in session
        params = {
            'client_id': settings.GOOGLE_CLIENT_ID,
            'redirect_uri': settings.GOOGLE_REDIRECT_URI,
            'response_type': 'code',
            'scope': 'openid profile email',
            'access_type': 'offline',
            'state': state,
            'prompt': 'consent',  # Force consent screen for testing refresh tokens if needed
        }
        # Correctly encode parameters
        url_params = requests.compat.urlencode(params)
        url = f"{google_auth_url}?{url_params}"
        logger.info(f"Redirecting user to Google for authentication. State: {state}")
        return redirect(url)

    @action(detail=False, methods=['GET'])
    def test(self, request):
        if not request.user.is_authenticated:
            # Return DRF Response for API consistency
            return Response({"error": "Authentication required via session"}, status=401)
        # Return DRF Response for API consistency
        return Response(
            {"hello": f"hello Django session authenticated user {request.user.email}!"}
        )


class GoogleCallbackViewSet(ViewSet):
    @action(detail=False, methods=['get'], url_path='callback')
    def callback_handler(self, request):
        """Handles the callback from Google and logs the user into Django session."""
        code = request.GET.get('code')
        received_state = request.GET.get('state')

        # --- State Validation (Using Session) ---
        expected_state = request.session.pop('oauth_state', None)
        if (
            not received_state
            or not expected_state
            or received_state != expected_state
        ):
            logger.warning("Invalid OAuth state parameter received.")
            # Using Response for consistency in this ViewSet
            return Response(
                {"error": "Invalid state parameter. Security check failed."},
                status=400,
            )

        if not code:
            logger.error("No authorization code provided in Google callback.")
            return Response({"error": "No code provided"}, status=400)

        # --- Exchange Code for Tokens (Server-to-Server) ---
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            'code': code,
            'client_id': settings.GOOGLE_CLIENT_ID,
            'client_secret': settings.GOOGLE_CLIENT_SECRET,
            'redirect_uri': settings.GOOGLE_REDIRECT_URI,  # Must match exactly what was sent initially
            'grant_type': 'authorization_code',
        }
        try:
            token_response = requests.post(token_url, data=data, timeout=10)
            token_response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            token_info = token_response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to exchange code for token: {e}", exc_info=True)
            # Provide a generic error message to the user
            return Response(
                {"error": "Failed to exchange authorization code with Google."},
                status=502,
            )  # Bad Gateway might be appropriate

        access_token = token_info.get('access_token')
        # id_token = token_info.get('id_token') # Also useful, contains user info directly

        if not access_token:
            logger.error("No access token received from Google.")
            return Response(
                {"error": "Failed to obtain access token from Google"}, status=502
            )

        # --- Get User Info ---
        # Note: You could potentially decode the id_token instead of making another request
        # if you just need basic verified info like email, sub, name, picture.
        # However, calling the userinfo endpoint is also common.
        try:
            user_info_url = "https://www.googleapis.com/oauth2/v3/userinfo"
            headers = {'Authorization': f'Bearer {access_token}'}
            user_info_response = requests.get(
                user_info_url, headers=headers, timeout=10
            )
            user_info_response.raise_for_status()
            user_info = user_info_response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch user info from Google: {e}", exc_info=True)
            return Response(
                {"error": "Failed to fetch user information from Google."}, status=502
            )

        email = user_info.get('email')
        if not email:
            logger.error("Email not found in Google user info.")
            return Response({"error": "Email not found in Google user info"}, status=400)

        # It's generally good practice to ensure the email is verified by Google
        if not user_info.get('email_verified'):
            logger.warning(f"Google email {email} is not verified.")
            return Response(
                {
                    "error": "Your Google email is not verified. Please verify it with Google first."
                },
                status=400,
            )

        # --- User Handling and Login ---
        try:
            defaults = {
                # Use email as username if your CustomUser requires one and it's unique
                # Or use another unique identifier from Google like 'sub' (subject identifier)
                # Make sure your CustomUser.USERNAME_FIELD is set appropriately
                "username": user_info.get('sub', email),  # Using 'sub' is often more stable than name/email part
                "first_name": user_info.get("given_name", ""),
                "last_name": user_info.get("family_name", ""),
                "is_active": True,  # Ensure the user is active
                # Example: Add picture if your model has it
                # "profile_picture": user_info.get("picture", ""),
            }
            # Use email as the lookup field as it's verified and likely unique identifier
            user, created = CustomUser.objects.update_or_create(
                email=email, defaults=defaults
            )

            # --- *** FIX IS HERE *** ---
            # Set Unusable Password (Important for social-only logins)
            if created or not user.has_usable_password():
                # Call make_random_password on the USER MODEL's MANAGER (.objects)

                random_password = '!@#$%QWERT'
                user.set_password(random_password)
                # Save only the password field if other fields were handled by update_or_create or subsequent logic
                user.save(update_fields=['password'])
                logger.info(
                    f"{'Created new user' if created else 'Set random unusable password for existing user'}: {email}"
                )
            # --- *** END FIX *** ---

            # Optional: Update other fields if the user already existed
            if not created:
                needs_save = False
                update_fields = []  # Track fields to save efficiently

                # Example: Update names only if they differ
                if user.first_name != defaults['first_name']:
                    user.first_name = defaults['first_name']
                    update_fields.append('first_name')
                    needs_save = True
                if user.last_name != defaults['last_name']:
                    user.last_name = defaults['last_name']
                    update_fields.append('last_name')
                    needs_save = True

                # Add picture update logic if desired and track field

                if needs_save:
                    user.save(update_fields=update_fields)
                    logger.info(
                        f"Updated fields {update_fields} for existing user {email}"
                    )

            # --- **** LOGIN TO DJANGO SESSION **** ---
            # Ensure you have 'django.contrib.auth.backends.ModelBackend' in AUTHENTICATION_BACKENDS
            login(
                request, user, backend='django.contrib.auth.backends.ModelBackend'
            )
            logger.info(f"User {user.email} successfully logged into Django session via Google.")
            # -----------------------------------------

            # --- **** REDIRECT TO CHAT VIEW **** ---
            # ** Replace 'chat' with the actual name from your urls.py **
            target_url_name = 'chat'  # MAKE SURE THIS URL NAME EXISTS
            try:
                destination = reverse(target_url_name)
                logger.info(
                    f"Redirecting authenticated user to '{target_url_name}' ({destination})"
                )
                return redirect(destination)  # SUCCESS! Redirect to your target page
            except Exception as reverse_e:
                # Use a reliable fallback URL name like 'chat' or just '/'
                fallback_url_name = 'chat'  # Replace 'chat' if you have a different name for your main page
                logger.error(
                    f"Could not reverse URL name '{target_url_name}': {reverse_e}. Falling back to '{fallback_url_name}'."
                )
                try:
                    fallback_destination = reverse(fallback_url_name)
                    return redirect(fallback_destination)
                except Exception:
                    logger.error(
                        f"Could not reverse fallback URL '{fallback_url_name}'. Redirecting to root '/'."
                    )
                    return redirect('/')  # Absolute fallback

            # -------------------------------------

        # Catch specific exceptions if possible (e.g., DatabaseError)
        except Exception as e:
            # Use logger.exception to include traceback in logs for better debugging
            logger.exception(
                f"Error during user processing or login for email {email}: {e}"
            )
            # Provide a generic error message to the user
            return Response(
                {"error": "An internal error occurred during user processing."},
                status=500,
            )



# In your chosen views.py (e.g., user/views.py)
# user/views.py (or your chosen app's views.py)

# --- [Imports remain the same as the previous full example] ---
from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.contrib.auth import get_user_model, login # Added login for web flow
from django.conf import settings
from django.shortcuts import redirect, reverse # Added for web flow
import logging
import requests # Added for web flow
import secrets # Added for web flow


# --- Google Auth Libraries ---
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
# -----------------------------

# --- JWT Library ---
from rest_framework_simplejwt.tokens import RefreshToken
# -------------------

# --- User Model ---
CustomUser = get_user_model()
# ----------------

logger = logging.getLogger(__name__)

# =============================================================================
# VIEWSET FOR WEB-BASED GOOGLE LOGIN FLOW (Start) - KEEPING AS REQUESTED
# =============================================================================
class GoogleLoginViewSet(ViewSet):
    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=['get'], url_path='login')
    def login_start(self, request):
        """Initiates the web-based Google OAuth2 login flow."""
        # ... (Code from previous full example is correct for web flow start) ...
        google_auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
        state = secrets.token_urlsafe(16)
        request.session['oauth_state'] = state
        params = {
            'client_id': settings.GOOGLE_CLIENT_ID, # Uses the Web Client ID
            'redirect_uri': settings.GOOGLE_REDIRECT_URI,
            'response_type': 'code',
            'scope': 'openid profile email',
            'access_type': 'offline',
            'state': state,
            'prompt': 'consent',
        }
        try:
            url_params = requests.compat.urlencode(params)
            url = f"{google_auth_url}?{url_params}"
            logger.info(f"Redirecting user to Google for web authentication. State: {state}")
            return redirect(url)
        except Exception as e:
            logger.error(f"Error constructing Google auth URL: {e}", exc_info=True)
            return Response({"error": "Failed to initiate Google login."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['GET'], url_path='test-session')
    def test_session_auth(self, request):
        # ... (Code from previous full example is correct for testing session) ...
         if not request.user.is_authenticated:
            return Response({"error": "Authentication required via session"}, status=401)
         else:
            return Response(
                {"message": f"Hello Django session authenticated user: {request.user.email}!"}
            )

# =============================================================================
# VIEWSET FOR WEB-BASED GOOGLE LOGIN FLOW (Callback) - KEEPING AS REQUESTED
# =============================================================================
class GoogleCallbackViewSet(ViewSet):
    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=['get'], url_path='callback')
    def callback_handler(self, request):
        """Handles the callback from Google for the web flow."""
        # ... (Code from previous full example is correct for web flow callback) ...
        # ... (Includes state validation, code exchange, userinfo fetch, user create/update, Django session login, redirect) ...
        # --- Key parts ---
        code = request.GET.get('code')
        received_state = request.GET.get('state')
        # 1. Validate state
        expected_state = request.session.pop('oauth_state', None)
        if not received_state or not expected_state or received_state != expected_state:
             logger.warning(f"Invalid OAuth state. Expected: {expected_state}, Received: {received_state}")
             return Response({"error": "Invalid state parameter."}, status=status.HTTP_400_BAD_REQUEST)
        if not code:
             logger.error("No authorization code in callback.")
             return Response({"error": "Authorization code missing."}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Exchange code for tokens
        try:
            token_url = "https://oauth2.googleapis.com/token"
            token_data = {
                'code': code,
                'client_id': settings.GOOGLE_CLIENT_ID,
                'client_secret': settings.GOOGLE_CLIENT_SECRET,
                'redirect_uri': settings.GOOGLE_REDIRECT_URI,
                'grant_type': 'authorization_code',
            }
            token_response = requests.post(token_url, data=token_data, timeout=15)
            token_response.raise_for_status()
            token_info = token_response.json()
            access_token = token_info.get('access_token')
            if not access_token:
                 raise ValueError("Access token not found in response")
        except Exception as e:
            logger.error(f"Failed to exchange code for token: {e}", exc_info=True)
            return Response({"error": "Failed to exchange authorization code."}, status=status.HTTP_502_BAD_GATEWAY)

        # 3. Get User Info
        try:
            user_info_url = "https://www.googleapis.com/oauth2/v3/userinfo"
            headers = {'Authorization': f'Bearer {access_token}'}
            user_info_response = requests.get(user_info_url, headers=headers, timeout=10)
            user_info_response.raise_for_status()
            user_info = user_info_response.json()
            email = user_info.get('email')
            google_user_id = user_info.get('sub')
            if not email or not google_user_id or not user_info.get('email_verified'):
                 raise ValueError("Incomplete or unverified user info from Google")
        except Exception as e:
            logger.error(f"Failed to fetch/validate user info: {e}", exc_info=True)
            return Response({"error": "Failed to get valid user information from Google."}, status=status.HTTP_502_BAD_GATEWAY)

        # 4. User Handling & Session Login
        try:
            defaults = {
                'username': email,
                'first_name': user_info.get("given_name", ""),
                'last_name': user_info.get("family_name", ""),
                'is_active': True,
                'google_id': google_user_id
            }
            user, created = CustomUser.objects.update_or_create(email=email, defaults=defaults)
            if created or not user.has_usable_password(): # Set unusable password if new or no password set
                user.set_unusable_password()
                user.save(update_fields=['password', 'google_id'] if created else ['password']) # Save necessary fields
            elif not user.google_id: # Ensure google_id is set for existing users
                 user.google_id = google_user_id
                 user.save(update_fields=['google_id'])

            login(request, user, backend='django.contrib.auth.backends.ModelBackend') # Log into session
            logger.info(f"Web flow: User {email} logged into session.")
            # 5. Redirect
            target_url_name = 'chat' # CHANGE AS NEEDED
            return redirect(reverse(target_url_name))
        except Exception as e:
             logger.exception(f"Error during web flow user processing/login for {email}: {e}")
             return Response({"error": "Internal server error during user processing."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# googleauth/views.py (or user/views.py)

# --- [Keep existing imports: ViewSet, action, Response, permissions, settings, logging, requests, secrets, id_token, google_requests, RefreshToken] ---
from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.conf import settings
from django.shortcuts import redirect, reverse # For web flow
from django.contrib.auth import login         # For web flow session login
import logging
import requests # For web flow
import secrets  # For web flow

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from rest_framework_simplejwt.tokens import RefreshToken

# --- ADJUST IMPORT PATHS FOR CustomUser and UserProfileSerializer ---
# Assuming CustomUser is in user.models and UserProfileSerializer is in user.serializers
from user.models import CustomUser
from user.serializers import UserProfileSerializer # IMPORTANT: You need this serializer

logger = logging.getLogger(__name__)

# ... (Your GoogleLoginViewSet and GoogleCallbackViewSet for WEB flow can remain as they are) ...
# class GoogleLoginViewSet(ViewSet): ...
# class GoogleCallbackViewSet(ViewSet): ...


# =============================================================================
# VIEWSET FOR API-BASED GOOGLE SIGN-IN (ID Token Verification) - CRITICAL FOR ANDROID
# =============================================================================
class GoogleSignInViewSet(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=['post'], url_path='login')
    def verify_google_token(self, request):
        received_token = request.data.get('id_token')

        if not received_token:
            logger.warning("API Google sign-in: ID token missing.")
            return Response({"error": "ID token not provided."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            idinfo = id_token.verify_token(
                received_token,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID # Use your Web Client ID (audience)
            )

            if not idinfo.get('email_verified'):
                logger.warning(f"API Google sign-in rejected: Email {idinfo.get('email')} not verified.")
                return Response({"error": "Email not verified by Google."}, status=status.HTTP_400_BAD_REQUEST)

            google_user_id = idinfo['sub']
            email = idinfo['email']
            first_name = idinfo.get('given_name', '')
            last_name = idinfo.get('family_name', '')
            # picture_url = idinfo.get('picture', '') # If you store profile picture

            defaults_for_update = {
                'username': email, # Or generate a unique username if email isn't your USERNAME_FIELD
                'first_name': first_name,
                'last_name': last_name,
                'is_active': True,
                'google_id': google_user_id, # Store the Google User ID
                # 'profile_image_url': picture_url, # If your CustomUser model has such a field
            }
            user, created = CustomUser.objects.update_or_create(
                email=email, # Using email as the primary lookup key for Google users
                defaults=defaults_for_update
            )

            if created or not user.has_usable_password():
                user.set_unusable_password()
                update_fields = ['password', 'google_id'] if created else ['password']
                if not created and not user.google_id:
                    user.google_id = google_user_id # Ensure google_id is set
                    update_fields.append('google_id')
                user.save(update_fields=list(set(update_fields))) # Use set to handle potential duplicates
            elif not user.google_id: # Existing user, ensure google_id is set
                user.google_id = google_user_id
                user.save(update_fields=['google_id'])

            logger.info(f"API Google sign-in: User processed: {email}")

            # --- Generate API Tokens (Simple JWT) ---
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)

            # --- Prepare NESTED Response using UserProfileSerializer ---
            user_profile_data = UserProfileSerializer(user, context={'request': request}).data # Serialize user

            response_data = {
                "access": access_token,
                "refresh": refresh_token,
                "user": user_profile_data # <<< NESTED user object
            }
            return Response(response_data, status=status.HTTP_200_OK)

        except ValueError as e:
            logger.error(f"API Google ID token verification value error: {e}", exc_info=True)
            return Response({"error": "Invalid Google ID token."}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            logger.exception(f"API Internal error during Google sign-in for token starting {received_token[:10]}...: {e}")
            return Response({"error": "An internal server error occurred during Google sign-in."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)





