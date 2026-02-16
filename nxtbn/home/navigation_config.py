from django.urls import reverse

from nxtbn.home.models import FooterSocialLink, SiteNavText


NAV_TEXT_DEFAULTS = [
    {
        "key": SiteNavText.KEY_SHOP_ALL,
        "label_tr": "Tum Urunler",
        "label_en": "Shop All",
        "sort_order": 10,
        "is_active": True,
    },
    {
        "key": SiteNavText.KEY_CONTACT,
        "label_tr": "Iletisim",
        "label_en": "Contact",
        "sort_order": 20,
        "is_active": True,
    },
    {
        "key": SiteNavText.KEY_ABOUT_US,
        "label_tr": "Hakkimizda",
        "label_en": "About Us",
        "sort_order": 30,
        "is_active": True,
    },
    {
        "key": SiteNavText.KEY_MORE_INFO,
        "label_tr": "Daha Fazla Bilgi",
        "label_en": "More Info",
        "sort_order": 40,
        "is_active": True,
    },
]


NAV_URL_MAP = {
    SiteNavText.KEY_SHOP_ALL: {"url_name": "products_list", "external": False},
    SiteNavText.KEY_CONTACT: {"url_name": "contact_page", "external": False},
    SiteNavText.KEY_ABOUT_US: {"url_name": "about_page", "external": False},
    SiteNavText.KEY_MORE_INFO: {"url": "https://flexymedical.com/", "external": True},
}


SOCIAL_ICON_MAP = {
    FooterSocialLink.PLATFORM_FACEBOOK: "facebook",
    FooterSocialLink.PLATFORM_INSTAGRAM: "photo_camera",
    FooterSocialLink.PLATFORM_YOUTUBE: "smart_display",
    FooterSocialLink.PLATFORM_LINKEDIN: "work",
    FooterSocialLink.PLATFORM_TIKTOK: "music_note",
}


def resolve_nav_url(nav_key):
    mapping = NAV_URL_MAP.get(nav_key)
    if not mapping:
        return "#", False
    if mapping.get("external"):
        return mapping["url"], True
    return reverse(mapping["url_name"]), False
