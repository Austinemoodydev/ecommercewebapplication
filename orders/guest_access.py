import hashlib
import hmac
import secrets


TOKEN_BYTES = 32


def generate_guest_access_token():

    return secrets.token_urlsafe(
        TOKEN_BYTES
    )


def hash_guest_access_token(
    token,
):

    if not token:

        return ""

    return hashlib.sha256(
        token.encode(
            "utf-8"
        )
    ).hexdigest()


def verify_guest_access_token(
    order,
    token,
):

    if not order.guest_checkout:

        return False


    stored_hash = (
        order.guest_access_token_hash
        or ""
    )


    if not stored_hash:

        return False


    supplied_hash = (
        hash_guest_access_token(
            token
        )
    )


    return hmac.compare_digest(
        stored_hash,
        supplied_hash,
    )
