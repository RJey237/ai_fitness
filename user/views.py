# user/views.py

# --- Django Web View Imports & Definitions ---
from django.shortcuts import render, redirect
from django.contrib.auth import login as django_auth_login, logout as django_auth_logout # Aliased for clarity
from django.contrib import messages
from .forms import RegistrationForm # Assuming RegistrationForm is your web form

# --- DRF API View Imports & Definitions ---
from rest_framework import viewsets, status, generics, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.contrib.auth import get_user_model
from .serializers import (
    RegisterSerializer,
    VerifySerializer,
    UserProfileSerializer,
    MyTokenObtainPairSerializer # Import your custom login serializer
)
from .models import CustomUser, Bmi # Keep if needed by other views
import datetime # Keep if needed by other views

from rest_framework_simplejwt.views import TokenObtainPairView # Base for custom login
from rest_framework.permissions import IsAuthenticated, AllowAny

User = get_user_model() # Use this consistently

# --- API VIEWS ---
class RegisterAPIViewSet(viewsets.ViewSet): # Renamed from RegisterView to RegisterAPIViewSet
    permission_classes = [AllowAny]

    @action(methods=['POST'], detail=False, url_path='perform-register') # Changed url_path for clarity
    def register(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        # For API, return structured data including the nested user profile
        user_profile_data = UserProfileSerializer(user, context={'request': request}).data
        response_payload = {
            "message": f"User {user.username} registered. Verification code sent to {user.phone}.", # Example message
            "access": None, # No tokens on registration
            "refresh": None,
            "user": user_profile_data
        }
        return Response(response_payload, status=status.HTTP_201_CREATED)

    @action(methods=['POST'], detail=False, url_path='verify-number') # Changed url_path
    def verify_number(self, request):
        serializer = VerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.save()
        return Response(data)

# --- THIS IS YOUR CUSTOM API LOGIN VIEW ---
class MyCustomLoginAPIView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer
    permission_classes = [AllowAny]

class UserProfileAPIView(generics.RetrieveAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    def get_object(self):
        return self.request.user

class ProfileUpdateAPIViewSet(viewsets.ModelViewSet): # Renamed from ProfileViewSet
    queryset = User.objects.all() # ModelViewSet needs a queryset
    serializer_class = UserProfileSerializer
    http_method_names = ['get', 'put', 'patch', 'head', 'options'] # retrieve, update, partial_update
    permission_classes = [IsAuthenticated]

    def get_queryset(self): # Ensure user can only access their own profile
        return User.objects.filter(pk=self.request.user.pk)
    
    def get_object(self): # For detail actions (retrieve, update, partial_update)
        return self.request.user # Always operate on the request.user

    # list() and create() are disabled by http_method_names.
    # retrieve(), update(), partial_update() are provided by ModelViewSet.

class CalculateCaloriesAPIView(generics.GenericAPIView): # Changed from ViewSet to GenericAPIView for a single POST
    # If it's just one action, a GenericAPIView with a post method is simpler than a ViewSet
    permission_classes = [IsAuthenticated]
    # serializer_class = BmiSerializer # If you have input validation for this

    def post(self, request, *args, **kwargs): # Changed from create to post
        try:
            activity_level = request.data.get('activity_level')
            if not activity_level:
                return Response({"error": "Activity level is required"}, status=status.HTTP_400_BAD_REQUEST)

            user_bmi_profile = Bmi.objects.get(user=request.user) # Assuming Bmi model has 'user' ForeignKey
            
            age_in_days = (datetime.date.today() - user_bmi_profile.birth_date).days
            age_in_years = age_in_days / 365.25 # Approximate

            if user_bmi_profile.gender.lower() == 'male':
                bmr = 88.362 + (13.397 * user_bmi_profile.weight) + (4.799 * user_bmi_profile.height) - (5.677 * age_in_years)
            else: # female
                bmr = 447.593 + (9.247 * user_bmi_profile.weight) + (3.098 * user_bmi_profile.height) - (4.330 * age_in_years)
            
            activity_multipliers = {
                'sedentary': 1.2, 'light': 1.375, 'moderate': 1.55,
                'intense': 1.725, 'very_intense': 1.9
            }
            multiplier = activity_multipliers.get(activity_level.lower())
            if not multiplier:
                return Response({"error": "Invalid activity level"}, status=status.HTTP_400_BAD_REQUEST)

            daily_calories = bmr * multiplier
            return Response({"daily_calories": daily_calories}, status=status.HTTP_200_OK)
        except Bmi.DoesNotExist:
            return Response({"error": "User BMI profile not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            # Log the exception for debugging
            # logger.error(f"Error calculating calories: {e}", exc_info=True)
            return Response({"error": "An error occurred during calculation."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from django.contrib.auth import login # To log the user in after registration

# --- Standard Django Views for Web Interface (Keep your existing ones) ---
def register_view(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save() # Save the user, UserCreationForm handles hashing
            login(request, user) # Log the user in automatically
            messages.success(request, "Registration successful! You are now logged in.")
            # Redirect to the same place as successful login
            # Or use: return redirect('some_other_page_name')
            return redirect('chat') # Redirect to chat view (adjust name if needed)
        else:
            # Form is invalid, add error messages if desired (form rendering handles field errors)
            messages.error(request, "Please correct the errors below.")
    else: # GET request
        form = RegistrationForm()

    context = {'form': form}
    return render(request, 'register.html', context)
def log_out(request): # Web logout
    if request.method == 'POST':
        django_auth_logout(request)
        messages.info(request, "You have been successfully logged out.")
        return redirect('login') # Name of your web login URL
    return redirect( 'login') # Adjust