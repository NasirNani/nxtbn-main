from django import forms
from django.utils.translation import gettext_lazy as _

from allauth.account.forms import SignupForm
from allauth.utils import set_form_field_order

from nxtbn.users.models import CustomerAddress


class AllauthSignupForm(SignupForm):
    field_order = [
        "email",
        "first_name",
        "last_name",
        "password1",
        "password2",
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"] = forms.CharField(
            label=_("First Name"),
            max_length=255,
            widget=forms.TextInput(attrs={"placeholder": _("First Name"), "autocomplete": "given-name"}),
        )
        self.fields["last_name"] = forms.CharField(
            label=_("Last Name"),
            max_length=255,
            widget=forms.TextInput(attrs={"placeholder": _("Last Name"), "autocomplete": "family-name"}),
        )

        if hasattr(self, "field_order"):
            set_form_field_order(self, self.field_order)


class CustomerProfileForm(forms.Form):
    username = forms.CharField(label=_("Username"), disabled=True, required=False)
    email = forms.EmailField(label=_("Email"), disabled=True, required=False)
    first_name = forms.CharField(label=_("First Name"), max_length=150, required=False)
    last_name = forms.CharField(label=_("Last Name"), max_length=150, required=False)

    def save(self, user):
        user.first_name = self.cleaned_data.get("first_name", "").strip()
        user.last_name = self.cleaned_data.get("last_name", "").strip()
        user.save(update_fields=["first_name", "last_name"])
        return user

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base_input = "mt-1 block w-full rounded-lg border-gray-300 dark:border-gray-700 dark:bg-gray-900"
        for field in self.fields.values():
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing} {base_input}".strip()


class CustomerAddressForm(forms.ModelForm):
    class Meta:
        model = CustomerAddress
        fields = [
            "label",
            "full_name",
            "phone",
            "city",
            "district",
            "postal_code",
            "address_line1",
            "address_line2",
            "country",
            "is_default_shipping",
            "is_default_billing",
        ]
        widgets = {
            "address_line2": forms.TextInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base_input = "mt-1 block w-full rounded-lg border-gray-300 dark:border-gray-700 dark:bg-gray-900"
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
            else:
                existing = field.widget.attrs.get("class", "")
                field.widget.attrs["class"] = f"{existing} {base_input}".strip()

    def clean_phone(self):
        phone = (self.cleaned_data.get("phone") or "").strip()
        if not phone:
            return ""
        sanitized = "".join(ch for ch in phone if ch.isdigit() or ch == "+")
        if len(sanitized.replace("+", "")) < 10:
            raise forms.ValidationError(_("Telefon numarasi en az 10 haneli olmali."))
        return sanitized

    def clean_postal_code(self):
        postal_code = (self.cleaned_data.get("postal_code") or "").strip()
        if postal_code and not postal_code.replace("-", "").isalnum():
            raise forms.ValidationError(_("Posta kodu gecersiz."))
        return postal_code
