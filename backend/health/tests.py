from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from unittest.mock import Mock, patch

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
                "ocr_text": (
                    "Hemoglobin 12.8 g/dL 12-16\n"
                    "WBC 6500 cells/uL 4000-11000\n"
                    "Doctor advice: repeat CBC after 2 weeks and keep hydration adequate."
                ),
            },
        )
        self.assertEqual(response.status_code, 302)
        report = MedicalReport.objects.filter(user=self.user1).latest("id")
        self.assertFalse(bool(report.report_file))
        self.assertTrue(report.parameters.exists())
        self.assertTrue(report.doctor_suggestions)

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

    def test_report_detail_shows_graphical_trends(self):
        self.client.login(username="u1", password="pass12345")
        self.client.post(
            reverse("report-upload"),
            {
                "report_date": "2026-02-24",
                "ocr_text": "Hemoglobin 11.5 g/dL 12-16",
            },
        )
        self.client.post(
            reverse("report-upload"),
            {
                "report_date": "2026-02-25",
                "ocr_text": "Hemoglobin 12.2 g/dL 12-16",
            },
        )
        report = MedicalReport.objects.filter(user=self.user1).latest("id")
        response = self.client.get(reverse("report-detail", args=[report.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Graphical Trend Analysis")

    @patch("health.views.requests.get")
    def test_translate_endpoint_returns_translated_text(self, mock_get):
        self.client.login(username="u1", password="pass12345")
        mock_response = Mock()
        mock_response.json.return_value = [[["Hola", "Hello", None, None]]]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        response = self.client.post(
            reverse("report-translate"),
            data='{"text":"Hello","source_lang":"en","target_lang":"es-ES"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get("translated_text"), "Hola")
