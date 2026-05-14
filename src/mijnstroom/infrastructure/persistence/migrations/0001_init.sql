CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);

CREATE TABLE tracks (
    id            TEXT PRIMARY KEY,
    storage_path  TEXT NOT NULL,
    format        TEXT NOT NULL,
    duration_ms   INTEGER,
    title         TEXT NOT NULL,
    artist        TEXT,
    album         TEXT,
    year          INTEGER,
    genre         TEXT,
    cover_path    TEXT,
    lyrics        TEXT,
    created_at    TEXT NOT NULL
);

CREATE INDEX tracks_title ON tracks (title);
CREATE INDEX tracks_artist ON tracks (artist);
CREATE INDEX tracks_album ON tracks (album);

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

CREATE INDEX playlist_tracks_position
    ON playlist_tracks (playlist_id, position);

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
