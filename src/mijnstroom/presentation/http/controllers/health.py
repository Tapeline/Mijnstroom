from dishka.integrations.litestar import FromDishka, inject
from litestar import get

from mijnstroom.bootstrap.config import Config


@get("/healthz")
@inject
async def healthz(config: FromDishka[Config]) -> dict[str, str]:
    return {"status": "ok", "data_dir": config.storage.data_dir}


