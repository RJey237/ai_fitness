from .views import chat_view,routine_detail_view,RoutineViewSet,routine_list_delete_view
from django.urls import path, include
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'routines', RoutineViewSet, basename='routine-api')


urlpatterns=[     
    path('chat/', chat_view, name='chat'),
    path('routine/<int:routine_id>/', routine_detail_view, name='routine_detail'),
    path('my-routines/', routine_list_delete_view, name='routine_list_delete'),

    
    path('api/', include(router.urls)),
]
