from django.contrib import admin

from .models import LLMContextSnapshot, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "age", "gender", "city", "updated_at")
    search_fields = ("user__username", "user__email", "city")


@admin.register(LLMContextSnapshot)
class LLMContextSnapshotAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "source", "created_at")
    search_fields = ("user__username", "source")

# Register your models here.
