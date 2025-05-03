from django.urls import path,include
from.views import RegisterView,ProfileViewSet,CalculateCaloriesView
from rest_framework.routers import DefaultRouter

user = DefaultRouter()

user.register(r'register', RegisterView, basename='register')
user.register(r'profile', ProfileViewSet, basename='profile')
user.register(r'calculate-bmi', CalculateCaloriesView, basename='calculate-bmi')

urlpatterns = [
    path('',include(user.urls)),
]
