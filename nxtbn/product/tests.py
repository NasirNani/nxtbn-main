from django.test import TestCase
from django.urls import reverse
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile

from nxtbn.filemanager.models import Image
from nxtbn.product.models import Category, Product, ProductReview, ProductVariant
from nxtbn.users.models import User
from nxtbn.vendor.models import Vendor


class ProductViewsTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username="buyer", email="buyer@example.com", password="pass12345")
        self.vendor = Vendor.objects.create(name="Vendor")

        self.product_a = Product.objects.create(
            created_by=self.user,
            last_modified_by=self.user,
            name="Knee Brace Basic",
            summary="Basic support",
            description="Basic support for knee",
            category="knee",
            vendor=self.vendor,
            is_live=True,
        )
        self.variant_a = ProductVariant.objects.create(
            product=self.product_a,
            name="Default",
            compare_at_price="150.00",
            price="100.00",
            cost_per_unit="60.00",
            stock=10,
        )
        self.product_a.default_variant = self.variant_a
        self.product_a.save(update_fields=["default_variant"])

        self.product_b = Product.objects.create(
            created_by=self.user,
            last_modified_by=self.user,
            name="Ankle Wrap",
            summary="Ankle support",
            description="Support for ankle",
            category="ankle",
            vendor=self.vendor,
            is_live=True,
        )
        self.variant_b = ProductVariant.objects.create(
            product=self.product_b,
            name="Default",
            compare_at_price="50.00",
            price="30.00",
            cost_per_unit="20.00",
            stock=5,
        )
        self.product_b.default_variant = self.variant_b
        self.product_b.save(update_fields=["default_variant"])

    def test_catalog_filters_by_query_category_and_price(self):
        response = self.client.get(
            reverse("products_list"),
            {"q": "ankle", "category": "ankle", "price": "25_50"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ankle Wrap")
        self.assertNotContains(response, "Knee Brace Basic")

    def test_review_create_or_update(self):
        self.client.force_login(self.user)
        detail_url = reverse("product_detail", kwargs={"product_id": self.product_a.id})

        response = self.client.post(detail_url, {"rating": "4", "comment": "Good"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ProductReview.objects.filter(product=self.product_a, user=self.user).count(), 1)

        response = self.client.post(detail_url, {"rating": "5", "comment": "Great"})
        self.assertEqual(response.status_code, 302)
        review = ProductReview.objects.get(product=self.product_a, user=self.user)
        self.assertEqual(review.rating, 5)

    def test_catalog_uses_non_default_variant_image_as_fallback(self):
        extra_variant = ProductVariant.objects.create(
            product=self.product_a,
            name="Alt",
            compare_at_price="200.00",
            price="180.00",
            cost_per_unit="120.00",
            stock=5,
        )
        gif_bytes = (
            b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00"
            b"\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00"
            b"\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        )
        image = Image.objects.create(
            created_by=self.user,
            last_modified_by=self.user,
            name="fallback",
            image=SimpleUploadedFile("fallback.gif", gif_bytes, content_type="image/gif"),
            image_alt_text="fallback",
        )
        extra_variant.variant_image.add(image)

        response = self.client.get(reverse("products_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, image.image.url)


class ProductCategoryCompatibilityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", email="owner@example.com", password="pass12345")
        self.vendor = Vendor.objects.create(name="Vendor")

    def test_text_category_auto_maps_to_category_ref(self):
        product = Product.objects.create(
            created_by=self.user,
            last_modified_by=self.user,
            name="Neck Support",
            summary="Summary",
            description="Description",
            category="  neck   support  ",
            vendor=self.vendor,
        )

        self.assertIsNotNone(product.category_ref_id)
        self.assertEqual(product.category_ref.name, "neck support")
        self.assertEqual(product.category, "neck support")

    def test_category_ref_syncs_legacy_text(self):
        category = Category.objects.create(name="Ortez")
        product = Product.objects.create(
            created_by=self.user,
            last_modified_by=self.user,
            name="Back Brace",
            summary="Summary",
            description="Description",
            category_ref=category,
            vendor=self.vendor,
        )

        self.assertEqual(product.category_ref_id, category.id)
        self.assertEqual(product.category, "Ortez")
