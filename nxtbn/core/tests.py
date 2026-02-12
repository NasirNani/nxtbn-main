from django.test import TestCase
from django.urls import reverse

from nxtbn.product.models import Product, ProductVariant
from nxtbn.users.models import User
from nxtbn.vendor.models import Vendor


class CoreHealthAndRateLimitTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="creator", email="creator@example.com", password="pass12345")
        self.vendor = Vendor.objects.create(name="Core Vendor")
        self.product = Product.objects.create(
            created_by=self.user,
            last_modified_by=self.user,
            name="Rate Product",
            summary="Summary",
            description="Description",
            vendor=self.vendor,
            is_live=True,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            name="Default",
            compare_at_price="30.00",
            price="20.00",
            cost_per_unit="10.00",
            stock=3,
        )
        self.product.default_variant = self.variant
        self.product.save(update_fields=["default_variant"])

    def test_health_endpoint(self):
        response = self.client.get(reverse("health_check"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_review_post_rate_limit(self):
        url = reverse("product_detail", kwargs={"product_id": self.product.id})
        for _ in range(20):
            self.client.post(url, {"rating": "5", "comment": "test"})
        blocked = self.client.post(url, {"rating": "5", "comment": "blocked"})
        self.assertEqual(blocked.status_code, 429)
