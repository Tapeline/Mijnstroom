from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from dishka import AsyncContainer
from dishka.integrations.litestar import setup_dishka
from litestar import Litestar
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.static_files import create_static_files_router
from litestar.template.config import TemplateConfig

from mijnstroom.presentation.http.controllers.auth import AuthController
from mijnstroom.presentation.http.controllers.health import healthz
from mijnstroom.presentation.http.error_handlers import app_exception_handler
from mijnstroom.presentation.http.middleware import auth_middleware

_PRESENTATION_ROOT = Path(__file__).resolve().parent.parent
_TEMPLATES_DIR = _PRESENTATION_ROOT / "templates"
_STATIC_DIR = _PRESENTATION_ROOT / "static"


def create_app(container: AsyncContainer) -> Litestar:
    """Create the Litestar application bound to the given Dishka container.

    Auth middleware is installed at the outermost ASGI layer via
    :attr:`Litestar.asgi_handler` so that even unrouted paths are
    redirected to login rather than producing a 404.
    """

    @asynccontextmanager
    async def lifespan(app: Litestar) -> AsyncIterator[None]:
        try:
            yield
        finally:
            await container.close()

    static_router = create_static_files_router(path="/static", directories=[str(_STATIC_DIR)])

    app = Litestar(
        route_handlers=[
            healthz,
            AuthController,
            static_router,
        ],
        template_config=TemplateConfig(
            directory=str(_TEMPLATES_DIR),
            engine=JinjaTemplateEngine,
        ),
        exception_handlers={Exception: app_exception_handler},
        lifespan=[lifespan],
        debug=False,
    )
    setup_dishka(container=container, app=app)
    # Wrap the outermost ASGI handler so middleware runs before routing.
    app.asgi_handler = auth_middleware(app.asgi_handler)
    return app
