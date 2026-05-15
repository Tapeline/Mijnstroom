from mijnstroom.application.worker.dispatch import register_handler
from mijnstroom.application.worker.process_yt_video_job import (
    ProcessYtPlaylistItemJob,
    ProcessYtVideoJob,
)
from mijnstroom.domain.job import JobKind


def register_all_handlers() -> None:
    """Register all worker handlers in the HANDLER_REGISTRY.

    Phase 6 wires the YouTube ingestion handlers; Phase 9 will add the
    audio conversion handler. The function is idempotent.
    """
    register_handler(JobKind.YT_VIDEO, ProcessYtVideoJob)
    register_handler(JobKind.YT_PLAYLIST_ITEM, ProcessYtPlaylistItemJob)
