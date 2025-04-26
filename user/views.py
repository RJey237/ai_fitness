from rest_framework.viewsets import ViewSet,ModelViewSet
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from .serializers import RegisterSerializer,VerifySerializer,UserProfileSerializer
from rest_framework import status
from rest_framework.response import Response
from .models import CustomUser
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
class RegisterView(ViewSet):
    
    @action(methods=['POST'],detail=False)
    def register(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        # send_sms function here
        return Response({"message":f"code was sent to {user.phone} number","user":user.id}, status=status.HTTP_200_OK)

    @action(methods=['POST'],detail=False)
    def verify_number(self,request):
        serializer = VerifySerializer(data = request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.save()
        return Response(data)
    
class ProfileViewSet(ViewSet):
    class ViewSet(ModelViewSet):
        queryset = CustomUser.objects.all()
        serializer_class = UserProfileSerializer
        http_method_names = ['get','post']
        permission_classes = (IsAuthenticated,)
    
    def list(self, request, *args, **kwargs):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)
        
    def create(self, request, *args, **kwargs):
        serializer = UserProfileSerializer(data = request.data,instance = request.user,partial = True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
