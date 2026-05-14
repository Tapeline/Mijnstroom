import logging

from litestar import MediaType, Request, Response
from litestar.exceptions import HTTPException
from litestar.response import Template

from mijnstroom.common.errors import (
    AppError,
    Conflict,
    Forbidden,
    NotFound,
    Unauthenticated,
    ValidationError,
)

logger = logging.getLogger(__name__)


def map_error(err: Exception) -> tuple[int, str]:
    """Map an application error to (HTTP status, short error code)."""
    match err:
        case Unauthenticated():
            return 401, "unauthenticated"
        case Forbidden():
            return 403, "forbidden"
        case NotFound():
            return 404, "not_found"
        case Conflict():
            return 409, "conflict"
        case ValidationError():
            return 400, "validation_error"
        case AppError():
            return 400, "app_error"
        case HTTPException() as http:
            status = int(http.status_code)
            if status == 404:
                return 404, "not_found"
            if status == 405:
                return 405, "method_not_allowed"
            if status == 401:
                return 401, "unauthenticated"
            if status == 403:
                return 403, "forbidden"
            if 400 <= status < 500:
                return status, "bad_request"
            return status, "http_error"
        case _:
            return 500, "internal_error"


def app_exception_handler(request: Request, exc: Exception) -> Response[object]:  # type: ignore[type-arg]
    """Render a minimal HTML4 error page for any exception."""
    status_code, error_code = map_error(exc)
    if status_code >= 500:
        logger.exception("Unhandled exception: %s", exc)
    message = str(exc) if isinstance(exc, AppError | HTTPException) else ""
    accept = request.headers.get("accept", "")
    if "text/html" in accept or accept == "":
        return Template(  # type: ignore[return-value]
            template_name="errors/error.html",
            context={
                "status_code": status_code,
                "error_code": error_code,
                "message": message,
            },
            status_code=status_code,
            media_type=MediaType.HTML,
        )
    return Response(
        content={"error": error_code, "message": message},
        status_code=status_code,
        media_type=MediaType.JSON,
    )


