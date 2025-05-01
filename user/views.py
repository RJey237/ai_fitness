from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Bmi
from .serializers import BmiSerializer
import datetime

class CalculateCaloriesView(APIView):
    
    def post(self, request, *args, **kwargs):
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
