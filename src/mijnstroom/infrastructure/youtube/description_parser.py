import re

from mijnstroom.application.interfaces.chapters import DescriptionChapterParser
from mijnstroom.application.interfaces.ytdlp import YtChapter

# Time prefix variants we recognise: "1:23", "01:23", "1:23:45", optionally
# bracketed, optionally followed by a dash.
_TIME_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^\s*\[?(\d{1,2}:\d{2}(?::\d{2})?)\]?\s*[-–—:]?\s*(.+?)\s*$"),  # noqa: RUF001
    re.compile(r"^\s*(.+?)\s*[-–—:]\s*\[?(\d{1,2}:\d{2}(?::\d{2})?)\]?\s*$"),  # noqa: RUF001
)


def _parse_timestamp(value: str) -> int | None:
    parts = value.split(":")
    try:
        if len(parts) == 2:
            minutes, seconds = int(parts[0]), int(parts[1])
            return (minutes * 60 + seconds) * 1000
        if len(parts) == 3:
            hours, minutes, seconds = int(parts[0]), int(parts[1]), int(parts[2])
            return ((hours * 60 + minutes) * 60 + seconds) * 1000
    except ValueError:
        return None
    return None


class RegexDescriptionChapterParser(DescriptionChapterParser):
    """Best-effort chapter extraction from free-form video descriptions.

    Recognises the four common formats called out in
    ``spec/IMPLEMENTATION_PLAN.md``:

    - ``0:00 Title``
    - ``[0:00] Title``
    - ``0:00 - Title``
    - ``Title - 0:00``

    The list is sorted by start time before being returned, and end times
    are derived from the next chapter's start. The final chapter ends at
    ``total_duration_ms`` when known.
    """

    def parse(self, description: str, total_duration_ms: int | None) -> list[YtChapter]:
        candidates: list[tuple[int, str]] = []
        for raw in description.splitlines():
            line = raw.strip()
            if not line:
                continue
            for pattern in _TIME_PATTERNS:
                match = pattern.match(line)
                if not match:
                    continue
                groups = match.groups()
                # The first capture group is the timestamp in pattern 0,
                # and the title in pattern 1.
                if pattern is _TIME_PATTERNS[0]:
                    timestamp_str, title = groups
                else:
                    title, timestamp_str = groups
                start_ms = _parse_timestamp(timestamp_str)
                if start_ms is None:
                    continue
                title = title.strip(" -–—:")  # noqa: RUF001
                if title:
                    candidates.append((start_ms, title))
                break
        if not candidates:
            return []
        candidates.sort()
        chapters: list[YtChapter] = []
        for index, (start, title) in enumerate(candidates):
            if index + 1 < len(candidates):
                end = candidates[index + 1][0]
            elif total_duration_ms is not None:
                end = total_duration_ms
            else:
                end = start  # zero-length; caller may re-cut
            if end < start:
                end = start
            chapters.append(YtChapter(start_ms=start, end_ms=end, title=title))
        return chapters
