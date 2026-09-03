# Development services

Install the project dependencies, then start Redis, Django, and Celery in three terminals:

```powershell
redis-server
python manage.py runserver
celery -A config worker --loglevel=info --pool=solo
```

`--pool=solo` is the reliable Celery worker mode on Windows. For Docker/Linux, omit it. Redis must be available at `CELERY_BROKER_URL` (default: `redis://localhost:6379/0`).

Add these secrets to `.env`: `AFRICASTALKING_USERNAME`, `AFRICASTALKING_API_KEY`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, and the relevant OAuth client credentials: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `FACEBOOK_CLIENT_ID`, `FACEBOOK_CLIENT_SECRET`, `APPLE_SERVICE_ID`, `APPLE_KEY_ID`, `APPLE_TEAM_ID`, `APPLE_PRIVATE_KEY`.

For M-PESA, set `MPESA_CALLBACK_URL` to a public HTTPS URL ending in `/payments/callback/`; the application appends the callback token securely. Use `MPESA_TRANSACTION_TYPE=CustomerPayBillOnline` for a PayBill shortcode, or `CustomerBuyGoodsOnline` only when Daraja has enabled that transaction type for your Till.

Register provider callback URLs as `/accounts/social/google/login/callback/`, `/accounts/social/facebook/login/callback/`, and `/accounts/social/apple/login/callback/`. Run `python manage.py migrate` after installing dependencies to create the Sites and allauth tables.

## Manual refund and reconciliation process

1. Open the Django admin and review the customer's refund request under Payments.
2. Confirm the order is paid and delivered, verify the requested amount and reason, then set the request to `Approved` or `Rejected` and record a staff note.
3. Process the reversal through the payment provider's approved merchant procedure. Do not mark the request as processed until the provider confirms the reversal.
4. Enter the provider receipt or reversal reference in `External reference`, set the request to `Processed`, and save. The order payment status is then marked `Refunded`.
5. Reconcile the reference against the provider statement and export the sales report for the affected period. Investigate any amount or reference mismatch before closing the case.

The current application records and reconciles manual refunds; it does not call an automatic M-PESA reversal API.
