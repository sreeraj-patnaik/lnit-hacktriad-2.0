from django.contrib import admin

from .models import AnalysisResult, LabParameter, MedicalReport


class LabParameterInline(admin.TabularInline):
    model = LabParameter
    extra = 0


@admin.register(MedicalReport)
class MedicalReportAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "report_date", "analysis_completed", "created_at")
    list_filter = ("analysis_completed", "report_date")
    search_fields = ("user__username", "user__email")
    inlines = [LabParameterInline]


@admin.register(AnalysisResult)
class AnalysisResultAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "report", "created_at")
    search_fields = ("user__username", "report__id")

# Register your models here.
