from django.test import TestCase
from django.urls import reverse
from django.core.cache import cache

from nxtbn.product.models import Product, ProductReview, ProductVariant
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
