from django.contrib.auth.models import User
from django.db import models


class MedicalReport(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="medical_reports")
    report_file = models.FileField(upload_to="reports/", blank=True, null=True)
    report_date = models.DateField()
    analysis_completed = models.BooleanField(default=False)
    ocr_text = models.TextField(blank=True)
    doctor_suggestions = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-report_date", "-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.report_date}"


class LabParameter(models.Model):
    RISK_CHOICES = [
        ("normal", "Normal"),
        ("low", "Low"),
        ("high", "High"),
        ("unknown", "Unknown"),
    ]

    report = models.ForeignKey(MedicalReport, on_delete=models.CASCADE, related_name="parameters")
    name = models.CharField(max_length=120)
    value = models.FloatField()
    unit = models.CharField(max_length=30, blank=True)
    ref_min = models.FloatField(null=True, blank=True)
    ref_max = models.FloatField(null=True, blank=True)
    risk_flag = models.CharField(max_length=20, choices=RISK_CHOICES, default="unknown")

    def __str__(self):
        return f"{self.name}: {self.value} {self.unit}".strip()


class AnalysisResult(models.Model):
    report = models.OneToOneField(MedicalReport, on_delete=models.CASCADE, related_name="analysis")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="analysis_results")
    mentor_summary = models.TextField(blank=True)
    trend_analysis = models.TextField(blank=True)
    doctor_summary = models.TextField(blank=True)
    raw_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Analysis for report {self.report_id}"
