from django.test import TestCase, override_settings
from django.urls import reverse

from nxtbn.users.models import User


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
class AdminFormUxBaselineTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="admin_form_ux",
            email="admin_form_ux@example.com",
            password="pass12345",
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_login(self.staff)

    def test_all_listed_add_forms_render_ops_shell(self):
        route_names = [
            "admin:account_emailaddress_add",
            "admin:auth_group_add",
            "admin:authtoken_tokenproxy_add",
            "admin:discount_coupon_add",
            "admin:filemanager_document_add",
            "admin:filemanager_image_add",
            "admin:gift_card_giftcard_add",
            "admin:gift_card_giftcardtransaction_add",
            "admin:home_homeslide_add",
            "admin:invoice_invoice_add",
            "admin:order_order_add",
            "admin:payment_paymentmethodconfig_add",
            "admin:payment_paymenttransaction_add",
            "admin:payment_paymentevent_add",
            "admin:product_category_add",
            "admin:product_product_add",
            "admin:product_productreview_add",
            "admin:product_productvariant_add",
            "admin:sites_site_add",
            "admin:tax_taxrule_add",
            "admin:users_user_add",
            "admin:users_customeraddress_add",
            "admin:vendor_vendor_add",
        ]
        for route_name in route_names:
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "ops-form-shell")
                self.assertContains(response, "ops-form-card")

    def test_popup_forms_render_compact_class(self):
        popup_routes = [
            "admin:account_emailaddress_add",
            "admin:auth_group_add",
            "admin:filemanager_document_add",
            "admin:product_category_add",
            "admin:vendor_vendor_add",
        ]
        for route_name in popup_routes:
            with self.subTest(route_name=route_name):
                url = f"{reverse(route_name)}?_popup=1&_to_field=id"
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "ops-form-shell--popup")
