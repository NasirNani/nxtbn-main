from django.test import TestCase
from django.urls import reverse

from nxtbn.order.models import Order
from nxtbn.payment.models import PaymentEvent, PaymentTransaction
from nxtbn.users.models import User


class PaytrCallbackTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="payer", email="payer@example.com", password="pass12345")
        self.order = Order.objects.create(
            user=self.user,
            full_name="Payer",
            email="payer@example.com",
            phone="555",
            address_line1="Addr",
            city="Izmir",
            state="Izmir",
            postal_code="35000",
            country="Turkiye",
            total="250.00",
        )
        self.transaction = PaymentTransaction.objects.create(
            order=self.order,
            amount="250.00",
            currency="TRY",
            provider="paytr",
            external_id="TEST-MERCHANT-OID",
        )

    def test_callback_success_and_idempotency(self):
        payload = {
            "merchant_oid": "TEST-MERCHANT-OID",
            "status": "success",
            "total_amount": "25000",
            "hash": "dev-no-signature",
        }
        url = reverse("paytr_callback")

        first = self.client.post(url, payload)
        self.assertEqual(first.status_code, 200)

        second = self.client.post(url, payload)
        self.assertEqual(second.status_code, 200)

        self.transaction.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.transaction.status, PaymentTransaction.STATUS_SUCCESS)
        self.assertEqual(self.order.status, Order.STATUS_PAID)
        self.assertEqual(PaymentEvent.objects.filter(transaction=self.transaction).count(), 1)
