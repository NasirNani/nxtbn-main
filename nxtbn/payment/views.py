import base64
import hashlib
import hmac
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from nxtbn.order.models import Order

from .models import PaymentEvent, PaymentMethodConfig, PaymentTransaction


def _config_value(config, key):
    if not config:
        return ""
    return (getattr(config, key, "") or "").strip()


def _paytr_signature_valid(payload, merchant_key, merchant_salt):
    merchant_oid = payload.get("merchant_oid", "")
    status = payload.get("status", "")
    total_amount = payload.get("total_amount", "")
    posted_hash = payload.get("hash", "")
    hash_input = f"{merchant_oid}{merchant_salt}{status}{total_amount}"
    digest = hmac.new(merchant_key.encode("utf-8"), hash_input.encode("utf-8"), hashlib.sha256).digest()
    generated_hash = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(generated_hash, posted_hash)


def _ensure_owner_or_staff(request, transaction_id):
    transaction = get_object_or_404(
        PaymentTransaction.objects.select_related("order", "order__user").prefetch_related("order__items"),
        id=transaction_id,
    )
    if request.user.is_staff or transaction.order.user_id == request.user.id:
        return transaction
    return None


@login_required
def payment_start(request, transaction_id):
    transaction = _ensure_owner_or_staff(request, transaction_id)
    if transaction is None:
        return redirect("home")

    if transaction.status == PaymentTransaction.STATUS_SUCCESS:
        return redirect("order_success", order_id=transaction.order_id)

    config = PaymentMethodConfig.objects.filter(provider=PaymentMethodConfig.PROVIDER_PAYTR, is_active=True).first()
    merchant_id = _config_value(config, "merchant_id") or os.getenv("PAYTR_MERCHANT_ID", "")
    merchant_key = _config_value(config, "secret_key") or os.getenv("PAYTR_MERCHANT_KEY", "")
    merchant_salt = (config.extra_config.get("merchant_salt", "") if config else "") or os.getenv("PAYTR_MERCHANT_SALT", "")

    payment_url = ""
    if merchant_id and merchant_key and merchant_salt:
        merchant_oid = str(transaction.id)
        transaction.external_id = merchant_oid
        transaction.save(update_fields=["external_id"])

        user_basket = [
            [item.product_name, str(item.unit_price), int(item.quantity)]
            for item in transaction.order.items.all()
        ]
        user_ip = request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", "127.0.0.1")).split(",")[0]
        payment_amount = int((Decimal(transaction.amount) * 100).quantize(Decimal("1")))

        hash_str = (
            f"{merchant_id}{user_ip}{merchant_oid}{transaction.order.email}"
            f"{payment_amount}{base64.b64encode(json.dumps(user_basket).encode('utf-8')).decode('utf-8')}"
            f"0{0}TRY{1}"
        )
        paytr_token = base64.b64encode(
            hmac.new(
                merchant_key.encode("utf-8"),
                f"{hash_str}{merchant_salt}".encode("utf-8"),
                hashlib.sha256,
            ).digest()
        ).decode("utf-8")

        payload = {
            "merchant_id": merchant_id,
            "user_ip": user_ip,
            "merchant_oid": merchant_oid,
            "email": transaction.order.email,
            "payment_amount": payment_amount,
            "paytr_token": paytr_token,
            "user_basket": base64.b64encode(json.dumps(user_basket).encode("utf-8")).decode("utf-8"),
            "debug_on": 1,
            "no_installment": 0,
            "max_installment": 0,
            "user_name": transaction.order.full_name,
            "user_address": transaction.order.address_line1,
            "user_phone": transaction.order.phone or "0000000000",
            "merchant_ok_url": request.build_absolute_uri(reverse("order_success", args=[transaction.order_id])),
            "merchant_fail_url": request.build_absolute_uri(reverse("payment_failed", args=[transaction.id])),
            "timeout_limit": 30,
            "currency": "TRY",
            "test_mode": 1,
            "lang": "tr",
        }
        try:
            encoded_payload = urllib.parse.urlencode(payload).encode("utf-8")
            request_obj = urllib.request.Request("https://www.paytr.com/odeme/api/get-token", data=encoded_payload)
            with urllib.request.urlopen(request_obj, timeout=10) as response:
                parsed = json.loads(response.read().decode("utf-8"))
            if parsed.get("status") == "success":
                token = parsed.get("token", "")
                payment_url = f"https://www.paytr.com/odeme/guvenli/{token}"
                transaction.token = token
                transaction.save(update_fields=["token"])
                PaymentEvent.objects.create(
                    transaction=transaction,
                    event_type=PaymentEvent.EVENT_REQUEST,
                    idempotency_key=f"request-{transaction.id}",
                    raw_payload={"provider": "paytr", "response": parsed},
                    signature_valid=True,
                    processed=True,
                )
            else:
                messages.warning(request, "PayTR token alinamadi. Gelistirme modunda test ekranina gecildi.")
        except (urllib.error.URLError, ValueError, json.JSONDecodeError):
            messages.warning(request, "PayTR ulasilamadi. Gelistirme modunda test ekranina gecildi.")

    return render(
        request,
        "store/payment_start.html",
        {"transaction": transaction, "payment_url": payment_url},
    )


@login_required
@require_POST
def payment_simulate(request, transaction_id):
    transaction = _ensure_owner_or_staff(request, transaction_id)
    if transaction is None:
        return redirect("home")

    outcome = request.POST.get("outcome", "fail")
    order = transaction.order
    if outcome == "success":
        transaction.status = PaymentTransaction.STATUS_SUCCESS
        transaction.is_processed = True
        transaction.processed_at = timezone.now()
        transaction.save(update_fields=["status", "is_processed", "processed_at"])

        order.status = Order.STATUS_PAID
        order.payment_reference = str(transaction.id)
        order.save(update_fields=["status", "payment_reference"])
        order.status_events.create(status=Order.STATUS_PAID, note="Payment approved (simulate)", changed_by=request.user)
        messages.success(request, "Odeme basarili.")
        return redirect("order_success", order_id=order.id)

    transaction.status = PaymentTransaction.STATUS_FAILED
    transaction.error_message = "Simulated payment failure"
    transaction.save(update_fields=["status", "error_message"])
    messages.error(request, "Odeme basarisiz.")
    return redirect("payment_failed", transaction_id=transaction.id)


@csrf_exempt
@require_POST
def paytr_callback(request):
    merchant_oid = request.POST.get("merchant_oid", "").strip()
    status = request.POST.get("status", "").strip()
    total_amount = request.POST.get("total_amount", "").strip()
    if not merchant_oid or not status:
        return HttpResponseBadRequest("invalid payload")

    transaction = PaymentTransaction.objects.filter(external_id=merchant_oid).select_related("order").first()
    if transaction is None:
        transaction = PaymentTransaction.objects.filter(id=merchant_oid).select_related("order").first()
    if transaction is None:
        return HttpResponseBadRequest("transaction not found")

    idempotency_key = f"{merchant_oid}:{status}:{total_amount}"
    event, created = PaymentEvent.objects.get_or_create(
        transaction=transaction,
        event_type=PaymentEvent.EVENT_CALLBACK,
        idempotency_key=idempotency_key,
        defaults={"raw_payload": dict(request.POST.items())},
    )
    if not created and event.processed:
        return HttpResponse("OK")

    config = PaymentMethodConfig.objects.filter(provider=PaymentMethodConfig.PROVIDER_PAYTR, is_active=True).first()
    merchant_key = _config_value(config, "secret_key") or os.getenv("PAYTR_MERCHANT_KEY", "")
    merchant_salt = (config.extra_config.get("merchant_salt", "") if config else "") or os.getenv("PAYTR_MERCHANT_SALT", "")
    signature_valid = True
    if merchant_key and merchant_salt:
        signature_valid = _paytr_signature_valid(request.POST, merchant_key, merchant_salt)

    event.raw_payload = dict(request.POST.items())
    event.signature_valid = signature_valid
    event.processed = True
    event.save(update_fields=["raw_payload", "signature_valid", "processed"])

    if signature_valid and status == "success":
        transaction.status = PaymentTransaction.STATUS_SUCCESS
        transaction.is_processed = True
        transaction.processed_at = timezone.now()
        transaction.save(update_fields=["status", "is_processed", "processed_at"])

        order = transaction.order
        order.status = Order.STATUS_PAID
        order.payment_reference = merchant_oid
        order.save(update_fields=["status", "payment_reference"])
        order.status_events.create(status=Order.STATUS_PAID, note="PayTR callback success")
    else:
        transaction.status = PaymentTransaction.STATUS_FAILED
        transaction.error_message = request.POST.get("failed_reason_msg", "Payment failed")
        transaction.save(update_fields=["status", "error_message"])

    return HttpResponse("OK")


@login_required
def payment_failed(request, transaction_id):
    transaction = _ensure_owner_or_staff(request, transaction_id)
    if transaction is None:
        return redirect("home")
    return render(request, "store/payment_failed.html", {"transaction": transaction})

# Create your views here.
