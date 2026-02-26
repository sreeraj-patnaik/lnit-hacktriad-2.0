from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse


class CoreAuthTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_signup_creates_user_and_profile(self):
        response = self.client.post(
            reverse("signup"),
            {
                "username": "alice",
                "email": "alice@example.com",
                "password1": "StrongPass123",
                "password2": "StrongPass123",
            },
        )
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="alice")
        self.assertTrue(hasattr(user, "userprofile"))

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_logout_logs_user_out(self):
        User.objects.create_user(username="bob", password="pass12345")
        self.client.login(username="bob", password="pass12345")
        response = self.client.post(reverse("logout"))
        self.assertEqual(response.status_code, 302)
        dashboard_response = self.client.get(reverse("dashboard"))
        self.assertEqual(dashboard_response.status_code, 302)
