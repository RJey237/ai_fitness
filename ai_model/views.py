from django.shortcuts import render,get_object_or_404,redirect
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
import google.generativeai as genai
import os
import json 
from django.db import transaction 
from routine.models import Routine, Day, DailyFood, DailyExercises
from user.models import CustomUser
from datetime import date, timedelta
from django.utils import timezone 
from django.conf import settings 
import traceback 
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib import messages

from .serializers import (
    RoutineSerializer,
    RoutineGenerationRequestSerializer,
)

@transaction.atomic 
def save_routine_from_json(data, user):
    """
    Saves the routine data from a parsed JSON dictionary to the database.
    Handles potential data type inconsistencies from AI.
    """
    try:
        # Assuming 'en' as the default language. Adjust if needed from settings.
        language_code = settings.LANGUAGE_CODE.split('-')[0] if hasattr(settings, 'LANGUAGE_CODE') and settings.LANGUAGE_CODE else 'en'

        # 1. Create Routine
        routine_desc = data.get('routine_description', 'No overall description provided.')
        if not isinstance(routine_desc, str):
            routine_desc = str(routine_desc) # Ensure it's a string

        routine = Routine.objects.create(
            user=user,
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


def chat_view(request):
    """
    A Django view to generate personalized fitness recommendations in JSON format
    and save them to the database.
    """
    # --- Get User (Replace with actual logged-in user logic eventually) ---
    user = None # Initialize user
    try:
        # ** IMPORTANT: Replace this with your actual authentication logic **
        # For example, if using Django's built-in auth:
        # if request.user.is_authenticated:
        #     user = request.user
        # else:
        #     # Handle unauthenticated user (e.g., redirect to login)
        #     # return redirect('login_url_name')
        #     # For now, fall back to testuser or error if not logged in
        #     try:
        #         user = CustomUser.objects.get(username="testuser")
        #     except CustomUser.DoesNotExist:
        #          return render(request, 'chat.html', {'error': 'User "testuser" does not exist and no user is logged in. Cannot proceed.'})

        # --- Using hardcoded user for demonstration ---
        user = CustomUser.objects.get(username="testuser")
        # --- End hardcoded user ---

    except CustomUser.DoesNotExist:
         # This handles the case where even the hardcoded user doesn't exist
         return render(request, 'chat.html', {'error': 'Default user "testuser" not found in the database. Cannot proceed.'})
    # ---

    if request.method == 'POST':
        ai_response_text_for_debug = None # Initialize for debugging context
        parsed_data_for_debug = None # Initialize for debugging context
       
        try:
            weight = float(request.POST.get('weight'))
            # Height in HTML is meters, model prompt expects cm. Convert here.
            height_m = float(request.POST.get('height'))
            height_cm = height_m * 100 # Convert meters to centimeters
            age = int(request.POST.get('age'))
            goal = request.POST.get('goal')

            if not (weight > 0 and height_m > 0 and age > 0 and goal in ['gain_muscle', 'lose_weight', 'maintain']):
                return render(request, 'chat.html', {
                    'error': 'Invalid input. Weight, height, and age must be positive numbers. Choose a valid goal!',
                    'username': user # Pass user even on error
                    })

            api_key = os.environ.get('GOOGLE_API_KEY')
            if not api_key:
                 return render(request, 'chat.html', {
                    'error': 'GOOGLE_API_KEY environment variable not set.',
                    'username': user
                    })

            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('models/gemini-1.5-flash') # Or a more advanced model if needed

            # --- Construct the Prompt ---
            base_prompt = f"User Profile: Age {age}, Weight {weight} kg, Height {height_cm} cm.\n"

            if goal == "gain_muscle":
                goal_instruction = "Generate a detailed weekly workout plan focused on muscle gain, including appropriate diet suggestions for each day to support muscle growth."
            elif goal == "lose_weight":
                goal_instruction = "Generate a detailed weekly diet and workout plan designed for weight loss, emphasizing calorie deficit and fat-burning exercises."
            elif goal == 'maintain':
                goal_instruction = "Generate a detailed weekly diet and workout plan for weight maintenance, balancing calorie intake and expenditure."
            else:
                 # Should be caught earlier, but good failsafe
                 return render(request, 'chat.html', {'error': 'Invalid goal selected.', 'username': user})


            # --- JSON Formatting Instruction (Refined) ---
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
                      "reps": "integer (Number of repetitions per set. Use for rep-based exercises like Bench Press. **Use 0 or 1 if the exercise is primarily time-based and uses the 'duration' field.** For AMRAP exercises, use -1.)",
                      "duration": "integer (Duration of the exercise **IF** it's time-based, like Running, Cycling, Plank. **The unit (seconds or minutes) MUST be specified in the 'description' field.** Use 0 if the exercise is purely repetition-based.)"                    }
                    // Add more exercise objects for the day's workout as needed.
                    // Ensure ALL exercise objects include 'name', 'sets', and 'reps'. 'description' is a must.
                    // If it's a rest day workout-wise, this array should be empty: []
                  ]
                }
                // *** Include exactly 7 day objects in this list, one for each day from Monday (1) to Sunday (7). ***
              ]
            }
            ```
            Ensure the output is only the valid JSON data, adhering strictly to the specified types (string, integer). Pay close attention to providing only integers for 'total_calories', 'sets', and 'reps'. Do not add any conversational text outside the JSON structure.
            """

            # Combine parts into the final prompt
            prompt = base_prompt + goal_instruction + "\n\n" + json_format_instruction

            # --- Generate Content ---
            print("--- Sending Prompt to AI ---")
            # print(prompt) # Uncomment to debug the exact prompt being sent
            print("--------------------------")

            # Configure safety settings to be less restrictive if needed, but be cautious
            # See https://ai.google.dev/docs/safety_setting_gemini
            safety_settings = [
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                # Add others if needed, e.g., HARASSMENT, HATE_SPEECH, SEXUALLY_EXPLICIT
            ]

            response = model.generate_content(prompt, safety_settings=safety_settings)
            ai_response_text = response.text
            ai_response_text_for_debug = ai_response_text # Store for potential debugging
            # print("--- Raw AI Response ---")
            # print(ai_response_text) # Uncomment to debug raw AI output
            # print("-----------------------")
            print(ai_response_text_for_debug)

            # --- Parse the JSON Response ---
            parsed_data = None # Initialize
            try:
                # Clean potential markdown code fences and leading/trailing whitespace
                cleaned_response_text = ai_response_text.strip().strip('```json').strip('```').strip()
 
                # Check if the cleaned text looks like JSON before parsing
                if not cleaned_response_text.startswith('{') or not cleaned_response_text.endswith('}'):
                     raise json.JSONDecodeError("Response does not start and end with curly braces.", cleaned_response_text, 0)

                parsed_data = json.loads(cleaned_response_text)
                parsed_data_for_debug = parsed_data # Store for potential debugging

            except json.JSONDecodeError as json_err:
                print(f"JSON Decode Error: {json_err}")
                # print(f"Failed to parse AI response: {cleaned_response_text}") # Show cleaned version in log
                error_message = (
                    f'AI response was not valid JSON. Please try again. '
                    f'Error: {json_err.msg} at position {json_err.pos}'
                )
                return render(request, 'chat.html', {
                    'error': error_message,
                    'raw_response_for_debug': ai_response_text_for_debug, # Send raw response for debugging
                    'username': user
                })

            # --- Save to Database ---
            try:
                # Get the user object again safely (in case it wasn't retrieved above, though it should be)
                # user_to_save = request.user if request.user.is_authenticated else CustomUser.objects.get(username="testuser") # Adapt based on your auth
                user_to_save = user # Use the user retrieved at the start of the view

                created_routine = save_routine_from_json(parsed_data, user_to_save)
                success_message = f"Successfully generated and saved routine (ID: {created_routine.id})!"

                # Show success message and routine description
                return render(request, 'chat.html', {
                    'success_message': success_message,
                    'routine_description': created_routine.description, # Show the saved description
                    'username': user # Pass user to template
                })

            except Exception as db_err:
                 # Error occurred within save_routine_from_json or related DB operation
                 print(f"Database Save Error: {db_err}")
                 print(traceback.format_exc()) # Log full traceback
                 return render(request, 'chat.html', {
                     'error': f'Successfully generated plan, but failed to save to database: {db_err}',
                     'parsed_data_for_debug': parsed_data_for_debug, # Send parsed data for debugging
                     'raw_response_for_debug': ai_response_text_for_debug, # May be useful too
                     'username': user
                 })

        except ValueError:
            # Error converting weight/height/age
            return render(request, 'chat.html', {
                'error': 'Invalid input. Weight, height, and age must be valid numbers.',
                'username': user
                })
        except genai.types.generation_types.BlockedPromptException as blocked_err:
             print(f"AI Generation Blocked: {blocked_err}")
             return render(request, 'chat.html', {
                'error': 'The request was blocked by the AI\'s safety filters. This might be due to the generated content potentially being unsafe. Please adjust your input or try a different goal.',
                'username': user
                })
        except genai.types.generation_types.StopCandidateException as stop_err:
             print(f"AI Generation Stopped Early: {stop_err}")
             # This can happen if the AI stops for reasons other than safety (e.g., length limits, unspecified reasons)
             return render(request, 'chat.html', {
                'error': f'The AI stopped generating the response unexpectedly. Response might be incomplete. Please try again. (Reason: {stop_err})',
                'raw_response_for_debug': ai_response_text_for_debug, # Show what was generated
                'username': user
                })
        except Exception as e:
            print(f"An unexpected error occurred in POST handling: {e}") # Log the exception
            print(traceback.format_exc()) # Print full traceback for debugging
            return render(request, 'chat.html', {
                'error': f'An unexpected error occurred: {str(e)}',
                 'raw_response_for_debug': ai_response_text_for_debug, # Show raw response if available
                'username': user
                })

    else: # GET Request
        # Just render the form, passing the username
        return render(request, 'chat.html', {'username': user})
    




    # Add this import at the top if you don't have it already

# ... (keep existing imports and functions like save_routine_from_json, chat_view) ...

# --- New View to Display a Routine ---
# views.py

# Import other necessary models and modules...
# from .models import Day, DailyFood, DailyExercises (if needed directly, though prefetch handles it)

# ... (keep existing imports and functions like save_routine_from_json, chat_view) ...

# --- Updated View to Display a Routine ---

# routine/views.py

# ... (keep existing imports and functions like save_routine_from_json, chat_view, routine_detail_view, RoutineViewSet) ...


def routine_list_delete_view(request):
    """
    Displays a list of routines for a user (logged-in or hardcoded fallback)
    and handles deletion via POST requests from the list.
    """
    user = CustomUser.objects.get(username="testuser")
    error_message = None
    username_to_display = "Unknown User"

    # 1. Determine the user
    # if request.user.is_authenticated:
    #     user = request.user
    #     username_to_display = user.username
    #     print(f"Displaying routines for logged-in user: {username_to_display}")
    # else:
    #     # Fallback to hardcoded user if not logged in
    #     try:
    #         # --- Using hardcoded user for demonstration ---
    #         user = CustomUser.objects.get(username="testuser")
    #         username_to_display = f"{user.username} (Hardcoded Fallback)"
    #         print(f"No logged-in user. Displaying routines for hardcoded user: {user.username}")
    #         # --- End hardcoded user ---
    #     except CustomUser.DoesNotExist:
    #         error_message = 'No user is logged in and the fallback user "testuser" was not found.'
    #         print("Error: No logged-in user and fallback 'testuser' not found.")
    #         user = None # Ensure user is None if lookup fails

    # 2. Handle Deletion (POST Request)
    if request.method == 'POST' and user:
        routine_id_to_delete = request.POST.get('routine_id')
        if routine_id_to_delete:
            try:
                # IMPORTANT: Filter by BOTH pk and the determined user for security
                # This prevents User A deleting User B's routine even if they guess the ID
                routine_to_delete = get_object_or_404(Routine, pk=routine_id_to_delete, user=user)

                routine_pk_for_message = routine_to_delete.pk # Store before deleting
                routine_to_delete.delete()
                messages.success(request, f"Routine {routine_pk_for_message} for user '{username_to_display}' deleted successfully.")
                print(f"Deleted routine {routine_pk_for_message} for user {user.username}")
                # Redirect back to the same page to show the updated list
                return redirect('routine_list_delete')

            except ValueError: # Handle case where routine_id is not a valid number
                 messages.error(request, "Invalid Routine ID format provided for deletion.")
                 print(f"Invalid routine ID format for deletion attempt: {routine_id_to_delete}")
            except Routine.DoesNotExist: # Should be caught by get_object_or_404, but explicit handling is fine
                 messages.error(request, f"Routine {routine_id_to_delete} not found or does not belong to user '{username_to_display}'.")
                 print(f"Routine not found or access denied for deletion: ID {routine_id_to_delete}, User {user.username}")
            except Exception as e:
                 messages.error(request, f"An unexpected error occurred during deletion: {e}")
                 print(f"Unexpected error deleting routine {routine_id_to_delete} for user {user.username}: {e}")
                 # Consider logging the full traceback here
                 # print(traceback.format_exc())

        else:
            messages.warning(request, "Delete request received without a Routine ID.")
            print("Warning: POST request received without 'routine_id'.")

        # Redirect even if deletion failed validation, to avoid resubmission issues
        return redirect('routine_list_delete')


    # 3. Prepare Context for Listing (GET Request or after POST redirect)
    routines_list = []
    if user:
        # Fetch routines only if a user was successfully determined
        routines_list = Routine.objects.filter(user=user).order_by('-start_date')
        print(f"Found {routines_list.count()} routines for user {user.username}")
    elif not error_message:
        # This case should ideally not be reached if error handling is correct
        error_message = "Could not determine user to display routines for."

    context = {
        'routines': routines_list,
        'view_user': user, # Pass the user object (or None)
        'username_to_display': username_to_display, # Pass the username string
        'error_message': error_message,
    }

    return render(request, 'routine_list.html', context)


def routine_detail_view(request, routine_id):
    """
    Displays the details of a specific routine.
    Adds day names to day objects for easier template access.
    """
    routine = get_object_or_404(
        Routine.objects.prefetch_related(
            'days',
            'days__dailyfood_set',
            'days__dailyexercises_set'
        ),
        pk=routine_id
    )

    # --- Add day names in the view ---
    day_names = {
        1: 'Monday',
        2: 'Tuesday',
        3: 'Wednesday',
        4: 'Thursday',
        5: 'Friday',
        6: 'Saturday',
        7: 'Sunday',
    }

    # Get the days (already efficiently fetched by prefetch_related)
    # Convert to list to allow modification if needed, or just iterate
    days_with_names = []
    for day in routine.days.all().order_by('week_day'): # Order here is efficient
        # Add a new attribute to the day object in memory
        day.name_of_day = day_names.get(day.week_day, "Unknown Day") # Use .get for safety
        days_with_names.append(day)
    # --- End adding day names ---


    context = {
        'routine': routine,
        'days_to_display': days_with_names, # Pass the list with added names
        # 'day_names' dictionary is no longer needed in the template context
    }
    return render(request, 'routine.html', context)



# routine/views.py

# ... (keep your existing save_routine_from_json, chat_view, routine_detail_view functions) ...


# --- Add this DRF ViewSet for Routines API ---

class RoutineViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing user routines via JSON requests.

    Provides standard `list`, `retrieve`, `update`, `partial_update`, `destroy` actions.
    The `create` action is overridden to trigger AI generation.
    Requires user authentication.
    """
    serializer_class = RoutineSerializer # Used for list, retrieve, update output
    # permission_classes = [IsAuthenticated] # Only logged-in users can access

    def get_queryset(self):
        """ Returns routines belonging ONLY to the requesting user. """
        user=CustomUser.objects.get(username="testuser")
        # user = self.request.user
        return Routine.objects.filter(user=user).prefetch_related(
            'days',                     # Adjust related names if needed
            'days__dailyfood_set',
            'days__dailyexercises_set'
        ).order_by('-start_date')

    # We are overriding 'create', so perform_create isn't strictly needed
    # but is good practice if you ever use mixins or default create.
    # def perform_create(self, serializer):
    #     serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        """
        Handles POST requests to /api/routines/.
        Generates a new routine using AI based on validated input.
        """
        input_serializer = RoutineGenerationRequestSerializer(data=request.data)
        if not input_serializer.is_valid():
            return Response(input_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = input_serializer.validated_data
        user=CustomUser.objects.get(username="testuser")
        # user = request.user # DRF ensures this is the authenticated user

        # Prepare data for AI Prompt (same logic as chat_view)
        weight = validated_data['weight']
        height_m = validated_data['height']
        height_cm = height_m * 100
        age = validated_data['age']
        goal = validated_data['goal']

        # --- AI Generation Logic (extracted and adapted from chat_view) ---
        ai_response_text = None # For debugging/error reporting
        try:
            api_key = os.environ.get('GOOGLE_API_KEY')
            if not api_key:
                # Log the error server-side for security
                print("CRITICAL ERROR: GOOGLE_API_KEY environment variable not set.")
                return Response({'error': 'AI service configuration error.'},
                                status=status.HTTP_503_SERVICE_UNAVAILABLE)

            genai.configure(api_key=api_key)
            model_name = getattr(settings, 'GEMINI_MODEL_NAME', 'models/gemini-1.5-flash')
            model = genai.GenerativeModel(model_name)

            # --- Construct the Prompt ---
            # Define base_prompt ONCE
            base_prompt = f"User Profile: Age {age}, Weight {weight} kg, Height {height_cm} cm.\n"

            # Determine goal_instruction using the validated goal
            if goal == "gain_muscle":
                goal_instruction = "Generate a detailed weekly workout plan focused on muscle gain, including appropriate diet suggestions for each day to support muscle growth."
            elif goal == "lose_weight":
                goal_instruction = "Generate a detailed weekly diet and workout plan designed for weight loss, emphasizing calorie deficit and fat-burning exercises."
            elif goal == 'maintain':
                goal_instruction = "Generate a detailed weekly diet and workout plan for weight maintenance, balancing calorie intake and expenditure."

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
                      "reps": "integer (Number of repetitions per set. Use for rep-based exercises like Bench Press. **Use 0 or 1 if the exercise is primarily time-based and uses the 'duration' field.** For AMRAP exercises, use -1.)",
                      "duration": "integer (Duration of the exercise **IF** it's time-based, like Running, Cycling, Plank. **The unit (seconds or minutes) MUST be specified in the 'description' field.** Use 0 if the exercise is purely repetition-based.)"                    }
                    // Add more exercise objects for the day's workout as needed.
                    // Ensure ALL exercise objects include 'name', 'sets', and 'reps'. 'description' is a must.
                    // If it's a rest day workout-wise, this array should be empty: []
                  ]
                }
                // *** Include exactly 7 day objects in this list, one for each day from Monday (1) to Sunday (7). ***
              ]
            }
            ```
            Ensure the output is only the valid JSON data, adhering strictly to the specified types (string, integer). Pay close attention to providing only integers for 'total_calories', 'sets', and 'reps'. Do not add any conversational text outside the JSON structure.
            """


            prompt = base_prompt + goal_instruction + "\n\n" + json_format_instruction
            # --- End Prompt Construction ---
            safety_settings = [
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                # Add others if needed, e.g., HARASSMENT, HATE_SPEECH, SEXUALLY_EXPLICIT
            ]
            print("--- Sending Prompt to AI (DRF ViewSet) ---")
            response = model.generate_content(prompt, safety_settings=safety_settings)
            ai_response_text = response.text
            print("--- Raw AI Response (DRF ViewSet) ---")
            print(ai_response_text) # Good for server logs
            print("------------------------------------")

            # --- Parse the JSON Response (Identical logic to chat_view) ---
            parsed_data = None
            try:
                cleaned_response_text = ai_response_text.strip().strip('```json').strip('```').strip()
                if not cleaned_response_text:
                     raise json.JSONDecodeError("Received empty response from AI.", "", 0)
                if not cleaned_response_text.startswith('{') or not cleaned_response_text.endswith('}'):
                     raise json.JSONDecodeError("Response does not start/end with curly braces.", cleaned_response_text, 0)
                parsed_data = json.loads(cleaned_response_text)
            except json.JSONDecodeError as json_err:
                print(f"DRF JSON Decode Error: {json_err}")
                print(f"Failed raw AI response (DRF):\n{ai_response_text}") # Log raw response
                error_message = (
                    f'AI response could not be parsed as valid JSON. '
                    f'Error: {json_err.msg} at pos {json_err.pos}. '
                    'Check server logs.'
                )
                return Response({'error': error_message}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
            # --- End JSON Parsing ---

            # --- Save to Database using the SHARED helper function ---
            try:
                # Call the same function used by chat_view
                created_routine = save_routine_from_json(parsed_data, user)

                # Success! Serialize the NEW routine using the main RoutineSerializer
                output_serializer = self.get_serializer(created_routine)
                return Response(output_serializer.data, status=status.HTTP_201_CREATED)

            except Exception as db_err:
                print(f"DRF Database Save Error: {db_err}")
                print(traceback.format_exc())
                return Response({'error': f'Failed to save generated plan to database: {db_err}'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            # --- End Database Save ---

        # --- Handle Specific AI/Generation Errors ---
        except genai.types.generation_types.BlockedPromptException as blocked_err:
             print(f"DRF AI Generation Blocked: {blocked_err}")
             return Response({'error': 'Request blocked by AI safety filters.'}, status=status.HTTP_400_BAD_REQUEST)
        except genai.types.generation_types.StopCandidateException as stop_err:
             print(f"DRF AI Generation Stopped Early: {stop_err}")
             return Response({
                'error': f'AI stopped generating unexpectedly. (Reason: {stop_err})',
                'raw_response': ai_response_text # Provide partial response if any
             }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            print(f"Unexpected error during DRF AI interaction: {e}")
            print(traceback.format_exc())
            return Response({'error': f'Unexpected server error during AI generation: {str(e)}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        # --- End AI/Generation Error Handling ---

    # Default list, retrieve, update, partial_update, destroy actions
    # from ModelViewSet will use get_queryset and RoutineSerializer.
# --- End DRF ViewSet ---