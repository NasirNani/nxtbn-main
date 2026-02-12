# Release Runbook

## 1. Pre-release checks
1. Ensure `.env` is set from `env.example` with production-safe values.
2. Set `DEBUG=False`, `SECURE_SSL_REDIRECT=True`, valid `ALLOWED_HOSTS`, and HTTPS `CSRF_TRUSTED_ORIGINS`.
3. Configure real PayTR credentials:
   - `PAYTR_MERCHANT_ID`
   - `PAYTR_MERCHANT_KEY`
   - `PAYTR_MERCHANT_SALT`
4. Run:
   ```bash
   python manage.py check
   python manage.py makemigrations --check
   python manage.py test
   ```

## 2. Deployment steps
1. Pull latest code.
2. Install dependencies.
3. Apply migrations:
   ```bash
   python manage.py migrate
   ```
4. Collect static files:
   ```bash
   python manage.py collectstatic --noinput
   ```
5. Restart application service/process manager.

## 3. Post-deploy smoke tests
1. Verify health and storefront:
   - `/`
   - `/products/`
   - `/cart/`
   - `/checkout/` (authenticated with non-empty cart)
2. Verify admin:
   - `/admin/`
   - `/admin/operations/analytics/`
3. Verify payment flow:
   - Start payment from checkout
   - Confirm callback endpoint receives and processes updates
4. Verify security headers in browser/network tools:
   - `X-Content-Type-Options`
   - `Referrer-Policy`
   - `Permissions-Policy`

## 4. Operational workflows
1. Product import/export:
   - Admin Product changelist -> `Import CSV` / `Export All CSV`
2. Order export:
   - Admin Order changelist -> `Export All CSV`
3. Review moderation:
   - Admin ProductReview actions (`Mark approved`, `Mark hidden`)
4. Low stock + queue monitoring:
   - `/admin/operations/analytics/`

## 5. Rollback strategy
1. Revert to previous application image/build.
2. Restore database backup if schema/data rollback is required.
3. Re-run smoke tests.

## 6. Incident notes
1. Payment callback is idempotent via `PaymentEvent.idempotency_key`.
2. Login and review submissions are rate-limited by middleware.
3. Use server logs (standard formatter in `LOGGING`) for request and error tracing.
