from django.core.management.base import BaseCommand
from nxtbn.order.models import Order
from nxtbn.users.models import CustomerAddress, User


class Command(BaseCommand):
    help = "Backfill default customer addresses from each user's latest order if address book is empty."

    def handle(self, *args, **options):
        users = User.objects.all()
        created = 0
        skipped = 0

        for user in users:
            if CustomerAddress.objects.filter(user=user, is_active=True).exists():
                skipped += 1
                continue

            latest_order = (
                Order.objects.filter(user=user)
                .order_by("-created_at")
                .first()
            )
            if latest_order is None:
                skipped += 1
                continue

            CustomerAddress.objects.create(
                user=user,
                label="Backfill",
                full_name=latest_order.full_name or user.get_full_name() or user.username,
                phone=latest_order.phone or "",
                city=latest_order.city or "",
                district=latest_order.state or "",
                postal_code=latest_order.postal_code or "",
                address_line1=latest_order.address_line1 or "",
                address_line2=latest_order.address_line2 or "",
                country=latest_order.country or "Turkiye",
                is_default_shipping=True,
                is_default_billing=True,
            )
            created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Backfill completed. Created={created}, skipped={skipped}."
            )
        )
