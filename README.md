# Mijnstroom

Self-hosted music storage and streaming service. Upload your library, download
from YouTube, split full-album videos into individual tracks, and stream
everywhere — from modern browsers down to a Nokia feature phone.

## Features

- **Library management** — upload audio files (MP3, M4A/AAC, OGG, FLAC, WAV,
  OPUS), browse cards with album art, search, edit metadata, bulk-edit.
- **YouTube ingestion** — search or paste a URL, preview results, split a video
  into named pieces with per-piece metadata, enqueue async download.
- **Playlists** — create, rename, add/remove tracks, play entire playlists.
- **Queue & worker** — background job queue with status page, cancel/delete,
  rate-limited YouTube downloads.
- **Audio player** — full-width progress bar, album cover, volume control,
  repeat modes (off / all / one), prev/next, playlist-aware queue.
- **Conversion downloads** — download tracks in alternate formats (MP3 320,
  MP3 192) via on-the-fly or queued ffmpeg conversion.
- **Legacy browser support** — core flows (library, YouTube, download) work
  on HTML 4.01 / CSS 2.1 browsers without JavaScript. Modern enhancements
  (sidebar, player, ripples, dynamic pieces) are loaded via
  `<script type="module">` and silently ignored by legacy browsers.
- **Single-user OIDC auth** — integrates with Authelia (or any OIDC provider);
  gates access by a configured user `sub`.

## Architecture

```
common ← domain ← application ← infrastructure / presentation ← bootstrap
```

| Layer | Responsibility |
|-------|---------------|
| `common` | Cross-cutting utilities: IDs, errors, clock, result type |
| `domain` | Pure value objects and entities: `Track`, `Playlist`, `Job`, `AudioFormat` |
| `application` | Interactors (use cases) with `Protocol` dependencies |
| `infrastructure` | Concrete implementations: SQLite, ffmpeg, ffprobe, yt-dlp, OIDC, local FS |
| `presentation` | Litestar HTTP controllers, Jinja2 templates, static assets |
| `bootstrap` | Wiring: config, DI container (Dishka), logging, entry points |

**Stack:** Python 3.13 · Litestar + Jinja2 SSR · Dishka DI · SQLite (hand-written SQL, WAL mode) · yt-dlp · ffmpeg · Authelia (OIDC)

## Quick start

```sh
# 1. Clone and install dependencies
uv sync

# 2. Copy and edit config
cp config.example.yaml config.yml
# Edit config.yml — at minimum set session.secret and oidc settings

# 3. Start the web server
uv run python -m mijnstroom.bootstrap web

# 4. (Separate terminal) Start the background worker
uv run python -m mijnstroom.bootstrap worker
```

Open `http://localhost:8000` in your browser.

## Docker

```sh
# Build and run with docker-compose
docker compose up -d

# Or build and run manually
docker build -t mijnstroom .
docker run -p 8000:8000 -v mijnstroom-data:/data --env-file .env mijnstroom
```

The compose file runs two services:
- **web** — Litestar app on port 8000 (200 MB memory limit)
- **worker** — background job processor (100 MB memory limit)

Both share a `data` volume for the SQLite database and audio files.

## Configuration

Copy `config.example.yaml` to `config.yml` and adjust:

```yaml
storage:
  data_dir: /data          # Where tracks, covers, and the SQLite DB live

http:
  host: 0.0.0.0
  port: 8000

oidc:
  issuer: https://auth.example.com
  client_id: mijnstroom
  client_secret: change-me
  redirect_uri: https://music.example.com/auth/callback
  allowed_sub: 00000000-0000-0000-0000-000000000000  # single-user gate

youtube:
  interval_seconds: 30     # Minimum gap between YouTube downloads

queue:
  poll_interval_seconds: 2 # Worker poll frequency

audio:
  default_format: aac      # Default output format (aac, mp3, ogg, flac, wav, opus)
  default_bitrate_kbps: 256

session:
  secret: <32+ random hex> # Generate with: openssl rand -hex 32
```

Environment variable `MIJNSTROOM_DATA_DIR` overrides `storage.data_dir`.

## Development

```sh
uv sync --all-groups

# Tests
uv run pytest

# Lint
uv run ruff check src tests

# Type check
uv run mypy src/mijnstroom

# Auto-fix lint issues
uv run ruff check --fix src tests
```

## Authelia setup

Mijnstroom uses OIDC Authorization Code flow. In your Authelia configuration:

```yaml
identity_providers:
  oidc:
    clients:
      - id: mijnstroom
        description: Mijnstroom Music
        secret: '$pbkdf2sha256$...'   # pbkdf2 hash of your client_secret
        public: false
        authorization_policy: two_factor
        redirect_uris:
          - https://music.example.com/auth/callback
        scopes:
          - openid
          - profile
        userinfo_signing_algorithm: none
```

Set `oidc.allowed_sub` in `config.yml` to the user's `sub` claim to restrict
access to a single account.

## Storage layout

```
/data/
├── mijnstroom.sqlite          # Application database (WAL mode)
├── tracks/
│   ├── <uuid>.m4a             # Audio files (content-addressed)
│   └── <uuid>.cover.jpg       # Album art (optional)
├── incoming/                  # Temp uploads (cleaned after processing)
└── cache/                     # Conversion output (TTL-cleaned)
```

## Frontend

The UI follows the Google Play Music 2014 (Material Design 1) aesthetic:

- **Top bar** — brand, search, logout
- **Left sidebar** — Library, YouTube, Upload, Playlists, Queue
- **Content area** — card grid, tables, forms
- **Bottom player** — full-width progress, album cover, controls (modern only)

Legacy browsers (Nokia, IE ≤ 8) see a clean HTML 4.01 layout with CSS 2.1
styling. The player bar and JavaScript enhancements are hidden from them
via `display: none` and `<script type="module">` respectively.

## License

Private / personal use.
