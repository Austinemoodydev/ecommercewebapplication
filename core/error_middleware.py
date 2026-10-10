import logging
import traceback
from uuid import uuid4

from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.http import Http404
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.deprecation import MiddlewareMixin

from .models import ErrorReport

logger = logging.getLogger(__name__)


class ApplicationErrorMiddleware(MiddlewareMixin):
    def process_exception(self, request, exception):
        # Expected client errors must retain Django's 400/403/404 handling.
        # Only unexpected server failures belong in the operational error log.
        if isinstance(exception, (Http404, PermissionDenied, SuspiciousOperation)):
            return None

        reference = uuid4().hex[:10].upper()
        logger.error("Unhandled application error %s at %s: %s", reference, request.path, exception)
        try:
            ErrorReport.objects.create(
                reference=reference,
                path=request.path[:500],
                method=request.method[:10],
                exception_type=exception.__class__.__name__[:150],
                message=str(exception)[:4000],
                traceback="".join(
                    traceback.format_exception(
                        type(exception), exception, exception.__traceback__
                    )
                )[-20000:],
                user=request.user if getattr(request, "user", None) and request.user.is_authenticated else None,
            )
        except Exception:
            logger.exception("Could not persist error report %s", reference)

        message = "We could not complete your request. Please try again. If it continues, contact support with the reference below."
        wants_json = request.headers.get("X-Requested-With") == "XMLHttpRequest" or "application/json" in request.headers.get("Accept", "")
        if wants_json:
            return JsonResponse({"success": False, "error": message, "reference": reference}, status=500)
        return render(request, "errors/500.html", {"error_reference": reference}, status=500)
