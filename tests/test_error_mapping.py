import pytest

from mijnstroom.common.errors import (
    AppError,
    Conflict,
    Forbidden,
    NotFound,
    Unauthenticated,
    ValidationError,
)
from mijnstroom.presentation.http.error_handlers import map_error


@pytest.mark.parametrize(
    ("err", "status", "code"),
    [
        (Unauthenticated("x"), 401, "unauthenticated"),
        (Forbidden("x"), 403, "forbidden"),
        (NotFound("x"), 404, "not_found"),
        (Conflict("x"), 409, "conflict"),
        (ValidationError("x"), 400, "validation_error"),
        (AppError("x"), 400, "app_error"),
        (RuntimeError("x"), 500, "internal_error"),
    ],
)
def test_map_error(err: Exception, status: int, code: str) -> None:
    assert map_error(err) == (status, code)
