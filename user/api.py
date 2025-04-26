from django.urls import path,include
from.views import RegisterView,ProfileViewSet
from rest_framework.routers import DefaultRouter

user = DefaultRouter()

user.register(r'', RegisterView, basename='register')
user.register(r'profile', ProfileViewSet, basename='profile')

urlpatterns = [
    path('',include(user.urls)),
]
