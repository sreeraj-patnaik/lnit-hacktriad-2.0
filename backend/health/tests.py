from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from .models import AnalysisResult, MedicalReport


class HealthFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(username="u1", password="pass12345")
        self.user2 = User.objects.create_user(username="u2", password="pass12345")

    def test_user_cannot_access_other_user_report(self):
        report = MedicalReport.objects.create(
            user=self.user1,
            report_file=SimpleUploadedFile("r1.txt", b"dummy"),
            report_date="2026-02-20",
        )
        self.client.login(username="u2", password="pass12345")
        response = self.client.get(reverse("report-detail", args=[report.id]))
        self.assertEqual(response.status_code, 404)

    def test_upload_creates_analysis_for_same_user(self):
        self.client.login(username="u1", password="pass12345")
        response = self.client.post(
            reverse("report-upload"),
            {
                "report_date": "2026-02-21",
                "report_file": SimpleUploadedFile("new.txt", b"test content"),
            },
        )
        self.assertEqual(response.status_code, 302)
        report = MedicalReport.objects.filter(user=self.user1).latest("id")
        self.assertTrue(AnalysisResult.objects.filter(report=report, user=self.user1).exists())

    def test_text_only_upload_creates_report(self):
        self.client.login(username="u1", password="pass12345")
        response = self.client.post(
            reverse("report-upload"),
            {
                "report_date": "2026-02-22",
                "ocr_text": "Hemoglobin 12.8 g/dL 12-16\nWBC 6500 cells/uL 4000-11000",
            },
        )
        self.assertEqual(response.status_code, 302)
        report = MedicalReport.objects.filter(user=self.user1).latest("id")
        self.assertFalse(bool(report.report_file))
        self.assertTrue(report.parameters.exists())

    def test_image_upload_still_analyzes_with_fallback(self):
        self.client.login(username="u1", password="pass12345")
        response = self.client.post(
            reverse("report-upload"),
            {
                "report_date": "2026-02-23",
                "report_file": SimpleUploadedFile("scan.jpg", b"fake-image-bytes", content_type="image/jpeg"),
            },
        )
        self.assertEqual(response.status_code, 302)
        report = MedicalReport.objects.filter(user=self.user1).latest("id")
        self.assertTrue(AnalysisResult.objects.filter(report=report, user=self.user1).exists())
