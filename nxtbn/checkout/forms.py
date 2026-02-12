from django import forms
from django.utils.translation import gettext_lazy as _


class CheckoutForm(forms.Form):
    address_id = forms.UUIDField(required=False, widget=forms.HiddenInput())
    use_saved_address = forms.BooleanField(required=False, initial=False)
    save_address = forms.BooleanField(required=False, initial=False)
    full_name = forms.CharField(max_length=120, label=_("Ad Soyad"))
    email = forms.EmailField()
    phone = forms.CharField(max_length=30, required=False, label=_("Telefon"))
    address_line1 = forms.CharField(max_length=180, label=_("Adres"))
    address_line2 = forms.CharField(max_length=180, required=False, label=_("Adres (2)"))
    city = forms.CharField(max_length=100, label=_("Sehir"))
    district = forms.CharField(max_length=100, label=_("Ilce"))
    state = forms.CharField(max_length=100, label=_("Il / Eyalet"))
    postal_code = forms.CharField(max_length=20, label=_("Posta Kodu"))
    country = forms.CharField(max_length=100, initial="Turkiye", label=_("Ulke"))
    payment_method = forms.ChoiceField(
        choices=[
            ("paytr", "PayTR"),
            ("cod", "Kapida Odeme"),
            ("bank", "Bank Transfer"),
        ]
    )
    notes = forms.CharField(widget=forms.Textarea, required=False, label=_("Notlar"))

    def clean_phone(self):
        phone = (self.cleaned_data.get("phone") or "").strip()
        if not phone:
            return ""
        digits = "".join(ch for ch in phone if ch.isdigit() or ch == "+")
        if len(digits.replace("+", "")) < 10:
            raise forms.ValidationError(_("Telefon numarasi en az 10 hane olmali."))
        return digits

    def clean_postal_code(self):
        postal_code = (self.cleaned_data.get("postal_code") or "").strip()
        if postal_code and not postal_code.replace("-", "").isalnum():
            raise forms.ValidationError(_("Posta kodu gecersiz."))
        return postal_code
