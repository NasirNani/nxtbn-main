from django.test import TestCase
from django.urls import reverse

from nxtbn.order.models import Order
from nxtbn.users.models import User


class OrderAccessTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", email="owner@example.com", password="pass12345")
        self.other = User.objects.create_user(username="other", email="other@example.com", password="pass12345")
        self.order = Order.objects.create(
            user=self.owner,
            full_name="Owner Name",
            email="owner@example.com",
            phone="123",
            address_line1="Address 1",
            city="Istanbul",
            state="Istanbul",
            postal_code="34000",
            country="Turkiye",
            total="100.00",
        )

    def test_owner_can_view_order_detail(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("order_detail", kwargs={"order_id": self.order.id}))
        self.assertEqual(response.status_code, 200)

    def test_other_user_cannot_view_order_detail(self):
        self.client.force_login(self.other)
        response = self.client.get(reverse("order_detail", kwargs={"order_id": self.order.id}))
        self.assertEqual(response.status_code, 404)
