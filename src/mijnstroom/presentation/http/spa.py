from litestar import Request


def is_spa_request(request: Request) -> bool:  # type: ignore[type-arg]
    """Check if this is an SPA AJAX navigation request."""
    return request.headers.get("X-Mijnstroom-SPA") == "1"
