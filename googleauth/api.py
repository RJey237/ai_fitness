

from django.urls import path, include
from rest_framework.routers import DefaultRouter


from .views import GoogleLoginViewSet, GoogleCallbackViewSet 
from .views import GoogleSignInViewSet 
router = DefaultRouter()

router.register(r'auth/google', GoogleSignInViewSet, basename='google-signin-api')

web_google_login_start = GoogleLoginViewSet.as_view({'get': 'login_start'})
web_google_callback_handler = GoogleCallbackViewSet.as_view({'get': 'callback_handler'})


urlpatterns = [

    path('api/', include(router.urls)), 


    path('web/auth/google/login/', web_google_login_start, name='web-google-login-start'),
    path('web/auth/google/callback/', web_google_callback_handler, name='web-google-callback'),


]

