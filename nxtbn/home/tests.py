from django.test import TestCase
from django.test import override_settings
from django.urls import reverse

from nxtbn.users.tests import UserFactory


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
class HomeViewTests(TestCase):
    def test_home_renders_for_guest(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home/index.html")

    def test_home_renders_for_authenticated_user(self):
        user = UserFactory()
        self.client.force_login(user)

        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home/index.html")

    def test_modules_index_renders(self):
        response = self.client.get(reverse("modules_index"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home/modules_index.html")

    def test_module_detail_renders(self):
        response = self.client.get(reverse("module_detail", kwargs={"app_label": "product"}))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home/module_detail.html")

    def test_about_page_renders(self):
        response = self.client.get(reverse("about_page"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home/about.html")

    def test_contact_page_renders(self):
        response = self.client.get(reverse("contact_page"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home/contact.html")
