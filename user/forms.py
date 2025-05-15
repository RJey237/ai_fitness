# user/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
# Import your custom user model OR use get_user_model
# from .models import CustomUser
from django.contrib.auth import get_user_model

User = get_user_model() # Good practice: Gets the user model defined in settings.py
# user/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model

User = get_user_model() # Good practice: Gets the user model defined in settings.py

class RegistrationForm(UserCreationForm):
    # Add email field
    email = forms.EmailField(
        required=True, # Make email required
        widget=forms.EmailInput(attrs={'autocomplete': 'email', 'placeholder': 'Enter your email'})
    )

    # Explicitly define password1 (as provided in your code)
    # Note: Inherited UserCreationForm already defines this,
    # explicitly defining allows easier widget customization but isn't strictly needed
    # unless changing behavior significantly.
    password1 = forms.CharField(
        label='Password',
        strip=False, # Don't strip whitespace from passwords
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password', 'placeholder': 'Enter password'}),
        help_text="Your password can't be too similar to your other personal information.<br>Your password must contain at least 8 characters.<br>Your password can't be a commonly used password.<br>Your password can't be entirely numeric.",
    )

    # Explicitly define password2 (as provided in your code)
    password2 = forms.CharField(
        label='Confirm password',
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password', 'placeholder': 'Confirm password'})
    )

    class Meta(UserCreationForm.Meta):
        model = User # Use the user model fetched by get_user_model()
        # Define the fields you want on the form AND their order
        # 'password1' and 'password2' are handled by UserCreationForm base fields implicitly
        # unless explicitly overridden like above.
        # This 'fields' tuple mainly controls which *model* fields besides passwords are shown.
        fields = ('username', 'email') # Add 'first_name', 'last_name' if needed

    def clean_password2(self):
        # Ensure both password fields match.
        # *** CORRECTED: Use password1 here ***
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            # This message will appear in form.non_field_errors or form.password2.errors
            # depending on Django version/setup
            raise forms.ValidationError("Passwords don't match.", code='password_mismatch')
        return password2

    # save() method is inherited from UserCreationForm, handles hashing.