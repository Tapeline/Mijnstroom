from mijnstroom.application.interfaces.audio import AudioProbe, CoverExtractor
from mijnstroom.application.interfaces.idp import UserIdProvider
from mijnstroom.application.interfaces.repos import TrackRepo
from mijnstroom.application.interfaces.storage import FileStorage
from mijnstroom.application.interfaces.tx import Transaction
from mijnstroom.application.tracks.dto import FinalizeUploadInput
from mijnstroom.common.decorators import interactor
from mijnstroom.common.errors import ValidationError
from mijnstroom.common.ids import generate_id
from mijnstroom.common.time import Clock
from mijnstroom.domain.audio import AudioFormat
from mijnstroom.domain.track import Track, TrackId


def _ext_for(fmt: AudioFormat) -> str:
    return {
        AudioFormat.AAC: "m4a",
        AudioFormat.MP3: "mp3",
        AudioFormat.OGG: "ogg",
        AudioFormat.FLAC: "flac",
        AudioFormat.WAV: "wav",
        AudioFormat.OPUS: "opus",
    }[fmt]


@interactor
class UploadTrack:
    """Persist a freshly uploaded audio file as a new ``Track``.

    The file is expected to already be present at ``input.incoming_path``
    (the controller saved the multipart upload to that location). The
    interactor probes it, generates a track id, moves the file into the
    library, optionally writes a cover, and inserts the row.
    """

    repo: TrackRepo
    storage: FileStorage
    probe: AudioProbe
    cover_extractor: CoverExtractor
    tx: Transaction
    idp: UserIdProvider
    clock: Clock

    async def __call__(self, input: FinalizeUploadInput) -> Track:
        if not input.title.strip():
            raise ValidationError("Track title cannot be blank")

        probed = await self.probe.probe(input.incoming_path)
        track_id = generate_id(TrackId)
        ext = _ext_for(probed.format)
        async with self.tx:
            await self.idp.require_user()
            storage_path = await self.storage.move_to_tracks(input.incoming_path, ext, track_id)
            cover_path: str | None = None
            if input.cover_bytes:
                cover_path = await self.storage.write_cover(input.cover_bytes, track_id)
            else:
                embedded = await self.cover_extractor.extract(input.incoming_path)
                if embedded:
                    cover_path = await self.storage.write_cover(embedded, track_id)
            track = Track(
                id=track_id,
                storage_path=storage_path,
                format=probed.format,
                duration_ms=probed.duration_ms,
                title=input.title.strip(),
                artist=input.artist or probed.artist,
                album=input.album or probed.album,
                year=input.year if input.year is not None else probed.year,
                genre=input.genre or probed.genre,
                cover_path=cover_path,
                lyrics=input.lyrics,
                created_at=self.clock.now(),
            )
            await self.repo.insert(track)
        return track
