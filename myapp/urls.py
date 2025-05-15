from django.urls import path
from .views import *
urlpatterns=[
    path('schedule_task/',schedule_task,name='schedule_task'),
    

]