class AppError(Exception):
    """Base class for every error raised inside the application core."""


class NotFound(AppError):  # noqa: N818  -- domain-style name preferred over -Error suffix
    """A requested entity does not exist."""


class Conflict(AppError):  # noqa: N818
    """An operation is incompatible with the current state."""


class Unauthenticated(AppError):  # noqa: N818
    """The caller is not authenticated."""


class Forbidden(AppError):  # noqa: N818
    """The caller is authenticated but lacks permission."""


class ValidationError(AppError):
    """Input fails an invariant or precondition."""
