from django.urls import path, include
from .views import GoogleLoginViewSet, GoogleCallbackViewSet
from rest_framework.routers import DefaultRouter

# router = DefaultRouter()
# router.register(r'auth/google', GoogleLoginViewSet, basename='google-login')
# router.register(r'auth/google', GoogleCallbackViewSet, basename='google-callback')

# urlpatterns = [
#     path('', include(router.urls)),
# ]from django.urls import path


google_login = GoogleLoginViewSet.as_view({'get': 'login_start'})
google_callback = GoogleCallbackViewSet.as_view({'get': 'callback_handler'})

urlpatterns = [
    path('auth/google/login/', google_login, name='google-login'),
    path('auth/google/callback/', google_callback, name='google-callback'),
]
