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
