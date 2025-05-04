from rest_framework.viewsets import ViewSet,ModelViewSet
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from .serializers import RegisterSerializer,VerifySerializer,UserProfileSerializer
from rest_framework import status
from rest_framework.response import Response
from .models import CustomUser
from .models import Bmi

import datetime
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
    
class ProfileViewSet(ModelViewSet):
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


class CalculateCaloriesView(ViewSet):
    
    def create(self, request, *args, **kwargs):
        try:
            
            activity_level = request.data.get('activity_level')
            if not activity_level:
                return Response({"error": "Activity level is required"}, status=status.HTTP_400_BAD_REQUEST)

           
            user_profile = Bmi.objects.get(user=request.user)

           
            age = (datetime.date.today() - user_profile.birth_date).days 

            if user_profile.gender == 'male':
                bmr = 88.362 + (13.397 * user_profile.weight) + (4.799 * user_profile.height) - (5.677 * age)
            else:
                bmr = 447.593 + (9.247 * user_profile.weight) + (3.098 * user_profile.height) - (4.330 * age)

            
            if activity_level == 'sedentary':
                daily_calories = bmr * 1.2
            elif activity_level == 'light':  
                daily_calories = bmr * 1.375
            elif activity_level == 'moderate':  
                daily_calories = bmr * 1.55
            elif activity_level == 'intense': 
                daily_calories = bmr * 1.725
            elif activity_level == 'very_intense':  
                daily_calories = bmr * 1.9
            else:
                return Response({"error": "Invalid activity level"}, status=status.HTTP_400_BAD_REQUEST)

            return Response({"daily_calories": daily_calories}, status=status.HTTP_200_OK)

        except Bmi.DoesNotExist:
            return Response({"error": "User profile not found"}, status=status.HTTP_404_NOT_FOUND)

# user/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login # To log the user in after registration
from django.contrib import messages
from .forms import RegistrationForm

def register_view(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save() # Save the user, UserCreationForm handles hashing
            login(request, user) # Log the user in automatically
            messages.success(request, "Registration successful! You are now logged in.")
            # Redirect to the same place as successful login
            # Or use: return redirect('some_other_page_name')
            return redirect('chat') # Redirect to chat view (adjust name if needed)
        else:
            # Form is invalid, add error messages if desired (form rendering handles field errors)
            messages.error(request, "Please correct the errors below.")
    else: # GET request
        form = RegistrationForm()

    context = {'form': form}
    return render(request, 'register.html', context) # Use a template within the user app


def log_out(request):
    return redirect('login')

