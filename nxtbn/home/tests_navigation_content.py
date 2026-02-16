from django.contrib import admin
from django.test import RequestFactory
from django.test import TestCase, override_settings
from django.urls import reverse

from nxtbn.home.models import FooterSocialLink, SiteNavText
from nxtbn.users.models import User


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
class StorefrontNavigationContentTests(TestCase):
    def setUp(self):
        self.home_url = reverse("home")
        self.products_url = reverse("products_list")
        self.contact_url = reverse("contact_page")
        self.about_url = reverse("about_page")

    def test_nav_links_are_rendered_in_navbar_and_footer(self):
        response = self.client.get(self.home_url, HTTP_ACCEPT_LANGUAGE="tr")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")

        self.assertIn("Tum Urunler", html)
        self.assertIn("Iletisim", html)
        self.assertIn("Hakkimizda", html)
        self.assertIn("Daha Fazla Bilgi", html)
        self.assertGreaterEqual(html.count("Tum Urunler"), 2)

    def test_url_destinations_are_locked_in_code(self):
        nav_item = SiteNavText.objects.get(key=SiteNavText.KEY_MORE_INFO)
        nav_item.label_tr = "Bilgi Merkezi"
        nav_item.label_en = "Info Center"
        nav_item.save(update_fields=["label_tr", "label_en"])

        response = self.client.get(self.home_url, HTTP_ACCEPT_LANGUAGE="en")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")

        self.assertIn("Info Center", html)
        self.assertIn('href="https://flexymedical.com/"', html)
        self.assertIn(f'href="{self.products_url}"', html)
        self.assertIn(f'href="{self.contact_url}"', html)
        self.assertIn(f'href="{self.about_url}"', html)

    def test_english_nav_uses_label_en(self):
        nav_item = SiteNavText.objects.get(key=SiteNavText.KEY_ABOUT_US)
        nav_item.label_en = "About Our Team"
        nav_item.save(update_fields=["label_en"])

        response = self.client.get(self.home_url, HTTP_ACCEPT_LANGUAGE="en")
        self.assertContains(response, "About Our Team")

    def test_missing_nav_row_falls_back_to_default(self):
        SiteNavText.objects.filter(key=SiteNavText.KEY_ABOUT_US).delete()

        response = self.client.get(self.home_url, HTTP_ACCEPT_LANGUAGE="en")
        html = response.content.decode("utf-8")

        self.assertIn("About Us", html)
        self.assertIn(f'href="{self.about_url}"', html)

    def test_footer_social_links_are_dynamic_and_sorted(self):
        FooterSocialLink.objects.create(
            platform=FooterSocialLink.PLATFORM_YOUTUBE,
            url="https://youtube.com/flexy",
            label="YouTube",
            sort_order=30,
            is_active=True,
        )
        FooterSocialLink.objects.create(
            platform=FooterSocialLink.PLATFORM_INSTAGRAM,
            url="https://instagram.com/flexy",
            label="Instagram",
            sort_order=10,
            is_active=True,
        )
        FooterSocialLink.objects.create(
            platform=FooterSocialLink.PLATFORM_FACEBOOK,
            url="https://facebook.com/flexy",
            label="Facebook",
            sort_order=20,
            is_active=False,
        )

        response = self.client.get(self.home_url)
        html = response.content.decode("utf-8")
        self.assertIn("https://instagram.com/flexy", html)
        self.assertIn("https://youtube.com/flexy", html)
        self.assertNotIn("https://facebook.com/flexy", html)

        self.assertLess(html.index("https://instagram.com/flexy"), html.index("https://youtube.com/flexy"))


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
class NavigationAdminTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_user(
            username="admin_nav",
            email="admin_nav@example.com",
            password="pass12345",
            is_staff=True,
            is_superuser=True,
        )
        self.request_factory = RequestFactory()
        self.client.force_login(self.superuser)

    def test_nav_text_admin_disables_add_and_delete(self):
        model_admin = admin.site._registry[SiteNavText]
        request = self.request_factory.get("/admin/home/sitenavtext/")
        request.user = self.superuser
        self.assertFalse(model_admin.has_add_permission(request))
        self.assertFalse(model_admin.has_delete_permission(request))

    def test_admin_sidebar_contains_site_content_section(self):
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Site Icerigi")
        self.assertContains(response, "Navbar ve Footer Metinleri")
        self.assertContains(response, "Sosyal Medya Linkleri")
