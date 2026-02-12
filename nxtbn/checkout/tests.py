from django.test import TestCase
from django.test import override_settings
from django.urls import reverse

from nxtbn.order.models import Order, OrderItem
from nxtbn.product.models import Product, ProductVariant
from nxtbn.users.models import CustomerAddress
from nxtbn.users.models import User
from nxtbn.vendor.models import Vendor


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
class CheckoutFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="store_admin", email="store@example.com", password="test1234")
        self.vendor = Vendor.objects.create(name="Acme Vendor")
        self.product = Product.objects.create(
            created_by=self.user,
            last_modified_by=self.user,
            name="Starter Product",
            summary="Short summary",
            description="Long description",
            vendor=self.vendor,
            currency="TRY",
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            name="Default",
            compare_at_price="19.99",
            price="14.99",
            cost_per_unit="10.00",
            stock=5,
            sku="SKU-STARTER-001",
        )

    def test_catalog_page_renders(self):
        response = self.client.get(reverse("products_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Starter Product")

    def test_add_to_cart_and_place_order(self):
        self.client.login(username="store_admin", password="test1234")
        add_response = self.client.post(reverse("cart_add", kwargs={"variant_id": self.variant.id}), {"quantity": 2})
        self.assertEqual(add_response.status_code, 302)

        cart_response = self.client.get(reverse("cart"))
        self.assertEqual(cart_response.status_code, 200)
        self.assertContains(cart_response, "Starter Product")

        checkout_response = self.client.post(
            reverse("checkout"),
            {
                "full_name": "Buyer Name",
                "email": "buyer@example.com",
                "phone": "1234567890",
                "address_line1": "123 Main St",
                "address_line2": "",
                "city": "Austin",
                "district": "Downtown",
                "state": "TX",
                "postal_code": "78701",
                "country": "United States",
                "payment_method": "cod",
                "notes": "Deliver fast",
            },
        )
        self.assertEqual(checkout_response.status_code, 302)

        self.assertEqual(Order.objects.count(), 1)
        order = Order.objects.first()
        self.assertEqual(order.email, "buyer@example.com")
        self.assertEqual(order.user, self.user)
        self.assertEqual(OrderItem.objects.filter(order=order).count(), 1)

        success_response = self.client.get(reverse("order_success", kwargs={"order_id": order.id}))
        self.assertEqual(success_response.status_code, 200)
        self.assertContains(success_response, "Siparis")

    def test_checkout_prefills_from_default_address_and_can_save_address(self):
        CustomerAddress.objects.create(
            user=self.user,
            label="Ev",
            full_name="Saved Buyer",
            phone="5554443322",
            city="Istanbul",
            district="Kadikoy",
            postal_code="34000",
            address_line1="Saved line 1",
            address_line2="Saved line 2",
            country="Turkiye",
            is_default_shipping=True,
            is_default_billing=True,
        )
        self.client.login(username="store_admin", password="test1234")
        self.client.post(reverse("cart_add", kwargs={"variant_id": self.variant.id}), {"quantity": 1})

        checkout_get = self.client.get(reverse("checkout"))
        self.assertEqual(checkout_get.status_code, 200)
        self.assertContains(checkout_get, "Saved Buyer")

        checkout_post = self.client.post(
            reverse("checkout"),
            {
                "full_name": "New Buyer",
                "email": "buyer2@example.com",
                "phone": "1234567890",
                "address_line1": "New Address",
                "address_line2": "",
                "city": "Ankara",
                "district": "Cankaya",
                "state": "Ankara",
                "postal_code": "06000",
                "country": "Turkiye",
                "payment_method": "cod",
                "notes": "",
                "save_address": "on",
            },
        )
        self.assertEqual(checkout_post.status_code, 302)
        self.assertTrue(CustomerAddress.objects.filter(user=self.user, city="Ankara", district="Cankaya").exists())

# Create your tests here.
