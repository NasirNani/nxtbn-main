from django.test import TestCase, override_settings
from django.urls import reverse

from nxtbn.users.models import User


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
class DashboardAccessTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="pass12345",
            is_staff=True,
            is_superuser=True,
        )
        self.user = User.objects.create_user(
            username="plain",
            email="plain@example.com",
            password="pass12345",
        )

    def test_staff_can_view_dashboard(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("admin_analytics_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Operations Dashboard")

    def test_non_staff_cannot_view_dashboard(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("admin_analytics_dashboard"))
        self.assertIn(response.status_code, [302, 403])
