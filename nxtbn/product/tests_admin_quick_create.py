from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from nxtbn.core.enum_helper import StockStatus
from nxtbn.filemanager.models import Image
from nxtbn.product.models import Category, Product
from nxtbn.users.models import User
from nxtbn.vendor.models import Vendor


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
class ProductQuickCreateAdminTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_user(
            username="quick_admin",
            email="quick_admin@example.com",
            password="pass12345",
            is_staff=True,
            is_superuser=True,
        )
        self.category = Category.objects.create(name="Ortopedi")
        self.vendor = Vendor.objects.create(name="Mevcut Tedarikci")
        self.quick_add_url = reverse("admin:product_product_quick_add")
        self.changelist_url = reverse("admin:product_product_changelist")

    def test_quick_create_creates_draft_product_with_default_variant(self):
        self.client.force_login(self.superuser)
        response = self.client.post(
            self.quick_add_url,
            data={
                "name": "Hizli Urun",
                "vendor": str(self.vendor.id),
                "category_ref": str(self.category.id),
                "price": "150.000",
                "stock": "5",
                "_continue": "1",
            },
        )

        self.assertEqual(response.status_code, 302)
        product = Product.objects.get(name="Hizli Urun")
        self.assertFalse(product.is_live)
        self.assertEqual(product.category_ref_id, self.category.id)
        self.assertEqual(product.category, self.category.name)
        self.assertIsNotNone(product.default_variant_id)
        self.assertEqual(product.default_variant.name, "Varsayilan")
        self.assertEqual(product.default_variant.stock, 5)
        self.assertEqual(product.default_variant.stock_status, StockStatus.IN_STOCK)

    def test_quick_create_vendor_inline_deduplicates_case_insensitive(self):
        self.client.force_login(self.superuser)
        Vendor.objects.create(name="Case Vendor")

        response = self.client.post(
            self.quick_add_url,
            data={
                "name": "Inline Vendor Urunu",
                "vendor": "",
                "new_vendor_name": "  case   vendor ",
                "category_ref": str(self.category.id),
                "price": "90.000",
                "stock": "0",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Vendor.objects.filter(name__iexact="case vendor").count(), 1)
        product = Product.objects.get(name="Inline Vendor Urunu")
        self.assertEqual(product.vendor.name, "Case Vendor")

    def test_user_without_add_vendor_permission_cannot_use_inline_vendor(self):
        limited_staff = User.objects.create_user(
            username="limited_staff",
            email="limited_staff@example.com",
            password="pass12345",
            is_staff=True,
        )
        add_product_permission = Permission.objects.get(codename="add_product")
        view_product_permission = Permission.objects.get(codename="view_product")
        limited_staff.user_permissions.add(add_product_permission, view_product_permission)

        self.client.force_login(limited_staff)
        get_response = self.client.get(self.quick_add_url)
        self.assertEqual(get_response.status_code, 200)
        self.assertNotContains(get_response, "Yeni Tedarikci Adi")

        post_response = self.client.post(
            self.quick_add_url,
            data={
                "name": "Yetki Test Urunu",
                "category_ref": str(self.category.id),
                "price": "80.000",
                "new_vendor_name": "Yetkisiz Vendor",
            },
        )
        self.assertEqual(post_response.status_code, 200)
        self.assertContains(post_response, "Tedarikci secimi zorunludur.")
        self.assertFalse(Product.objects.filter(name="Yetki Test Urunu").exists())

    def test_changelist_add_button_points_to_quick_add(self):
        self.client.force_login(self.superuser)
        response = self.client.get(self.changelist_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("admin:product_product_quick_add"))

    def test_quick_create_attaches_uploaded_image_to_default_variant(self):
        self.client.force_login(self.superuser)
        gif_bytes = (
            b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00"
            b"\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00"
            b"\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        )
        upload = SimpleUploadedFile("quick.gif", gif_bytes, content_type="image/gif")

        response = self.client.post(
            self.quick_add_url,
            data={
                "name": "Gorselli Hizli Urun",
                "vendor": str(self.vendor.id),
                "category_ref": str(self.category.id),
                "price": "200.000",
                "stock": "2",
                "image": upload,
            },
        )

        self.assertEqual(response.status_code, 302)
        product = Product.objects.get(name="Gorselli Hizli Urun")
        self.assertIsNotNone(product.default_variant_id)
        self.assertEqual(product.default_variant.variant_image.count(), 1)
        self.assertEqual(Image.objects.count(), 1)
