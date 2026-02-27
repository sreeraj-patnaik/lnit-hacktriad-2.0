from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):

    LOCATION_CHOICES = [
        ("rural", "Rural"),
        ("urban", "Urban"),
        ("semi-urban", "Semi Urban"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)

    age = models.IntegerField(null=True, blank=True)
    gender = models.CharField(max_length=20, blank=True)
    city = models.CharField(max_length=100, blank=True)

    location_type = models.CharField(
        max_length=20,
        choices=LOCATION_CHOICES,
        blank=True
    )

    # Lifestyle
    sleep_hours = models.FloatField(null=True, blank=True)
    activity_level = models.CharField(max_length=50, blank=True)
    diet_type = models.CharField(max_length=100, blank=True)

    
    occupation = models.CharField(max_length=150, blank=True)

    past_medical_conditions = models.TextField(blank=True)
    current_symptoms = models.TextField(blank=True)
    medications = models.TextField(blank=True)

    health_goal = models.CharField(max_length=255, blank=True)
    language_preference = models.CharField(max_length=50, blank=True)

    smoking_status = models.CharField(max_length=50, blank=True)
    alcohol_consumption = models.CharField(max_length=50, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.username
    

class LLMContextSnapshot(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    context_json = models.JSONField()

    source = models.CharField(max_length=50, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)