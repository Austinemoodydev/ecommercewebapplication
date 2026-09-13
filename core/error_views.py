from django.http import HttpResponse
from django.template.loader import get_template


def _error_response(
    template_name,
    *,
    status,
):

    # Render without passing request.
    #
    # This deliberately avoids normal context processors,
    # because some of this project's storefront context
    # processors query the database. A server error page
    # should still render even if the database is unavailable.
    template = get_template(
        template_name
    )

    html = template.render({})

    response = HttpResponse(
        html,
        status=status,
        content_type="text/html; charset=utf-8",
    )

    response["Cache-Control"] = (
        "no-store, no-cache, must-revalidate"
    )

    response["Pragma"] = "no-cache"

    response["X-Robots-Tag"] = (
        "noindex, nofollow"
    )

    return response


def bad_request(
    request,
    exception=None,
):

    return _error_response(
        "errors/400.html",
        status=400,
    )


def permission_denied(
    request,
    exception=None,
):

    return _error_response(
        "errors/403.html",
        status=403,
    )


def page_not_found(
    request,
    exception=None,
):

    return _error_response(
        "errors/404.html",
        status=404,
    )


def server_error(request):

    return _error_response(
        "errors/500.html",
        status=500,
    )
