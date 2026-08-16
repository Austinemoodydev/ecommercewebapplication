import base64
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests
from django.conf import settings
from django.utils import timezone


class MpesaError(Exception):
    """A safe message suitable for returning to the checkout screen."""


def get_base_url():
    return "https://api.safaricom.co.ke" if settings.MPESA_ENV == "production" else "https://sandbox.safaricom.co.ke"


def _require_settings(*names):
    missing = [name for name in names if not getattr(settings, name, None)]
    if missing:
        raise MpesaError(f"M-PESA is not configured: missing {', '.join(missing)}.")


def get_access_token():
    _require_settings("MPESA_CONSUMER_KEY", "MPESA_CONSUMER_SECRET")
    try:
        response = requests.get(
            f"{get_base_url()}/oauth/v1/generate?grant_type=client_credentials",
            auth=(settings.MPESA_CONSUMER_KEY, settings.MPESA_CONSUMER_SECRET),
            timeout=(5, 30),
        )
        response.raise_for_status()
        return response.json()["access_token"]
    except (requests.RequestException, KeyError, ValueError) as exc:
        raise MpesaError("Could not authenticate with M-PESA. Check your consumer key, secret, and environment.") from exc


def format_phone_number(phone):
    """Return a Kenyan Safaricom-compatible MSISDN: 2547XXXXXXXX."""
    phone = "".join(str(phone).strip().split()).replace("+", "")
    if phone.startswith("0"):
        phone = f"254{phone[1:]}"
    if not phone.isdigit() or len(phone) != 12 or not phone.startswith("2547"):
        raise MpesaError("Enter a valid Kenyan M-PESA number, for example 0712345678.")
    return phone


def generate_password(timestamp):
    raw = f"{settings.MPESA_SHORTCODE}{settings.MPESA_PASSKEY}{timestamp}"
    return base64.b64encode(raw.encode()).decode()


def get_callback_url():
    _require_settings("MPESA_CALLBACK_URL", "MPESA_CALLBACK_SECRET")
    callback_url = settings.MPESA_CALLBACK_URL
    parsed = urlsplit(callback_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise MpesaError("MPESA_CALLBACK_URL must be a public HTTPS URL.")
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.setdefault("token", settings.MPESA_CALLBACK_SECRET)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment))


def stk_push(phone_number, amount, order_number, description="Order payment"):
    _require_settings("MPESA_SHORTCODE", "MPESA_PASSKEY")
    try:
        amount = Decimal(amount).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise MpesaError("The order amount is invalid.") from exc
    if amount < 1:
        raise MpesaError("The order amount must be at least KES 1.")

    timestamp = timezone.localtime().strftime("%Y%m%d%H%M%S")
    phone_number = format_phone_number(phone_number)
    payload = {
        "BusinessShortCode": settings.MPESA_SHORTCODE,
        "Password": generate_password(timestamp),
        "Timestamp": timestamp,
        "TransactionType": settings.MPESA_TRANSACTION_TYPE,
        "Amount": int(amount),
        "PartyA": phone_number,
        "PartyB": settings.MPESA_SHORTCODE,
        "PhoneNumber": phone_number,
        "CallBackURL": get_callback_url(),
        "AccountReference": str(order_number)[:12],
        "TransactionDesc": description[:13],
    }
    try:
        response = requests.post(
            f"{get_base_url()}/mpesa/stkpush/v1/processrequest",
            json=payload,
            headers={"Authorization": f"Bearer {get_access_token()}", "Content-Type": "application/json"},
            timeout=(5, 30),
        )
        data = response.json()
    except requests.RequestException as exc:
        raise MpesaError("M-PESA could not be reached. Please try again shortly.") from exc
    except ValueError as exc:
        raise MpesaError("M-PESA returned an invalid response. Please try again shortly.") from exc

    if not response.ok or data.get("ResponseCode") != "0":
        raise MpesaError(data.get("errorMessage") or data.get("ResponseDescription") or "M-PESA rejected the payment request.")
    return data
