from pathlib import Path

from litestar import get
from litestar.response import File
from litestar.static_files import create_static_files_router


@get("/login", sync_to_thread=False)
def serve_login() -> File:
    """Serve the login page."""
    return File(path=Path("frontend/login.html"), content_disposition_type="inline")


frontend_router = create_static_files_router(
    path="/",
    directories=["frontend"],
    html_mode=True,
)
