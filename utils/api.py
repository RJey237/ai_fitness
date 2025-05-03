from rest_framework.routers import DefaultRouter
from utils.views import SendSMSViewSet

router = DefaultRouter()
router.register(r'sms', SendSMSViewSet, basename='sms')

urlpatterns = router.urls
