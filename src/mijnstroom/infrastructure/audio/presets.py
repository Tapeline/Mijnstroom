from dataclasses import dataclass

from mijnstroom.domain.audio import AudioFormat


@dataclass(frozen=True, slots=True)
class FormatPreset:
    """Named encoding preset, used for downloads and conversions."""

    key: str
    display_name: str
    target_format: AudioFormat
    bitrate_kbps: int
    extension: str


AAC_256 = FormatPreset("aac256", "AAC 256 kbit", AudioFormat.AAC, 256, "m4a")
MP3_320 = FormatPreset("mp3-320", "MP3 320 kbit (CBR)", AudioFormat.MP3, 320, "mp3")
MP3_192 = FormatPreset("mp3-192", "MP3 192 kbit (legacy)", AudioFormat.MP3, 192, "mp3")

PRESETS: tuple[FormatPreset, ...] = (AAC_256, MP3_320, MP3_192)


def preset_by_key(key: str) -> FormatPreset | None:
    for preset in PRESETS:
        if preset.key == key:
            return preset
    return None
