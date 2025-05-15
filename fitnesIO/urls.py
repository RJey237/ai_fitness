# your_project_name/urls.py
from django.urls import path, include, reverse_lazy
from django.contrib import admin
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from rest_framework_simplejwt.views import TokenRefreshView # Keep for refresh
from django.views.generic import RedirectView

# --- IMPORT YOUR CUSTOM LOGIN VIEW ---
from user.views import MyCustomLoginAPIView # Make sure this path is correct for your project structure

schema_view = get_schema_view(
    openapi.Info(
        title="My API", default_version='v1', description="API документация",
        # ... other schema info ...
    ),
    public=True, permission_classes=(permissions.AllowAny,)
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(url=reverse_lazy('login'), permanent=False)),    # API Endpoints - These are included directly at the root
    path('', include('googleauth.api')), # e.g., /google/login/ (if defined inside)
    path('', include('user.api')),       # e.g., /register/perform-register/, /user/profile/, /calculate-calories/
    path('', include('utils.api')),      # e.g., /some-util-endpoint/
    path('', include('ai_model.urls')),  # e.g., /ai-chat/ (if defined inside)

    # Authentication API Login and Refresh
    # THIS IS THE KEY: Android will call /auth/login/ and hit your custom view
    path('auth/login/', MyCustomLoginAPIView.as_view(), name='api_custom_token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='api_token_refresh'),

    # Web Interface Endpoints
    path('accounts/', include('user.urls')), # For your web views like register_view, log_out
                                           # e.g., /accounts/register/
    path('accounts/', include('django.contrib.auth.urls')), # Django's built-in web auth (e.g. /accounts/login/)
                                                          # Ensure no clashes with your custom web URLs

    # API Documentation
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)