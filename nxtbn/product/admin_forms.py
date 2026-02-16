import re
from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import get_language, gettext_lazy as _

from nxtbn.product.models import Category
from nxtbn.vendor.models import Vendor


def _normalize_text(value):
    return re.sub(r"\s+", " ", (value or "").strip())


class QuickProductCreateForm(forms.Form):
    name = forms.CharField(
        label=_("Product Name"),
        max_length=255,
        help_text=_("Visible product name for customers."),
    )
    vendor = forms.ModelChoiceField(
        label=_("Vendor"),
        queryset=Vendor.objects.all().order_by("name"),
        required=False,
        help_text=_("Select an existing vendor."),
    )
    new_vendor_name = forms.CharField(
        label=_("New Vendor Name"),
        max_length=100,
        required=False,
        help_text=_("Creates a new vendor if no vendor is selected."),
    )
    category_ref = forms.ModelChoiceField(
        label=_("Category"),
        queryset=Category.objects.filter(is_active=True).order_by("sort_order", "name"),
        required=True,
    )
    price = forms.DecimalField(
        label=_("Price"),
        min_value=Decimal("0.01"),
        max_digits=12,
        decimal_places=3,
        help_text=_("Saved in TRY currency."),
    )
    stock = forms.IntegerField(
        label=_("Stock"),
        required=False,
        min_value=0,
        initial=0,
        help_text=_("If empty, defaults to 0."),
    )
    image = forms.ImageField(
        label=_("Product Image"),
        required=False,
        help_text=_("Optional. Selected image is attached to the default variant."),
    )

    def __init__(self, *args, can_create_vendor=False, **kwargs):
        self.can_create_vendor = can_create_vendor
        super().__init__(*args, **kwargs)
        language = (get_language() or "").lower()
        is_turkish = language.startswith("tr")
        if is_turkish:
            localized = {
                "name": ("Urun Adi", "Musterinin gorecegi urun adi."),
                "vendor": ("Tedarikci", "Mevcut bir tedarikci secin."),
                "new_vendor_name": ("Yeni Tedarikci Adi", "Secili tedarikci yoksa hizlica yeni tedarikci olusturur."),
                "category_ref": ("Kategori", None),
                "price": ("Fiyat", "TRY para birimi ile kaydedilir."),
                "stock": ("Stok", "Bos birakilirsa 0 kabul edilir."),
                "image": ("Urun Gorseli", "Istege bagli. Secilen gorsel varsayilan varyanta eklenir."),
            }
            for field_name, (label, help_text) in localized.items():
                if field_name in self.fields:
                    self.fields[field_name].label = label
                    if help_text is not None:
                        self.fields[field_name].help_text = help_text
        if not self.can_create_vendor:
            self.fields.pop("new_vendor_name", None)

    def _resolve_vendor(self):
        vendor = self.cleaned_data.get("vendor")
        if vendor:
            return vendor

        is_turkish = (get_language() or "").lower().startswith("tr")
        if not self.can_create_vendor:
            raise ValidationError(_("Tedarikci secimi zorunludur.") if is_turkish else _("Vendor selection is required."))

        new_name = _normalize_text(self.cleaned_data.get("new_vendor_name"))
        if not new_name:
            raise ValidationError(
                _("Tedarikci secin veya yeni tedarikci adi girin.")
                if is_turkish
                else _("Select a vendor or enter a new vendor name.")
            )

        existing_vendor = Vendor.objects.filter(name__iexact=new_name).order_by("name").first()
        if existing_vendor:
            return existing_vendor
        return Vendor.objects.create(name=new_name)

    def clean_stock(self):
        stock = self.cleaned_data.get("stock")
        return stock if stock is not None else 0

    def clean(self):
        cleaned = super().clean()
        if self.errors:
            return cleaned

        cleaned["resolved_vendor"] = self._resolve_vendor()
        return cleaned
