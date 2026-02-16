from django.test import TestCase, override_settings
from django.urls import reverse

from nxtbn.order.models import Order
from nxtbn.product.models import Product, ProductVariant
from nxtbn.users.models import User
from nxtbn.vendor.models import Vendor


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
class AdminPanelSmokeTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="admin_staff",
            email="admin_staff@example.com",
            password="pass12345",
            is_staff=True,
            is_superuser=True,
        )
        self.user = User.objects.create_user(
            username="regular_user",
            email="regular_user@example.com",
            password="pass12345",
        )

    def test_staff_can_load_admin_index(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "/admin/logout/")

    def test_non_staff_cannot_load_admin_index(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("admin:index"))
        self.assertIn(response.status_code, [302, 403])


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
class AdminCsvWorkflowTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="csv_admin",
            email="csv_admin@example.com",
            password="pass12345",
            is_staff=True,
            is_superuser=True,
        )
        self.owner = User.objects.create_user(
            username="csv_owner",
            email="csv_owner@example.com",
            password="pass12345",
        )
        self.vendor = Vendor.objects.create(name="CSV Vendor")
        self.product = Product.objects.create(
            created_by=self.owner,
            last_modified_by=self.owner,
            name="CSV Product",
            summary="CSV summary",
            description="CSV description",
            category="csv",
            vendor=self.vendor,
            is_live=True,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            name="Default",
            compare_at_price="120.00",
            price="100.00",
            cost_per_unit="90.00",
            stock=4,
        )
        self.product.default_variant = self.variant
        self.product.save(update_fields=["default_variant"])
        self.order = Order.objects.create(
            user=self.owner,
            full_name="CSV Owner",
            email="csv_owner@example.com",
            phone="555",
            address_line1="Address",
            city="Istanbul",
            state="Istanbul",
            postal_code="34000",
            country="Turkiye",
            total="100.00",
            subtotal="100.00",
        )

    def test_product_import_page_is_reachable(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("admin:product_product_import_csv"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CSV dosyasi")

    def test_product_export_returns_csv(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("admin:product_product_export_csv"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("products_export.csv", response["Content-Disposition"])
        self.assertContains(response, "product_id")

    def test_order_export_returns_csv(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("admin:order_order_export_csv"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("orders_export.csv", response["Content-Disposition"])
        self.assertContains(response, "order_id")
