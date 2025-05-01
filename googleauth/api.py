from django.urls import path, include
from .views import GoogleLoginViewSet, GoogleCallbackViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'auth/google', GoogleLoginViewSet, basename='google-login')
router.register(r'auth/google', GoogleCallbackViewSet, basename='google-callback')

urlpatterns = [
    path('', include(router.urls)),
]