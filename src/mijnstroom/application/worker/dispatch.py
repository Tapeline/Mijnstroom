from typing import Protocol

from mijnstroom.domain.job import Job, JobKind


class JobHandler(Protocol):
    """Stateless interactor used by the worker to process a job.

    Concrete handlers are registered into the Dishka container by
    binding them to ``JobKind`` keys via :data:`HANDLER_REGISTRY`.
    """

    async def __call__(self, job: Job) -> None: ...


# Mapping populated lazily by the worker at startup. Keeping this as a
# plain dict avoids pulling concrete handlers into the application layer.
HANDLER_REGISTRY: dict[JobKind, type[JobHandler]] = {}


def register_handler(kind: JobKind, handler_cls: type[JobHandler]) -> None:
    """Register ``handler_cls`` for the given ``JobKind``.

    The registry is module-level by design so the worker bootstrap can
    populate it once at startup. The web process never reads the registry.
    """
    HANDLER_REGISTRY[kind] = handler_cls
