# views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse, HttpResponseForbidden
import google.generativeai as genai
import os
import json
from django.db import transaction
from routine.models import Routine, Day, DailyFood, DailyExercises
from user.models import CustomUser # Ensure this is your correct user model import
from datetime import date, timedelta
from django.utils import timezone
from django.conf import settings
import traceback
from rest_framework import viewsets, status
from rest_framework.views import APIView 
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated # For API token auth
from django.contrib.auth.decorators import login_required # For HTML view session auth
from django.contrib import messages

from .serializers import (
    RoutineSerializer,
    RoutineGenerationRequestSerializer,
    AIChatQuerySerializer,
)


# --- Helper Function (Remains the same) ---
@transaction.atomic
def save_routine_from_json(data, user):
    """
    Saves the routine data from a parsed JSON dictionary to the database.
    Handles potential data type inconsistencies from AI.
    Requires a valid user object passed in.
    """
    # ... (Keep the full implementation of this function as provided before) ...
    try:
        # Assuming 'en' as the default language. Adjust if needed from settings.
        language_code = settings.LANGUAGE_CODE.split('-')[0] if hasattr(settings, 'LANGUAGE_CODE') and settings.LANGUAGE_CODE else 'en'

        # 1. Create Routine
        routine_desc = data.get('routine_description', 'No overall description provided.')
        if not isinstance(routine_desc, str):
            routine_desc = str(routine_desc) # Ensure it's a string

        routine = Routine.objects.create(
            user=user, # User is passed as argument
            amount_of_weeks=1 # Assuming 1 week based on the prompt
            # start_date will be set automatically by auto_now_add=True
        )
        # Set translated description
        routine.set_current_language(language_code)
        routine.description = routine_desc
        routine.save()

        today = date.today()
        current_weekday = today.weekday() # Monday is 0, Sunday is 6

        # 2. Create Days, DailyFood, DailyExercises
        weekly_plan_data = data.get('weekly_plan', [])
        if not isinstance(weekly_plan_data, list):
             print(f"Warning: 'weekly_plan' data is not a list: {type(weekly_plan_data)}. Skipping day creation.")
             weekly_plan_data = [] # Treat as empty if not a list


        for day_data in weekly_plan_data:
            if not isinstance(day_data, dict):
                print(f"Warning: Skipping invalid day data item (not a dict): {day_data}")
                continue

            target_json_weekday = day_data.get('day_of_week') # 1-7
            if not isinstance(target_json_weekday, int) or not 1 <= target_json_weekday <= 7:
                print(f"Warning: Skipping day with invalid or missing 'day_of_week': {target_json_weekday}")
                continue # Skip if day_of_week is invalid or missing

            target_python_weekday = target_json_weekday - 1 # Convert to 0-6

            # Calculate the date for the upcoming instance of this weekday
            days_until_target = (target_python_weekday - current_weekday + 7) % 7
            calculated_date = today + timedelta(days=days_until_target)

            # Create Day
            day_obj = Day.objects.create(
                routine=routine,
                week_number=1, # Assuming week 1
                week_day=target_json_weekday, # Store the 1-7 value
                week_date=calculated_date,
                status=False # Default status
            )

            # 3. Create DailyFood (if diet info exists)
            diet_data = day_data.get('diet')
            if isinstance(diet_data, dict):
                try:
                    # Ensure total_calories is treated as a number (float allows flexibility)
                    total_calories = float(diet_data.get('total_calories', 0))
                except (ValueError, TypeError):
                    print(f"Warning: Invalid value for 'total_calories' ({diet_data.get('total_calories')}) on day {target_json_weekday}. Defaulting to 0.")
                    total_calories = 0.0

                diet_desc = diet_data.get('description', 'No diet details provided.')
                if not isinstance(diet_desc, str):
                    diet_desc = str(diet_desc) # Ensure string

                daily_food = DailyFood.objects.create(
                    day=day_obj,
                    callory=total_calories # Use float for calories
                )
                # Set translated description
                daily_food.set_current_language(language_code)
                daily_food.description = diet_desc
                daily_food.save()
            elif diet_data is not None:
                 print(f"Warning: 'diet' data for day {target_json_weekday} is not a dictionary: {type(diet_data)}. Skipping food creation.")


            # 4. Create DailyExercises (if workout info exists)
            workout_data = day_data.get('workout', [])
            if isinstance(workout_data, list):
                for exercise_data in workout_data:
                    if isinstance(exercise_data, dict):
                        # --- Add robust integer conversion ---
                        try:
                            # Handle potential missing key gracefully
                            sets_val = int(exercise_data.get('sets', 0))
                        except (ValueError, TypeError):
                            print(f"Warning: Invalid value for sets '{exercise_data.get('sets')}' in exercise '{exercise_data.get('name', 'N/A')}'. Defaulting to 0.")
                            sets_val = 0 # Default to 0 if conversion fails

                        try:
                            # Handle potential missing key or non-integer (like AMRAP text)
                            reps_val = int(exercise_data.get('reps', 0))
                        except (ValueError, TypeError):
                            # Check if it's 'AMRAP' or similar non-integer, handle specifically if needed, otherwise default to 0
                            reps_str = str(exercise_data.get('reps', '0')).strip().upper()
                            if reps_str == 'AMRAP':
                                reps_val = -1 # Use -1 for AMRAP as per prompt refinement
                            else:
                                print(f"Warning: Invalid value for reps '{exercise_data.get('reps')}' in exercise '{exercise_data.get('name', 'N/A')}'. Defaulting to 0.")
                                reps_val = 0 # Default to 0 if conversion fails or gets text
                        try:
                            # Duration might not be generated, keep default or handle if needed
                            duration_val = int(exercise_data.get('duration', 0))
                        except (ValueError, TypeError):
                             duration_val = 0
                        # --- End of robust conversion ---

                        ex_name = exercise_data.get('name', 'Unnamed Exercise')
                        if not isinstance(ex_name, str): ex_name = str(ex_name)

                        ex_desc = exercise_data.get('description', '')
                        if not isinstance(ex_desc, str): ex_desc = str(ex_desc)


                        daily_exercise = DailyExercises.objects.create(
                            day=day_obj,
                            duration=duration_val, # Use the safely converted value
                            sets=sets_val,       # Use the safely converted value
                            reps=reps_val        # Use the safely converted value
                        )
                        # Set translated fields
                        daily_exercise.set_current_language(language_code)
                        daily_exercise.name = ex_name
                        daily_exercise.description = ex_desc
                        daily_exercise.save()
                    elif exercise_data is not None:
                         print(f"Warning: Skipping invalid workout item (not a dict) for day {target_json_weekday}: {exercise_data}")

            elif workout_data is not None:
                 print(f"Warning: 'workout' data for day {target_json_weekday} is not a list: {type(workout_data)}. Skipping exercise creation.")


        print(f"Successfully saved routine {routine.id} for user {user.username}")
        return routine # Return the created routine object

    except Exception as e:
        # Log the error during saving
        print(f"Error saving routine to DB: {e}")
        print(traceback.format_exc()) # Print full traceback for DB errors
        # The transaction.atomic decorator will automatically roll back changes
        raise  # Re-raise the exception so the view knows saving failed


# --- Chat View (Requires Session Login) ---
@login_required # Use decorator to ensure user is logged in via session
def chat_view(request):
    """
    A Django view to generate personalized fitness recommendations in JSON format
    and save them to the database. Requires session-based login.
    Accessible via browser.
    """
    user = request.user # Get the logged-in user object directly from the request

    # ** IMPORTANT: Ensure the template path matches your project structure **
    # Default assumes 'templates/chat.html' or an app-level template dir
    template_name = 'chat.html' # ADJUST IF YOUR PATH IS DIFFERENT (e.g., 'chat.html')

    if request.method == 'POST':
        ai_response_text_for_debug = None # Initialize for debugging context
        parsed_data_for_debug = None # Initialize for debugging context

        try:
            weight = float(request.POST.get('weight'))
            height_m = float(request.POST.get('height'))
            height_cm = height_m * 100
            age = int(request.POST.get('age'))
            goal = request.POST.get('goal')

            if not (weight > 0 and height_m > 0 and age > 0 and goal in ['gain_muscle', 'lose_weight', 'maintain']):
                messages.error(request, 'Invalid input. Weight, height, and age must be positive numbers. Choose a valid goal!')
                return render(request, template_name, {'user': user}) # Pass user object

            api_key = os.environ.get('GOOGLE_API_KEY')
            if not api_key:
                 messages.error(request, 'AI service configuration error. Please contact support.')
                 print("CRITICAL ERROR: GOOGLE_API_KEY environment variable not set.")
                 return render(request, template_name, {'user': user}) # Pass user object

            genai.configure(api_key=api_key)
            model_name = getattr(settings, 'GEMINI_MODEL_NAME', 'models/gemini-2.0-flash')
            model = genai.GenerativeModel(model_name)

            # --- Construct the Prompt (Using the simpler, preferred structure) ---
            base_prompt = f"User Profile: Age {age}, Weight {weight} kg, Height {height_cm} cm.\n"

            if goal == "gain_muscle":
                goal_instruction = "Generate a detailed weekly workout plan focused on muscle gain, including appropriate diet suggestions for each day to support muscle growth."
            elif goal == "lose_weight":
                goal_instruction = "Generate a detailed weekly diet and workout plan designed for weight loss, emphasizing calorie deficit and fat-burning exercises."
            elif goal == 'maintain':
                goal_instruction = "Generate a detailed weekly diet and workout plan for weight maintenance, balancing calorie intake and expenditure."
            else:
                 messages.error(request, 'Invalid goal selected.')
                 return render(request, template_name, {'user': user}) # Pass user object

            # --- JSON Formatting Instruction (Keep your detailed, strict version) ---
            json_format_instruction = """
            Format the entire response STRICTLY as a single JSON object. Do NOT include any text, explanations, introductions, acknowledgements, or markdown formatting (like ```json) before or after the JSON block. The entire response MUST start with `{` and end with `}`.
            The JSON object must follow this exact structure:

            ```json
            {
              "routine_description": "string (A brief overall summary of the weekly plan's strategy and goals based on the user profile and goal)",
              "weekly_plan": [
                {
                  "day_of_week": "integer (1 for Monday, 2 for Tuesday, ..., 7 for Sunday)",
                  "day_name": "string (e.g., 'Monday - Upper Body Strength', 'Tuesday - Cardio & Core', 'Rest Day')",
                  "diet": {
                    "description": "string (Detailed meal suggestions for the day: Breakfast, Lunch, Dinner, Snacks. Provide specific food ideas and portion guidance appropriate for the user's goal.)",
                    "total_calories": "integer (Estimated total daily calorie target for this specific day, tailored to the user's goal. Must be a whole number.)"
                  },
                  "workout": [
                    {
                      "name": "string (Specific exercise name, e.g., 'Barbell Bench Press', 'Running', 'Plank')",
                      "description": "string (: Brief execution tip, form focus, or intensity level. For AMRAP, mention 'Perform as many reps as possible' here. For timed holds like Planks, mention duration unit here e.g., 'Hold for seconds indicated in reps')",
                      "sets": "integer (Number of sets. Must be a whole number. Use 1 for single-bout cardio/duration exercises like running.)",
                      "reps": "integer (Number of repetitions per set. Use for rep-based exercises like Bench Press. **Use 0 or 1 if the exercise is primarily time-based and uses the 'duration' field.** Use -1 for AMRAP.)",
                      "duration": "integer (Duration of the exercise **IF** it's time-based, like Running, Cycling, Plank. **The unit (seconds or minutes) MUST be specified in the 'description' field.** Use 0 if the exercise is purely repetition-based.)"
                    }
                    // Add more exercise objects for the day's workout as needed.
                    // Ensure ALL exercise objects include 'name', 'description', 'sets', and 'reps'.
                    // If it's a rest day workout-wise, this array should be empty: []
                  ]
                }
                // *** Include exactly 7 day objects in this list, one for each day from Monday (1) to Sunday (7). ***
              ]
            }
            ```
            Ensure the output is only the valid JSON data, adhering strictly to the specified types (string, integer). Pay close attention to providing only integers for 'total_calories', 'sets', and 'reps' (unless reps is -1 for AMRAP). Do not add any conversational text outside the JSON structure.
            """

            # Combine just the essential parts for the prompt
            prompt = base_prompt + goal_instruction + "\n\n" + json_format_instruction

            # --- Generate Content ---
            print(f"--- Sending Prompt to AI for user: {user.username} (chat_view) ---")
            safety_settings = [{"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}]
            response = model.generate_content(prompt, safety_settings=safety_settings)
            ai_response_text = response.text
            ai_response_text_for_debug = ai_response_text
            print("--- Raw AI Response (chat_view) ---")
            print(ai_response_text)
            print("-----------------------------------")

            # --- Parse the JSON Response ---
            parsed_data = None
            try:
                cleaned_response_text = ai_response_text.strip().strip('```json').strip('```').strip()
                if not cleaned_response_text: raise json.JSONDecodeError("Received empty response from AI.", "", 0)
                if not cleaned_response_text.startswith('{') or not cleaned_response_text.endswith('}'): raise json.JSONDecodeError("Response does not start/end with curly braces.", cleaned_response_text, 0)
                parsed_data = json.loads(cleaned_response_text)
                parsed_data_for_debug = parsed_data
            except json.JSONDecodeError as json_err:
                print(f"JSON Decode Error (chat_view): {json_err}")
                error_message = f'AI response was not valid JSON. Error: {json_err.msg} at pos {json_err.pos}'
                messages.error(request, error_message)
                return render(request, template_name, { # Pass user object on error
                    'error': error_message,
                    'raw_response_for_debug': ai_response_text_for_debug if settings.DEBUG else None,
                    'user': user
                })

            # --- Save to Database ---
            try:
                created_routine = save_routine_from_json(parsed_data, user) # Pass the authenticated user
                success_message = f"Successfully generated and saved routine (ID: {created_routine.id})!"
                messages.success(request, success_message)
                # Redirect to detail view on success
                return redirect('routine_detail', routine_id=created_routine.id) # Make sure 'routine_detail' is a valid URL name

            except Exception as db_err:
                 print(f"Database Save Error for user {user.username} (chat_view): {db_err}")
                 print(traceback.format_exc())
                 error_message = f'Successfully generated plan, but failed to save to database: {db_err}'
                 messages.error(request, error_message)
                 return render(request, template_name, { # Pass user object on error
                     'error': error_message,
                     'parsed_data_for_debug': parsed_data_for_debug if settings.DEBUG else None,
                     'raw_response_for_debug': ai_response_text_for_debug if settings.DEBUG else None,
                     'user': user
                 })

        # --- Handle Specific Errors During POST Processing ---
        except ValueError:
            messages.error(request, 'Invalid input. Weight, height, and age must be valid numbers.')
            return render(request, template_name, {'user': user}) # Pass user object
        except genai.types.generation_types.BlockedPromptException as blocked_err:
             print(f"AI Generation Blocked for user {user.username} (chat_view): {blocked_err}")
             messages.error(request, 'The request was blocked by the AI\'s safety filters. Please adjust your input or try again.')
             return render(request, template_name, {'user': user}) # Pass user object
        except genai.types.generation_types.StopCandidateException as stop_err:
             print(f"AI Generation Stopped Early for user {user.username} (chat_view): {stop_err}")
             messages.warning(request, f'The AI stopped generating the response unexpectedly. (Reason: {stop_err})')
             return render(request, template_name, { # Pass user object
                'raw_response_for_debug': ai_response_text_for_debug if settings.DEBUG else None,
                'user': user
                })
        except Exception as e: # Catch other unexpected errors
            print(f"An unexpected error occurred in POST handling for user {user.username} (chat_view): {e}")
            print(traceback.format_exc())
            messages.error(request, f'An unexpected error occurred: {str(e)}')
            return render(request, template_name, { # Pass user object
                 'error': f'Unexpected error: {str(e)}',
                 'raw_response_for_debug': ai_response_text_for_debug if settings.DEBUG else None, # Show response if available
                 'user': user
                })

    else: # GET Request
        # Just render the form, passing the user object to the template context
        return render(request, template_name, {'user': user})


# --- Routine List & Delete View (Requires Session Login) ---
@login_required # Use decorator to ensure user is logged in via session
def routine_list_delete_view(request):
    """
    Displays a list of routines for the logged-in user (via session)
    and handles deletion via POST requests from the list.
    Accessible via browser.
    """
    user = request.user
    # ** Adjust template path if necessary **
    list_template_name = 'routine_list.html' # Or 'routine_list.html' etc.

    # 1. Handle Deletion (POST Request)
    if request.method == 'POST':
        # ... (Keep the deletion logic as provided before) ...
        routine_id_to_delete = request.POST.get('routine_id')
        if routine_id_to_delete:
            try:
                routine_to_delete = get_object_or_404(Routine, pk=routine_id_to_delete, user=user)
                routine_pk_for_message = routine_to_delete.pk
                routine_to_delete.delete()
                messages.success(request, f"Routine {routine_pk_for_message} deleted successfully.")
                print(f"Deleted routine {routine_pk_for_message} for user {user.username}")
                return redirect('routine_list_delete') # Ensure 'routine_list_delete' is a valid URL name
            except ValueError:
                 messages.error(request, "Invalid Routine ID format.")
                 print(f"Invalid routine ID format for deletion attempt by user {user.username}: {routine_id_to_delete}")
            except Routine.DoesNotExist:
                 messages.error(request, f"Routine not found or permission denied.")
                 print(f"Routine not found or access denied for deletion: ID {routine_id_to_delete}, User {username}")
            except Exception as e:
                 messages.error(request, f"An unexpected error occurred during deletion: {e}")
                 print(f"Unexpected error deleting routine {routine_id_to_delete} for user {user.username}: {e}")
                 print(traceback.format_exc())
        else:
            messages.warning(request, "Delete request received without a Routine ID.")
            print(f"Warning: POST request received without 'routine_id' from user {user.username}.")
        return redirect('routine_list_delete') # Redirect after POST processing

    # 2. Prepare Context for Listing (GET Request or after POST redirect)
    routines_list = Routine.objects.filter(user=user).order_by('-start_date')
    context = {
        'routines': routines_list,
        'user': user, # Pass the full user object
    }
    return render(request, list_template_name, context)


# --- Routine Detail View (Requires Session Login) ---
@login_required # Use decorator to ensure user is logged in via session
def routine_detail_view(request, routine_id):
    """
    Displays the details of a specific routine belonging to the logged-in user (via session).
    Adds day names to day objects for easier template access.
    Accessible via browser.
    """
    # ** Adjust template path if necessary **
    detail_template_name = 'routine.html' # Or 'routine.html' etc.

    # Filter by both pk and the logged-in user to ensure ownership
    routine = get_object_or_404(
        Routine.objects.prefetch_related('days','days__dailyfood_set','days__dailyexercises_set'),
        pk=routine_id,
        user=request.user # Ensure the routine belongs to the logged-in user
    )

    day_names = { 1: 'Monday', 2: 'Tuesday', 3: 'Wednesday', 4: 'Thursday', 5: 'Friday', 6: 'Saturday', 7: 'Sunday' }
    days_with_names = []
    for day in routine.days.all().order_by('week_day'):
        day.name_of_day = day_names.get(day.week_day, "Unknown Day")
        days_with_names.append(day)

    context = {
        'routine': routine,
        'days_to_display': days_with_names,
        'user': request.user # Pass user object for consistency
    }
    return render(request, detail_template_name, context)


# --- DRF ViewSet for Routines API (Requires Token Authentication) ---

class RoutineViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing user routines via JSON requests (e.g., for Postman, mobile apps).
    Uses token-based authentication (e.g., JWT).
    """
    serializer_class = RoutineSerializer
    permission_classes = [IsAuthenticated] # Ensures only token-authenticated users can access
    def get_queryset(self):
        """ Returns routines belonging ONLY to the requesting (token-authenticated) user. """
        user = self.request.user # DRF/JWTAuthentication provides the user associated with the token
        return Routine.objects.filter(user=user).prefetch_related(
            'days', 'days__dailyfood_set', 'days__dailyexercises_set'
        ).order_by('-start_date')

    def perform_create(self, serializer):
        """ Associates the routine with the token-authenticated user during creation. """
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        """
        Handles POST requests to /api/routines/.
        Generates a new routine using AI based on validated input for the token-authenticated user.
        """
        input_serializer = RoutineGenerationRequestSerializer(data=request.data)
        if not input_serializer.is_valid():
            return Response(input_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = input_serializer.validated_data
        user = request.user # Get user from token authentication

        weight = validated_data['weight']
        height_m = validated_data['height']
        height_cm = height_m * 100
        age = validated_data['age']
        goal = validated_data['goal']

        # --- AI Generation Logic ---
        ai_response_text = None
        try:
            api_key = os.environ.get('GOOGLE_API_KEY')
            if not api_key:
                print("CRITICAL ERROR: GOOGLE_API_KEY environment variable not set (DRF).")
                return Response({'error': 'AI service configuration error.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

            genai.configure(api_key=api_key)
            model_name = getattr(settings, 'GEMINI_MODEL_NAME', 'models/gemini-2.0-flash')
            model = genai.GenerativeModel(model_name)

            # --- Construct the Prompt (Using the simpler, preferred structure) ---
            base_prompt = f"User Profile: Age {age}, Weight {weight} kg, Height {height_cm} cm.\n"

            if goal == "gain_muscle":
                goal_instruction = "Generate a detailed weekly workout plan focused on muscle gain, including appropriate diet suggestions for each day to support muscle growth."
            elif goal == "lose_weight":
                goal_instruction = "Generate a detailed weekly diet and workout plan designed for weight loss, emphasizing calorie deficit and fat-burning exercises."
            elif goal == 'maintain':
                goal_instruction = "Generate a detailed weekly diet and workout plan for weight maintenance, balancing calorie intake and expenditure."
            else:
                 return Response({'goal': ['Invalid goal provided.']}, status=status.HTTP_400_BAD_REQUEST)

            # --- JSON Formatting Instruction (Keep your detailed, strict version) ---
            json_format_instruction = """
            Format the entire response STRICTLY as a single JSON object. Do NOT include any text, explanations, introductions, acknowledgements, or markdown formatting (like ```json) before or after the JSON block. The entire response MUST start with `{` and end with `}`.
            The JSON object must follow this exact structure:

            ```json
            {
              "routine_description": "string (A brief overall summary of the weekly plan's strategy and goals based on the user profile and goal)",
              "weekly_plan": [
                {
                  "day_of_week": "integer (1 for Monday, 2 for Tuesday, ..., 7 for Sunday)",
                  "day_name": "string (e.g., 'Monday - Upper Body Strength', 'Tuesday - Cardio & Core', 'Rest Day')",
                  "diet": {
                    "description": "string (Detailed meal suggestions for the day: Breakfast, Lunch, Dinner, Snacks. Provide specific food ideas and portion guidance appropriate for the user's goal.)",
                    "total_calories": "integer (Estimated total daily calorie target for this specific day, tailored to the user's goal. Must be a whole number.)"
                  },
                  "workout": [
                    {
                      "name": "string (Specific exercise name, e.g., 'Barbell Bench Press', 'Running', 'Plank')",
                      "description": "string (: Brief execution tip, form focus, or intensity level. For AMRAP, mention 'Perform as many reps as possible' here. For timed holds like Planks, mention duration unit here e.g., 'Hold for seconds indicated in reps')",
                      "sets": "integer (Number of sets. Must be a whole number. Use 1 for single-bout cardio/duration exercises like running.)",
                      "reps": "integer (Number of repetitions per set. Use for rep-based exercises like Bench Press. **Use 0 or 1 if the exercise is primarily time-based and uses the 'duration' field.** Use -1 for AMRAP.)",
                      "duration": "integer (Duration of the exercise **IF** it's time-based, like Running, Cycling, Plank. **The unit (seconds or minutes) MUST be specified in the 'description' field.** Use 0 if the exercise is purely repetition-based.)"
                    }
                    // Add more exercise objects for the day's workout as needed.
                    // Ensure ALL exercise objects include 'name', 'description', 'sets', and 'reps'.
                    // If it's a rest day workout-wise, this array should be empty: []
                  ]
                }
                // *** Include exactly 7 day objects in this list, one for each day from Monday (1) to Sunday (7). ***
              ]
            }
            ```
            Ensure the output is only the valid JSON data, adhering strictly to the specified types (string, integer). Pay close attention to providing only integers for 'total_calories', 'sets', and 'reps' (unless reps is -1 for AMRAP). Do not add any conversational text outside the JSON structure.
            """
            # Combine just the essential parts for the prompt
            prompt = base_prompt + goal_instruction + "\n\n" + json_format_instruction

            # --- Generate Content ---
            safety_settings = [{"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}]
            print(f"--- Sending Prompt to AI (DRF ViewSet) for user: {user.username} ---")
            response = model.generate_content(prompt, safety_settings=safety_settings)
            ai_response_text = response.text
            print("--- Raw AI Response (DRF ViewSet) ---")
            # print(ai_response_text) # Avoid logging raw response in prod
            print("------------------------------------")

            # --- Parse the JSON Response ---
            parsed_data = None
            try:
                cleaned_response_text = ai_response_text.strip().strip('```json').strip('```').strip()
                if not cleaned_response_text: raise json.JSONDecodeError("Received empty response from AI.", "", 0)
                if not cleaned_response_text.startswith('{') or not cleaned_response_text.endswith('}'): raise json.JSONDecodeError("Response does not start/end with curly braces.", cleaned_response_text, 0)
                parsed_data = json.loads(cleaned_response_text)
            except json.JSONDecodeError as json_err:
                print(f"DRF JSON Decode Error for user {user.username}: {json_err}")
                print(f"Failed raw AI response (DRF) preview (first 500 chars):\n{ai_response_text[:500]}")
                error_message = f'AI response could not be parsed as JSON. Error: {json_err.msg} at pos {json_err.pos}.'
                # Return API error response
                return Response({'error': error_message, 'raw_response': ai_response_text if settings.DEBUG else None},
                                status=status.HTTP_422_UNPROCESSABLE_ENTITY)

            # --- Save to Database ---
            try:
                created_routine = save_routine_from_json(parsed_data, user) # Pass token-authenticated user
                output_serializer = self.get_serializer(created_routine)
                return Response(output_serializer.data, status=status.HTTP_201_CREATED) # Return serialized routine
            except Exception as db_err:
                print(f"DRF Database Save Error for user {user.username}: {db_err}")
                print(traceback.format_exc())
                return Response({'error': f'Failed to save generated plan to database: {db_err}'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # --- Handle Specific AI/Generation Errors ---
        except genai.types.generation_types.BlockedPromptException as blocked_err:
             print(f"DRF AI Generation Blocked for user {user.username}: {blocked_err}")
             return Response({'error': 'Request blocked by AI safety filters.'}, status=status.HTTP_400_BAD_REQUEST)
        except genai.types.generation_types.StopCandidateException as stop_err:
             print(f"DRF AI Generation Stopped Early for user {user.username}: {stop_err}")
             return Response({
                'error': f'AI stopped generating unexpectedly. (Reason: {stop_err})',
                'raw_response_preview': ai_response_text[:500] if ai_response_text else None
             }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e: # Catch other unexpected errors
            print(f"Unexpected error during DRF AI interaction for user {user.username}: {e}")
            print(traceback.format_exc())
            return Response({'error': f'Unexpected server error during AI generation: {str(e)}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Default list, retrieve, update, partial_update, destroy actions
    # from ModelViewSet will use get_queryset (filtering by token user)
    # and RoutineSerializer, protected by IsAuthenticated.

# --- End DRF ViewSet ---



class GeneralAIChatView(APIView):
    """
    API endpoint for general chat interactions with the AI.
    Expects a JSON payload like: {"user_query": "Your question here"}
    Returns a JSON payload like: {"ai_response": "AI's answer"}
    Uses token-based authentication.
    Does NOT save chat history to the database.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = AIChatQuerySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user_query = serializer.validated_data['user_query']
        user = request.user # User from token

        print(f"--- Received General Chat Query from user: {user.username} ---")
        print(f"Query: {user_query}")

        ai_generated_text = None # To store the raw text from AI before JSON formatting

        try:
            api_key = os.environ.get('GOOGLE_API_KEY')
            if not api_key:
                print("CRITICAL ERROR: GOOGLE_API_KEY environment variable not set (AIChatView).")
                return Response({'error': 'AI service configuration error.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

            genai.configure(api_key=api_key)
            # You might use the same model or a different one optimized for chat/general queries
            model_name = getattr(settings, 'GEMINI_CHAT_MODEL_NAME', 'models/gemini-1.5-flash-latest') # Or your preferred chat model
            model = genai.GenerativeModel(model_name)

            # --- Construct the Prompt for General Chat ---
            # Keep the prompt simple for general chat, but instruct for JSON output.
            # You can add system prompts or persona instructions here if desired.
            prompt_instruction = (
                "You are a helpful AI assistant. "
                "The user will ask a question or make a statement. Provide a concise and helpful response. "
                "Format your entire response STRICTLY as a single JSON object with one key: 'ai_response'. "
                "Provide the user with the link of youtube tutorials if you are asked and they must be inside the exact same key for your responce"
                "The value for 'ai_response' should be your textual answer to the user's query. "
                "Example: {\"ai_response\": \"Your generated answer here.\"}. "
                "Do NOT include any text, explanations, or markdown formatting (like ```json) before or after the JSON block. "
                "The entire response MUST start with { and end with }."
            )
            
            # You might want to prepend some context or a system message
            # For simple one-off chats, the user query might be enough with the JSON instruction.
            # For more conversational AI, you'd pass chat history.
            # For now, let's make the AI respond to the user_query directly but wrap it in the required JSON.

            # This prompt tells the AI what it should *produce* as output structure
            full_prompt = f"{prompt_instruction}\n\nUser's query: {user_query}"


            print(f"--- Sending Prompt to AI (AIChatView) for user: {user.username} ---")
            # print(f"Full Prompt: {full_prompt}") # For debugging

            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            ]
            
            # For simple chat, using generate_content is fine.
            # For conversational chat, you would use model.start_chat() and chat.send_message()
            response = model.generate_content(full_prompt, safety_settings=safety_settings)
            ai_generated_text = response.text # This is what the AI returns, hopefully as JSON
            
            print("--- Raw AI Response (AIChatView) ---")
            # print(ai_generated_text) # Avoid logging raw response in prod
            print("-----------------------------------")

            # --- Validate and Return the AI's JSON Response ---
            # The AI should ideally return the JSON directly based on the prompt.
            # We still need to validate it.
            try:
                # Attempt to clean any potential markdown/text before/after the JSON
                cleaned_response_text = ai_generated_text.strip()
                if cleaned_response_text.startswith("```json"):
                    cleaned_response_text = cleaned_response_text[7:]
                if cleaned_response_text.endswith("```"):
                    cleaned_response_text = cleaned_response_text[:-3]
                cleaned_response_text = cleaned_response_text.strip()

                if not cleaned_response_text:
                    raise json.JSONDecodeError("Received empty or whitespace-only response from AI.", "", 0)
                if not cleaned_response_text.startswith('{') or not cleaned_response_text.endswith('}'):
                    # If AI didn't follow JSON instruction, wrap its text into the desired JSON structure
                    print(f"AI did not return valid JSON. Wrapping its response: '{ai_generated_text[:100]}...'")
                    ai_response_content = ai_generated_text # Use the raw text as the content
                    # Manually create the JSON structure
                    response_data = {"ai_response": ai_response_content}
                    # No need to json.loads here, we are constructing the dict
                else:
                    # AI likely returned JSON, try to parse it to ensure it's valid
                    # and that it contains the 'ai_response' key.
                    parsed_json = json.loads(cleaned_response_text)
                    if "ai_response" not in parsed_json:
                        # If AI returned JSON but not the right structure, wrap its raw text.
                        print(f"AI returned JSON but without 'ai_response' key. Wrapping its response: '{ai_generated_text[:100]}...'")
                        response_data = {"ai_response": ai_generated_text}
                    else:
                        response_data = parsed_json # Use the JSON as returned by AI

                return Response(response_data, status=status.HTTP_200_OK)

            except json.JSONDecodeError as json_err:
                print(f"AIChatView JSON Decode Error for user {user.username}: {json_err}")
                print(f"Failed raw AI response (AIChatView) preview (first 500 chars):\n{ai_generated_text[:500] if ai_generated_text else 'None'}")
                # If parsing fails, send the raw AI text as the content of ai_response
                # This is a fallback if the AI completely fails to produce JSON.
                return Response({'ai_response': ai_generated_text if ai_generated_text else "AI response was empty or unparsable."}, 
                                status=status.HTTP_200_OK) # Still 200 OK, but client needs to handle potentially non-JSON text

        except genai.types.generation_types.BlockedPromptException as blocked_err:
            print(f"AIChatView AI Generation Blocked for user {user.username}: {blocked_err}")
            return Response({'error': 'Your query was blocked by safety filters.'}, status=status.HTTP_400_BAD_REQUEST)
        except genai.types.generation_types.StopCandidateException as stop_err:
            print(f"AIChatView AI Generation Stopped Early for user {user.username}: {stop_err}")
            return Response({
                'error': f'AI stopped generating unexpectedly. (Reason: {stop_err})',
                'raw_response_preview': ai_generated_text[:500] if ai_generated_text else None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            print(f"Unexpected error during AIChatView interaction for user {user.username}: {e}")
            print(traceback.format_exc())
            return Response({'error': f'An unexpected server error occurred: {str(e)}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)