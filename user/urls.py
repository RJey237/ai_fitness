# user/urls.py
from django.urls import path
from . import views # Import views from the current directory

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('log_out/', views.log_out, name='log_out'),

]