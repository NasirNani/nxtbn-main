from django.db import DatabaseError
from django.utils.translation import get_language

from nxtbn.home.models import FooterSocialLink, SiteNavText
from nxtbn.home.navigation_config import NAV_TEXT_DEFAULTS, SOCIAL_ICON_MAP, resolve_nav_url


def _is_turkish_language():
    return (get_language() or "").lower().startswith("tr")


def storefront_navigation_content(request):
    is_turkish = _is_turkish_language()
    try:
        db_rows_by_key = {row.key: row for row in SiteNavText.objects.all()}
        social_rows = FooterSocialLink.objects.filter(is_active=True).order_by("sort_order", "id")
    except DatabaseError:
        db_rows_by_key = {}
        social_rows = []

    managed_nav_items = []
    for default in NAV_TEXT_DEFAULTS:
        row = db_rows_by_key.get(default["key"])
        if row:
            if not row.is_active:
                continue
            label = row.label_tr if is_turkish else row.label_en
            sort_order = row.sort_order
        else:
            if not default.get("is_active", True):
                continue
            label = default["label_tr"] if is_turkish else default["label_en"]
            sort_order = default["sort_order"]

        url, is_external = resolve_nav_url(default["key"])
        managed_nav_items.append(
            {
                "key": default["key"],
                "label": label,
                "url": url,
                "is_external": is_external,
                "sort_order": sort_order,
            }
        )

    managed_nav_items = sorted(managed_nav_items, key=lambda item: (item["sort_order"], item["key"]))

    managed_social_links = []
    for item in social_rows:
        managed_social_links.append(
            {
                "platform": item.platform,
                "platform_display": item.get_platform_display(),
                "label": item.label or item.get_platform_display(),
                "url": item.url,
                "icon": SOCIAL_ICON_MAP.get(item.platform),
            }
        )

    return {
        "managed_nav_items": managed_nav_items,
        "managed_social_links": managed_social_links,
    }
