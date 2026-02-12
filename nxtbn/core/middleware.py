import re
from dataclasses import dataclass

from django.core.cache import cache
from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin


@dataclass(frozen=True)
class RateLimitRule:
    pattern: re.Pattern
    methods: tuple
    limit: int
    window_seconds: int


class SecurityHeadersMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        response.setdefault("X-Content-Type-Options", "nosniff")
        response.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        return response


class RateLimitMiddleware(MiddlewareMixin):
    RULES = (
        RateLimitRule(
            pattern=re.compile(r"^/accounts/login/?$"),
            methods=("POST",),
            limit=10,
            window_seconds=300,
        ),
        RateLimitRule(
            pattern=re.compile(r"^/admin/login/?$"),
            methods=("POST",),
            limit=10,
            window_seconds=300,
        ),
        RateLimitRule(
            pattern=re.compile(r"^/products/[0-9a-fA-F-]+/?$"),
            methods=("POST",),
            limit=20,
            window_seconds=300,
        ),
        RateLimitRule(
            pattern=re.compile(r"^/storefront/v1/api/products/[0-9a-fA-F-]+/reviews/?$"),
            methods=("POST",),
            limit=20,
            window_seconds=300,
        ),
        RateLimitRule(
            pattern=re.compile(r"^/accounts/addresses/add/?$"),
            methods=("POST",),
            limit=15,
            window_seconds=300,
        ),
        RateLimitRule(
            pattern=re.compile(r"^/accounts/addresses/[0-9a-fA-F-]+/edit/?$"),
            methods=("POST",),
            limit=20,
            window_seconds=300,
        ),
        RateLimitRule(
            pattern=re.compile(r"^/accounts/addresses/[0-9a-fA-F-]+/delete/?$"),
            methods=("POST",),
            limit=20,
            window_seconds=300,
        ),
        RateLimitRule(
            pattern=re.compile(r"^/accounts/reviews/?$"),
            methods=("POST",),
            limit=30,
            window_seconds=300,
        ),
        RateLimitRule(
            pattern=re.compile(r"^/storefront/v1/api/account/addresses/?$"),
            methods=("POST",),
            limit=30,
            window_seconds=300,
        ),
        RateLimitRule(
            pattern=re.compile(r"^/storefront/v1/api/account/addresses/[0-9a-fA-F-]+/?$"),
            methods=("PATCH", "DELETE"),
            limit=40,
            window_seconds=300,
        ),
    )

    def _client_ip(self, request):
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "unknown")

    def process_request(self, request):
        path = request.path
        method = request.method.upper()
        ip = self._client_ip(request)

        for rule in self.RULES:
            if method not in rule.methods:
                continue
            if not rule.pattern.match(path):
                continue

            key = f"ratelimit:{rule.pattern.pattern}:{ip}"
            current = cache.get(key, 0)
            if current >= rule.limit:
                response = HttpResponse("Too many requests. Please try again later.", status=429)
                response["Retry-After"] = str(rule.window_seconds)
                return response

            if current == 0:
                cache.set(key, 1, timeout=rule.window_seconds)
            else:
                cache.incr(key)
            return None

        return None
