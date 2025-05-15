# routine/serializers.py

from rest_framework import serializers
from routine.models import Routine, Day, DailyFood, DailyExercises
from user.models import CustomUser 
from django.conf import settings
from django.utils import timezone
from datetime import timedelta, date

# --- Serializers for nested objects (Read-Only for now in Routine Detail) ---

class DailyExercisesSerializer(serializers.ModelSerializer):
    # If you need translated fields exposed via API, look into 'parler-rest'
    class Meta:
        model = DailyExercises
        fields = ['id', 'name', 'description', 'duration', 'sets', 'reps']


class DailyFoodSerializer(serializers.ModelSerializer):
    # If you need translated fields exposed via API, look into 'parler-rest'
    class Meta:
        model = DailyFood
        fields = ['id', 'description', 'callory'] # Corrected typo 'callory' to 'calorie' if model is updated, otherwise keep 'callory'


class DaySerializer(serializers.ModelSerializer):
    # Use the correct related names ('dailyfood_set', 'dailyexercises_set' are defaults if not specified in ForeignKey)
    dailyfood = DailyFoodSerializer(many=False, read_only=True, source='dailyfood_set.first') # Assuming one DailyFood per Day based on your save logic
    dailyexercises = DailyExercisesSerializer(many=True, read_only=True, source='dailyexercises_set')
    name_of_day = serializers.SerializerMethodField(read_only=True) # Add day name

    class Meta:
        model = Day
        fields = ['id', 'week_number', 'week_day', 'name_of_day', 'week_date', 'status', 'dailyfood', 'dailyexercises']

    def get_name_of_day(self, obj):
        day_names = {
            1: 'Monday', 2: 'Tuesday', 3: 'Wednesday', 4: 'Thursday',
            5: 'Friday', 6: 'Saturday', 7: 'Sunday',
        }
        return day_names.get(obj.week_day, "Unknown Day")

# --- Serializer for Routine Listing/Retrieval ---

class RoutineSerializer(serializers.ModelSerializer):
    # Ensure 'days' matches the related_name in Day model's ForeignKey to Routine
    days = DaySerializer(many=True, read_only=True)
    user = serializers.PrimaryKeyRelatedField(read_only=True) # Show user ID

    class Meta:
        model = Routine
        fields = ['id', 'user', 'amount_of_weeks', 'description', 'start_date', 'days']
        # If using parler-rest for translations:
        # fields = ['id', 'user', 'amount_of_weeks', 'description', 'start_date', 'days', 'translations']


# --- Serializer for Routine Generation Request (Input Validation) ---

class RoutineGenerationRequestSerializer(serializers.Serializer):
    GOAL_CHOICES = [
        ('gain_muscle', 'Gain Muscle'),
        ('lose_weight', 'Lose Weight'),
        ('maintain', 'Maintain Weight'),
    ]

    # Expect height in meters from API user, consistent with HTML form
    height = serializers.FloatField(min_value=0.1, max_value=3.0) # Height in meters
    weight = serializers.FloatField(min_value=1.0)
    age = serializers.IntegerField(min_value=1, max_value=120)
    goal = serializers.ChoiceField(choices=GOAL_CHOICES)

    def validate_height(self, value):
        """Ensure height is positive."""
        if value <= 0:
            raise serializers.ValidationError("Height must be a positive number.")
        return value

    def validate_weight(self, value):
        """Ensure weight is positive."""
        if value <= 0:
            raise serializers.ValidationError("Weight must be a positive number.")
        return value

    def validate_age(self, value):
        """Ensure age is positive."""
        if value <= 0:
            raise serializers.ValidationError("Age must be a positive number.")
        return value




class AIChatQuerySerializer(serializers.Serializer):
    user_query = serializers.CharField(max_length=2000, trim_whitespace=True)
