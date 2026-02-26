from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import UserProfile


class SignupForm(UserCreationForm):
    email = forms.EmailField(required=True)
    age = forms.IntegerField(required=False)
    gender = forms.CharField(required=False)
    city = forms.CharField(required=False)
    location_type = forms.ChoiceField(required=False, choices=UserProfile.LOCATION_CHOICES)
    sleep_hours = forms.FloatField(required=False)
    activity_level = forms.CharField(required=False)
    diet_type = forms.CharField(required=False)
    occupation = forms.CharField(required=False)
    past_medical_conditions = forms.CharField(required=False, widget=forms.Textarea)
    current_symptoms = forms.CharField(required=False, widget=forms.Textarea)
    medications = forms.CharField(required=False, widget=forms.Textarea)
    health_goal = forms.CharField(required=False)
    language_preference = forms.CharField(required=False)
    smoking_status = forms.CharField(required=False)
    alcohol_consumption = forms.CharField(required=False)

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "password1",
            "password2",
            "age",
            "gender",
            "city",
            "location_type",
            "sleep_hours",
            "activity_level",
            "diet_type",
            "occupation",
            "past_medical_conditions",
            "current_symptoms",
            "medications",
            "health_goal",
            "language_preference",
            "smoking_status",
            "alcohol_consumption",
        )

    def save(self, commit=True):
        user = super().save(commit=commit)
        profile = user.userprofile
        for field in (
            "age",
            "gender",
            "city",
            "location_type",
            "sleep_hours",
            "activity_level",
            "diet_type",
            "occupation",
            "past_medical_conditions",
            "current_symptoms",
            "medications",
            "health_goal",
            "language_preference",
            "smoking_status",
            "alcohol_consumption",
        ):
            setattr(profile, field, self.cleaned_data.get(field))
        profile.save()
        return user


class LoginForm(AuthenticationForm):
    username = forms.CharField(max_length=150)


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        exclude = ("user", "created_at", "updated_at")
