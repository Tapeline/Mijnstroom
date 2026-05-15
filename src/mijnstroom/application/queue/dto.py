from mijnstroom.common.decorators import dto


@dto
class JobView:
    """Read-only view of a job for the queue UI."""

    id: str
    kind: str
    status: str
    attempts: int
    error: str | None
    created_at: str
    next_run_at: str
