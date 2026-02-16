import csv
import uuid

from django.contrib import admin, messages
from django.db import models
from django.db.models import Q
from django.http import HttpResponse


class OpsAdminMixin:
    """Shared admin defaults for faster list pages and safer forms."""

    list_per_page = 50
    save_on_top = True
    audit_readonly_candidates = ("created_at", "last_modified", "last_modified_by", "created_by")
    tr_field_labels = {
        "name": "Ad",
        "code": "Kod",
        "summary": "Ozet",
        "description": "Aciklama",
        "slug": "Slug",
        "title": "Baslik",
        "subtitle": "Alt Baslik",
        "label": "Etiket",
        "comment": "Yorum",
        "notes": "Notlar",
        "note": "Not",
        "full_name": "Ad Soyad",
        "email": "E-posta",
        "phone": "Telefon",
        "user": "Kullanici",
        "avatar": "Profil Gorseli",
        "city": "Sehir",
        "district": "Ilce",
        "state": "Bolge",
        "country": "Ulke",
        "postal_code": "Posta Kodu",
        "address_line1": "Adres Satiri 1",
        "address_line2": "Adres Satiri 2",
        "image": "Gorsel",
        "image_alt_text": "Gorsel Aciklamasi",
        "document": "Dokuman",
        "vendor": "Tedarikci",
        "contact_info": "Iletisim Bilgisi",
        "brand": "Marka",
        "category": "Kategori",
        "category_ref": "Kategori",
        "default_variant": "Varsayilan Varyant",
        "subscribable": "Abonelige Uygun",
        "published_date": "Yayin Tarihi",
        "discount_type": "Indirim Turu",
        "discount_value": "Indirim Degeri",
        "min_subtotal": "Minimum Ara Toplam",
        "max_discount": "Maksimum Indirim",
        "usage_limit": "Kullanim Limiti",
        "used_count": "Kullanim Sayisi",
        "starts_at": "Baslangic Tarihi",
        "ends_at": "Bitis Tarihi",
        "is_active": "Aktif",
        "is_live": "Yayinda",
        "is_processed": "Islendi",
        "is_default_shipping": "Varsayilan Teslimat",
        "is_default_billing": "Varsayilan Fatura",
        "sort_order": "Siralama",
        "status": "Durum",
        "transaction_type": "Islem Turu",
        "event_type": "Olay Turu",
        "provider": "Saglayici",
        "currency": "Para Birimi",
        "balance": "Bakiye",
        "amount": "Tutar",
        "price": "Fiyat",
        "compare_at_price": "Liste Fiyati",
        "cost_per_unit": "Birim Maliyet",
        "stock": "Stok",
        "track_inventory": "Stok Takibi",
        "low_stock_threshold": "Dusuk Stok Esigi",
        "stock_status": "Stok Durumu",
        "sku": "SKU",
        "weight_unit": "Agirlik Birimi",
        "weight_value": "Agirlik",
        "order": "Siparis",
        "number": "Numara",
        "issued_at": "Duzenlenme Tarihi",
        "paid_at": "Odeme Tarihi",
        "payment_method": "Odeme Yontemi",
        "payment_reference": "Odeme Referansi",
        "coupon_code": "Kupon Kodu",
        "gift_card_code": "Hediye Karti Kodu",
        "cancellation_requested": "Iptal Talebi",
        "cancellation_reason": "Iptal Nedeni",
        "shipped_at": "Kargolama Tarihi",
        "delivered_at": "Teslim Tarihi",
        "tracking_number": "Takip Numarasi",
        "tracking_url": "Takip Baglantisi",
        "subtotal": "Ara Toplam",
        "discount": "Indirim",
        "tax": "Vergi",
        "shipping": "Kargo",
        "total": "Toplam",
        "external_id": "Harici Kimlik",
        "token": "Token",
        "error_message": "Hata Mesaji",
        "public_key": "Acik Anahtar",
        "secret_key": "Gizli Anahtar",
        "merchant_id": "Satici Kimligi",
        "extra_config": "Ek Ayarlar",
        "idempotency_key": "Idempotency Anahtari",
        "raw_payload": "Ham Veri",
        "signature_valid": "Imza Gecerli",
        "processed": "Islendi",
        "rating": "Puan",
        "report_count": "Sikayet Sayisi",
    }

    def get_ordering(self, request):
        if self.ordering:
            return self.ordering
        field_names = {field.name for field in self.model._meta.fields}
        if "created_at" in field_names:
            return ("-created_at",)
        return (self.model._meta.pk.name,)

    def get_readonly_fields(self, request, obj=None):
        existing = {field.name for field in self.model._meta.fields}
        readonly = set(super().get_readonly_fields(request, obj))
        readonly.update(name for name in self.audit_readonly_candidates if name in existing)
        return tuple(sorted(readonly))

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)

        term = (search_term or "").strip()
        if not term:
            return queryset, use_distinct

        extra_queryset = self.model.objects.none()
        pk_field = self.model._meta.pk
        pk_name = pk_field.name

        if isinstance(pk_field, models.UUIDField):
            try:
                uuid.UUID(term)
            except ValueError:
                pass
            else:
                extra_queryset = extra_queryset | self.model.objects.filter(**{pk_name: term})
        elif term.isdigit():
            extra_queryset = extra_queryset | self.model.objects.filter(**{pk_name: term})

        email_fields = [field.name for field in self.model._meta.fields if isinstance(field, models.EmailField)]
        if "@" in term and email_fields:
            email_query = Q()
            for field_name in email_fields:
                email_query |= Q(**{f"{field_name}__iexact": term})
            extra_queryset = extra_queryset | self.model.objects.filter(email_query)

        if extra_queryset.exists():
            queryset = (queryset | extra_queryset).distinct()
            use_distinct = True

        return queryset, use_distinct

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if not formfield:
            return formfield

        language_code = (getattr(request, "LANGUAGE_CODE", "") or "").lower()
        if not language_code.startswith("tr"):
            return formfield

        translated_label = self.tr_field_labels.get(db_field.name)
        if translated_label:
            formfield.label = translated_label
        return formfield


class AutoUserStampMixin:
    """Auto-fill created_by / last_modified_by fields if present on model."""

    def save_model(self, request, obj, form, change):
        if hasattr(obj, "created_by") and (not change or getattr(obj, "created_by_id", None) is None):
            obj.created_by = request.user
        if hasattr(obj, "last_modified_by"):
            obj.last_modified_by = request.user
        super().save_model(request, obj, form, change)


def export_queryset_as_csv(filename, headers, rows):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    return response


def status_update_action(description, target_status, *, allowed_from=None, status_field="status"):
    @admin.action(description=description)
    def _action(modeladmin, request, queryset):
        if allowed_from:
            queryset = queryset.filter(**{f"{status_field}__in": tuple(allowed_from)})
        updated = queryset.update(**{status_field: target_status})
        level = messages.SUCCESS if updated else messages.WARNING
        modeladmin.message_user(request, f"{updated} kayit guncellendi.", level=level)

    return _action
