# Mijnstroom Implementation Plan

This plan turns `spec/MAIN.md`, `spec/BACKEND_ARCH.md` and
`spec/GUIDELINES.md` into a concrete, ordered programme of work.

## 0. Locked decisions

| Concern                | Decision                                                                  |
| ---------------------- | ------------------------------------------------------------------------- |
| Language / runtime     | Python 3.13, managed by `uv`                                              |
| Web framework          | Litestar with Jinja SSR                                                   |
| DI                     | Dishka (`dishka.integrations.litestar`)                                   |
| Database               | SQLite via `aiosqlite`, no ORM, hand-written SQL                          |
| Queue                  | SQLite-backed, separate worker process                                    |
| Auth                   | OIDC code flow against Authelia (`authlib`); single-user gate by `sub`    |
| Frontend               | HTML 4.01 Strict / CSS 2.1 / ES3; progressive enhance.js optional         |
| Audio                  | AAC 256 kbit `.m4a` default; ffmpeg + yt-dlp                              |
| Storage layout         | Content-addressed: `/data/tracks/<uuid>.<ext>`                            |
| AI recommendations     | Dropped from scope                                                        |
| YouTube piece defaults | Prefer yt-dlp chapters; fallback to description regex; user always edits  |
| Bulk metadata edit     | Form-based with checkboxes and per-field "apply" toggle                   |
| Transaction model      | Single `Transaction` type, always `BEGIN IMMEDIATE`                       |
| Worker dispatch        | `dict[JobKind, type[Interactor]]` registered in Dishka                    |
| Worker `UserIdProvider`| `SystemUserIdProvider` returning the configured user                      |
| `@interactor`          | `@dataclass(slots=True)` (mutable), fields injected by Dishka             |
| Form / view-model home | `presentation/http/forms` and `presentation/http/view_models`             |
| Application DTOs       | Co-located in `application/<feature>/dto.py`                              |
| `enhance.js`           | Kept; optional and harmless on legacy browsers                            |

## 1. Target source tree

```
src/mijnstroom/
├── common/
│   ├── decorators.py
│   ├── errors.py
│   ├── ids.py
│   ├── result.py
│   └── time.py
├── domain/
│   ├── audio.py
│   ├── job.py
│   ├── playlist.py
│   ├── track.py
│   └── ytsource.py
├── application/
│   ├── interfaces/
│   │   ├── audio.py
│   │   ├── chapters.py
│   │   ├── idp.py
│   │   ├── queue.py
│   │   ├── repos.py
│   │   ├── storage.py
│   │   ├── tx.py
│   │   └── ytdlp.py
│   ├── tracks/
│   │   ├── dto.py
│   │   ├── upload_track.py
│   │   ├── edit_metadata.py
│   │   ├── bulk_edit_metadata.py
│   │   ├── delete_track.py
│   │   ├── list_tracks.py
│   │   └── stream_track.py
│   ├── playlists/
│   │   ├── dto.py
│   │   ├── create_playlist.py
│   │   ├── rename_playlist.py
│   │   ├── delete_playlist.py
│   │   ├── add_track_to_playlist.py
│   │   ├── remove_track_from_playlist.py
│   │   └── list_playlists.py
│   ├── youtube/
│   │   ├── dto.py
│   │   ├── search_youtube.py
│   │   ├── prepare_video.py
│   │   ├── prepare_playlist.py
│   │   ├── submit_video_download.py
│   │   └── submit_playlist_download.py
│   ├── queue/
│   │   ├── dto.py
│   │   ├── list_jobs.py
│   │   ├── cancel_job.py
│   │   └── delete_failed_job.py
│   └── worker/
│       ├── dispatch.py
│       ├── process_yt_video_job.py
│       ├── process_yt_playlist_item_job.py
│       └── process_convert_job.py
├── infrastructure/
│   ├── audio/
│   │   ├── ffmpeg.py
│   │   ├── ffprobe.py
│   │   └── presets.py
│   ├── auth/
│   │   ├── oidc_client.py
│   │   └── session_idp.py
│   ├── logging.py
│   ├── persistence/
│   │   ├── job_repo.py
│   │   ├── migrations/
│   │   ├── playlist_repo.py
│   │   ├── sqlite.py
│   │   ├── track_repo.py
│   │   └── transaction.py
│   ├── queue/
│   │   └── sqlite_queue.py
│   ├── storage/
│   │   └── local_fs.py
│   └── youtube/
│       ├── description_parser.py
│       └── ytdlp_client.py
├── presentation/
│   ├── http/
│   │   ├── app.py
│   │   ├── controllers/
│   │   │   ├── auth.py
│   │   │   ├── bulk.py
│   │   │   ├── library.py
│   │   │   ├── playlists.py
│   │   │   ├── queue.py
│   │   │   ├── stream.py
│   │   │   ├── upload.py
│   │   │   └── youtube.py
│   │   ├── deps.py
│   │   ├── error_handlers.py
│   │   ├── forms/
│   │   └── view_models/
│   ├── static/
│   └── templates/
└── bootstrap/
    ├── config.py
    ├── di/
    │   ├── container.py
    │   └── providers.py
    ├── logging.py
    ├── main.py
    └── worker.py
```

## 2. Database schema (initial migrations)

`infrastructure/persistence/migrations/0001_init.sql`:

```sql
CREATE TABLE schema_version (version INTEGER PRIMARY KEY);

CREATE TABLE tracks (
    id            TEXT PRIMARY KEY,
    storage_path  TEXT NOT NULL,
    format        TEXT NOT NULL,
    duration_ms   INTEGER,
    title         TEXT,
    artist        TEXT,
    album         TEXT,
    year          INTEGER,
    genre         TEXT,
    cover_path    TEXT,
    lyrics        TEXT,
    created_at    TEXT NOT NULL
);

CREATE TABLE playlists (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TABLE playlist_tracks (
    playlist_id TEXT NOT NULL REFERENCES playlists(id) ON DELETE CASCADE,
    track_id    TEXT NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
    position    INTEGER NOT NULL,
    PRIMARY KEY (playlist_id, track_id)
);

CREATE TABLE jobs (
    id              TEXT PRIMARY KEY,
    kind            TEXT NOT NULL,
    payload_json    TEXT NOT NULL,
    status          TEXT NOT NULL,
    attempts        INTEGER NOT NULL DEFAULT 0,
    error           TEXT,
    parent_job_id   TEXT,
    created_at      TEXT NOT NULL,
    started_at      TEXT,
    finished_at     TEXT,
    next_run_at     TEXT NOT NULL
);

CREATE INDEX jobs_status_next ON jobs (status, next_run_at);
```

WAL mode and `busy_timeout=5000` are applied as session pragmas at
connection time, not in the migration.

## 3. Configuration

```yaml
# config.example.yaml
storage:
  data_dir: /data
http:
  host: 0.0.0.0
  port: 8000
oidc:
  issuer: https://auth.example.com
  client_id: mijnstroom
  client_secret: change-me
  redirect_uri: https://music.example.com/auth/callback
  allowed_sub: my-authelia-sub
youtube:
  interval_seconds: 30
queue:
  poll_interval_seconds: 2
audio:
  default_format: aac
  default_bitrate_kbps: 256
session:
  secret: change-me
```

`bootstrap/config.py` declares the matching dataclass tree
(`Config`, `StorageConfig`, `HttpConfig`, `OIDCConfig`, `YoutubeConfig`,
`QueueConfig`, `AudioConfig`, `SessionConfig`) and a `load_config(path:
str) -> Config` function whose body is left empty if `dature` usage is
uncertain.

## 4. DI providers

```
ConfigProvider   (APP)    -> Config and sub-configs
InfraProvider    (APP)    -> aiosqlite pool, FileStorage, AudioProbe,
                              AudioConverter, TagWriter, YoutubeClient,
                              DescriptionChapterParser, Clock,
                              QueueGateway, OIDCClient
RequestProvider  (REQUEST)-> Transaction, TrackRepo, PlaylistRepo,
                              JobRepo, UserIdProvider
InteractorProvider (REQUEST) -> provide_all of every interactor
WorkerProvider   (REQUEST)-> SystemUserIdProvider override + worker-only
                              interactors
```

The web entrypoint uses `ConfigProvider`, `InfraProvider`,
`RequestProvider`, `InteractorProvider`, plus `LitestarProvider()`. The
worker entrypoint swaps `RequestProvider`'s `UserIdProvider` for
`SystemUserIdProvider` via `WorkerProvider`.

## 5. Phased delivery

Each phase is shippable (the previous behaviour keeps working) and ends
with passing tests for the phase's slice.

### Phase 1 — Skeleton

- `pyproject.toml` (uv), `ruff`, `mypy`, `pytest`.
- `common`: decorators, ids, errors, Clock protocol, `SystemClock` impl.
- `domain`: `Track`, `Playlist`, `Job` skeletons with their value objects
  and base errors.
- `application/interfaces`: protocols (empty methods).
- `bootstrap`: `config.py` (dataclasses + empty `load_config`), `logging`,
  `di/providers.py` (Config + Infra placeholders), `di/container.py`,
  `main.py` and `worker.py` shells.
- `infrastructure/persistence`: aiosqlite pool, migration runner,
  `0001_init.sql`.
- `presentation/http/app.py`: Litestar factory, `setup_dishka`, a
  `/healthz` controller using `FromDishka[Config]` to confirm wiring.
- `Dockerfile` + `docker-compose.yml` building the image and running
  `web` and `worker` services on the shared volume.
- Tests: container resolves, migrations apply, `/healthz` returns 200.

### Phase 2 — Auth

- `infrastructure/auth/oidc_client.py`: authlib code-flow client.
- `infrastructure/auth/session_idp.py`: `UserIdProvider` over signed
  cookie (`itsdangerous`).
- Controllers under `presentation/http/controllers/auth.py`: `/auth/login`,
  `/auth/callback`, `/auth/logout`.
- Middleware that redirects unauthenticated requests to login (excluding
  `/auth/*` and `/static/*`).
- `presentation/http/error_handlers.py`: `map_error`, Litestar handler,
  HTML4 error template.
- Tests: callback verifies `sub`, denies non-allowed users.

### Phase 3 — Tracks vertical slice

- `infrastructure/storage/local_fs.py`: write/move/delete under
  `<data_dir>/tracks` and `<data_dir>/incoming`.
- `infrastructure/audio/ffprobe.py` and `ffmpeg.py`: probe + tag write +
  cover embed via subprocess.
- `infrastructure/persistence/track_repo.py`: hand-written SQL.
- Interactors: `UploadTrack`, `EditTrackMetadata`, `DeleteTrack`,
  `ListTracks`, `StreamTrack`.
- Controllers: `library.py` (list with search), `upload.py` (multipart →
  metadata form → save), `stream.py` (range + download).
- Templates: track list, upload form, metadata form, single track page.
- Static: `style.css` (GPM palette), optional `enhance.js` (ES3 audio
  player wiring).
- Tests: end-to-end via `httpx.AsyncClient`.

### Phase 4 — Playlists

- `infrastructure/persistence/playlist_repo.py`.
- Interactors: create / rename / delete playlist, add / remove track,
  list playlists, view playlist tracks.
- Controllers and templates under `presentation/http/controllers/playlists.py`.
- Tests for invariants (e.g. rename to blank rejected, delete cascades to
  `playlist_tracks`).

### Phase 5 — Queue plumbing and worker bootstrap

- `infrastructure/persistence/job_repo.py` and
  `infrastructure/queue/sqlite_queue.py` implementing `QueueGateway` with
  atomic claim.
- Worker loop in `bootstrap/worker.py`: poll, claim, dispatch via
  registered handler map, commit / fail / reschedule.
- `application/worker/dispatch.py`: handler registry contract.
- Tests: concurrency test that two workers cannot claim the same job;
  rate-limit spacing honoured.

### Phase 6 — YouTube ingestion

- `infrastructure/youtube/ytdlp_client.py`: search, info extract, audio
  download to a temp path.
- `infrastructure/youtube/description_parser.py`: regex set covering
  `0:00 Title`, `[0:00] Title`, `0:00 - Title`, `1:23:45 Title`.
- Interactors: `SearchYoutube`, `PrepareVideo` (uses chapters first,
  parser fallback), `PreparePlaylist`, `SubmitVideoDownload`,
  `SubmitPlaylistDownload`.
- Worker handlers: `ProcessYtVideoJob` (download once, ffmpeg-cut per
  enabled piece, embed cover, insert track per piece),
  `ProcessYtPlaylistItemJob`.
- Controllers and templates under
  `presentation/http/controllers/youtube.py`: search results, prepare
  page (per-piece editable rows), submission redirects to queue page.
- Tests: parser covers the four formats; prepare returns yt-dlp chapters
  when present; submission enqueues the expected jobs.

### Phase 7 — Queue UI

- Interactors: `ListJobs`, `CancelJob`, `DeleteFailedJob`.
- Controller `queue.py`: pending / running / failed sections; cancel and
  delete-failed buttons.
- Tests: cancel only succeeds while pending; delete-failed cleans temp
  files.

### Phase 8 — Bulk metadata edit

- `BulkEditTrackMetadata` interactor: given selected ids and a patch
  describing which fields to apply, updates rows in one SQL statement.
- Controller `bulk.py` with the two-step form: select on the list page,
  then per-field "apply" checkboxes.
- Tests: only checked fields update; cover replacement re-embeds and
  rewrites `cover_path`.

### Phase 9 — Lyrics and conversion downloads

- Add `lyrics` field to track edit form and template.
- `audio/presets.py`: AAC 256, MP3 320 CBR, MP3 192 CBR (legacy player
  preset).
- `ProcessConvertJob` worker handler producing a temporary file under
  `<data_dir>/cache/<uuid>-<format>.<ext>` with a TTL janitor (run as a
  recurring job).
- `/download?format=` controller: serves directly when format matches,
  otherwise enqueues a conversion and shows a "ready when done" page that
  refreshes via meta-refresh.

### Phase 10 — Polish

- GPM-2014 styling pass on every template.
- Nokia smoke test against the served pages (verify no CSS3, no ES4+).
- Docker-compose memory limits and resource verification against the
  300 MB peak budget.
- README with setup instructions and Authelia configuration snippet.

## 6. Cross-cutting checklists

Before any phase is considered complete:

- [ ] All new public functions and protocols carry full type annotations.
- [ ] `ruff check` and `ruff format --check` pass.
- [ ] `mypy --strict src/mijnstroom` passes.
- [ ] `pytest` passes.
- [ ] No imports cross the layer rules in `spec/GUIDELINES.md` §1.
- [ ] No HTML or template uses CSS3, flexbox, grid, transitions or
      shadows.
- [ ] No new direct I/O appears in `application/`.
- [ ] New entities have explicit invariants and at least one negative
      unit test per invariant.

## 7. Risks and mitigations

| Risk                                                       | Mitigation                                                                 |
| ---------------------------------------------------------- | -------------------------------------------------------------------------- |
| 300 MB RAM budget tight with ffmpeg / yt-dlp running       | Worker runs ffmpeg as a subprocess, not in-process; uvicorn `--workers 1`. |
| SQLite write contention between worker and web             | WAL + `BEGIN IMMEDIATE`; single worker; short transactions.                |
| HTML4 / ES3 constraint vs. modern browsers                 | Progressive `enhance.js` strictly optional; core flows are pure HTML.      |
| YouTube anti-abuse                                         | Rate limit via `next_run_at`; configurable interval per `config.youtube`.  |
| Half-written files on worker crash                         | All file moves are atomic (`os.replace`); cleanup runs on `delete_failed`. |
| dature API uncertainty                                     | `load_config` may be left empty per `spec/MAIN.md` instruction.            |
