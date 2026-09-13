class SensitiveCapabilityURLMiddleware:
    """
    Extra response protection for URLs containing bearer-like
    capability values.

    Current sensitive URL families:

    /checkout/guest/<order>/<token>/...
    /payments/guest/.../<token>/...
    /payments/callback/?token=...

    These URLs must not be cached, indexed, or leaked through
    browser Referer headers.
    """

    SENSITIVE_PREFIXES = (
        "/checkout/guest/",
        "/payments/guest/",
        "/payments/callback/",
    )


    def __init__(self, get_response):

        self.get_response = get_response


    def __call__(self, request):

        response = self.get_response(
            request
        )

        if request.path.startswith(
            self.SENSITIVE_PREFIXES
        ):

            # Capability URLs contain values which effectively
            # grant access to protected functionality.
            response["Cache-Control"] = (
                "private, no-store, no-cache, "
                "must-revalidate, max-age=0"
            )

            response["Pragma"] = (
                "no-cache"
            )

            response["Expires"] = (
                "0"
            )

            # Stronger than the application's normal
            # same-origin policy for these sensitive pages.
            response["Referrer-Policy"] = (
                "no-referrer"
            )

            # Do not let order/payment capability URLs enter
            # search engine indexes.
            response["X-Robots-Tag"] = (
                "noindex, nofollow, noarchive"
            )


        return response
