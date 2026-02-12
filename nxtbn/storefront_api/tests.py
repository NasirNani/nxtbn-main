from django.test import TestCase
from django.urls import reverse

from nxtbn.order.models import Order
from nxtbn.product.models import Product, ProductVariant
from nxtbn.users.models import CustomerAddress
from nxtbn.users.models import User
from nxtbn.vendor.models import Vendor


class StorefrontApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="apiuser", email="api@example.com", password="pass12345")
        vendor = Vendor.objects.create(name="API Vendor")
        self.product = Product.objects.create(
            created_by=self.user,
            last_modified_by=self.user,
            name="API Product",
            summary="API summary",
            description="API description",
            category="api",
            vendor=vendor,
            is_live=True,
        )
        variant = ProductVariant.objects.create(
            product=self.product,
            name="Default",
            compare_at_price="120.00",
            price="90.00",
            cost_per_unit="60.00",
            stock=5,
        )
        self.product.default_variant = variant
        self.product.save(update_fields=["default_variant"])

    def test_products_endpoint_returns_results(self):
        response = self.client.get(reverse("api_products"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

    def test_orders_endpoint_requires_auth(self):
        response = self.client.get(reverse("api_orders"))
        self.assertEqual(response.status_code, 401)

        Order.objects.create(
            user=self.user,
            full_name="Api User",
            email=self.user.email,
            address_line1="Addr",
            city="Istanbul",
            state="Istanbul",
            postal_code="34000",
            country="Turkiye",
            total="90.00",
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse("api_orders"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

    def test_account_endpoints_require_auth(self):
        response = self.client.get(reverse("api_account_summary"))
        self.assertEqual(response.status_code, 401)

        response = self.client.get(reverse("api_account_addresses"))
        self.assertEqual(response.status_code, 401)

    def test_account_addresses_crud(self):
        self.client.force_login(self.user)
        create = self.client.post(
            reverse("api_account_addresses"),
            data={
                "label": "Ev",
                "full_name": "Api User",
                "phone": "5551112233",
                "city": "Istanbul",
                "district": "Kadikoy",
                "postal_code": "34000",
                "address_line1": "Adres satiri 1",
                "address_line2": "",
                "country": "Turkiye",
                "is_default_shipping": True,
            },
            content_type="application/json",
        )
        self.assertEqual(create.status_code, 201)
        address_id = create.json()["id"]

        listing = self.client.get(reverse("api_account_addresses"))
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.json()["count"], 1)

        patch = self.client.patch(
            reverse("api_account_address_detail", kwargs={"address_id": address_id}),
            data={"city": "Ankara"},
            content_type="application/json",
        )
        self.assertEqual(patch.status_code, 200)
        self.assertEqual(patch.json()["city"], "Ankara")

        delete = self.client.delete(reverse("api_account_address_detail", kwargs={"address_id": address_id}))
        self.assertEqual(delete.status_code, 204)
        self.assertFalse(CustomerAddress.objects.filter(id=address_id, is_active=True).exists())
