from django.test import TestCase
from django.urls import reverse

from nxtbn.order.models import Order
from nxtbn.users.models import CustomerAddress, User


class CustomerPanelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="paneluser", email="panel@example.com", password="pass12345")
        self.other = User.objects.create_user(username="otheruser", email="other@example.com", password="pass12345")
        self.address = CustomerAddress.objects.create(
            user=self.user,
            label="Ev",
            full_name="Panel User",
            phone="5551112233",
            city="Istanbul",
            district="Kadikoy",
            postal_code="34000",
            address_line1="Adres 1",
            country="Turkiye",
            is_default_shipping=True,
            is_default_billing=True,
        )
        Order.objects.create(
            user=self.user,
            full_name="Panel User",
            email=self.user.email,
            phone="5551112233",
            address_line1="Adres 1",
            city="Istanbul",
            state="Kadikoy",
            postal_code="34000",
            country="Turkiye",
            total="120.00",
        )
        Order.objects.create(
            user=self.other,
            full_name="Other User",
            email=self.other.email,
            phone="5550001122",
            address_line1="Adres 2",
            city="Ankara",
            state="Cankaya",
            postal_code="06000",
            country="Turkiye",
            total="99.00",
        )

    def test_account_pages_require_login(self):
        response = self.client.get(reverse("account_dashboard"))
        self.assertEqual(response.status_code, 302)

        response = self.client.get(reverse("account_addresses"))
        self.assertEqual(response.status_code, 302)

    def test_add_address(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("account_address_add"),
            data={
                "label": "Ofis",
                "full_name": "Panel User",
                "phone": "5559998877",
                "city": "Istanbul",
                "district": "Besiktas",
                "postal_code": "34353",
                "address_line1": "Ofis Adresi",
                "address_line2": "",
                "country": "Turkiye",
                "is_default_shipping": False,
                "is_default_billing": False,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(CustomerAddress.objects.filter(user=self.user, is_active=True).count(), 2)

    def test_owner_cannot_edit_other_user_address(self):
        foreign = CustomerAddress.objects.create(
            user=self.other,
            label="Other",
            full_name="Other User",
            phone="5551110000",
            city="Ankara",
            district="Cankaya",
            postal_code="06000",
            address_line1="Other Address",
            country="Turkiye",
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse("account_address_edit", kwargs={"address_id": foreign.id}))
        self.assertEqual(response.status_code, 404)

    def test_orders_page_only_contains_owner_orders(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("account_orders"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].paginator.count, 1)

    def test_reviews_page_renders(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("account_reviews"))
        self.assertEqual(response.status_code, 200)
