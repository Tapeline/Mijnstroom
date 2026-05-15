from mijnstroom.infrastructure.youtube.description_parser import (
    RegexDescriptionChapterParser,
)


def test_simple_zero_zero_title() -> None:
    parser = RegexDescriptionChapterParser()
    desc = "0:00 Intro\n1:30 Verse\n3:45 Chorus"
    chapters = parser.parse(desc, total_duration_ms=300_000)
    assert len(chapters) == 3
    assert chapters[0].title == "Intro"
    assert chapters[0].start_ms == 0
    assert chapters[1].start_ms == 90_000
    assert chapters[2].end_ms == 300_000


def test_bracketed_timestamps() -> None:
    parser = RegexDescriptionChapterParser()
    desc = "[0:00] Intro\n[1:30] Verse"
    chapters = parser.parse(desc, None)
    assert [c.title for c in chapters] == ["Intro", "Verse"]


def test_timestamps_with_dash() -> None:
    parser = RegexDescriptionChapterParser()
    desc = "0:00 - Intro\n1:30 - Verse"
    chapters = parser.parse(desc, 200_000)
    assert [c.title for c in chapters] == ["Intro", "Verse"]


def test_timestamps_after_title() -> None:
    parser = RegexDescriptionChapterParser()
    desc = "Intro - 0:00\nVerse - 1:30"
    chapters = parser.parse(desc, 200_000)
    assert [c.title for c in chapters] == ["Intro", "Verse"]


def test_hour_long_timestamps() -> None:
    parser = RegexDescriptionChapterParser()
    desc = "1:23:45 Big Section"
    chapters = parser.parse(desc, None)
    assert len(chapters) == 1
    assert chapters[0].start_ms == (1 * 3600 + 23 * 60 + 45) * 1000


def test_no_timestamps_returns_empty() -> None:
    parser = RegexDescriptionChapterParser()
    assert parser.parse("Some random text\nwith no timestamps", None) == []
