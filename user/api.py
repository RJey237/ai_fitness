# user/api.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RegisterAPIViewSet, # Use the API ViewSet
    UserProfileAPIView,
    ProfileUpdateAPIViewSet, # Use the API ViewSet
    CalculateCaloriesAPIView, # Use the API GenericAPIView

)

# Note: MyCustomLoginAPIView and TokenRefreshView will be in the main project urls.py

router = DefaultRouter()
# This will create /register/perform-register/ and /register/verify-number/
router.register(r'register', RegisterAPIViewSet, basename='api-user-auth')
# This will create /profile-update/ and /profile-update/{pk}/
router.register(r'profile-update', ProfileUpdateAPIViewSet, basename='api-profile-update')

urlpatterns = [
    path('', include(router.urls)), # Includes router generated URLs

    # GET current user's profile: /user/profile/
    path('user/profile/', UserProfileAPIView.as_view(), name='api_get_user_profile'),

    # POST to calculate calories: /calculate-calories/
    path('calculate-calories/', CalculateCaloriesAPIView.as_view(), name='api_calculate_calories'),

    # POST to verify OTP: /verify-otp/
    # path('verify-otp/', VerifyOtpView.as_view(), name='api_verify_otp'), # Uncomment if you have VerifyOtpView
]