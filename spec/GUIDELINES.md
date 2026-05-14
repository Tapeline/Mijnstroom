# Mijnstroom Engineering Guidelines

These guidelines are binding for every change in the repository. They derive
from `spec/MAIN.md` and `spec/BACKEND_ARCH.md` and the design decisions agreed
during planning.

## 1. Architectural layers

The codebase is organised in strict, one-directional layers under
`src/mijnstroom/`:

```
common  <- domain  <- application  <- infrastructure
                                   <- presentation
                                   <- bootstrap
```

Allowed import directions:

- `common` may import nothing from the project.
- `domain` may import from `common` only.
- `application` may import from `common` and `domain` only.
- `infrastructure` may import from `common`, `domain`, `application`.
- `presentation` may import from `common`, `domain`, `application`. It must
  not import `infrastructure` directly; concrete dependencies arrive through
  Dishka.
- `bootstrap` is the only place allowed to import every layer; it wires the
  DI container and entrypoints.

Violations of these rules are bugs.

## 2. Layer responsibilities

### common
Pure-language utilities with no I/O and no domain knowledge. Examples: id
generation, the `Clock` protocol (interface only), generic decorators,
the base `AppError` class.

### domain
Entities, value objects, domain errors and their invariants. No I/O, no
async, no third-party libraries beyond standard typing and `dataclasses`.
All domain types are immutable (`frozen=True`).

### application
Interactors and the protocols they depend on. One interactor per use case.
Interactors are composable units with explicit dependencies declared as
fields. Application code must not perform I/O directly: every side effect
goes through an injected protocol.

### infrastructure
Concrete implementations of application protocols. SQL lives here, ffmpeg
calls live here, yt-dlp calls live here, file-system access lives here.
Repositories return domain entities, never database rows.

### presentation
Litestar controllers, Jinja templates, static assets, request/response
DTOs (forms and view-models), error mapping. Controllers are thin: parse
input, call an interactor, render the result. No business logic.

### bootstrap
Configuration loading, logging setup, Dishka providers and container
construction, the `web` and `worker` entrypoints. The only layer that knows
how the others are glued together.

## 3. Decorator conventions (`common.decorators`)

```python
@entity         # frozen dataclass with slots, used for domain entities
@value_object   # frozen dataclass with slots, used for VOs
@interactor     # mutable dataclass with slots, used for interactors
@dto            # frozen dataclass with slots, used for application DTOs
```

All four are `@dataclass_transform`-annotated thin wrappers around
`dataclasses.dataclass`.

## 4. Interactor contract

An interactor:

- is decorated with `@interactor`;
- declares its dependencies as typed fields (no constructor body);
- exposes a single `async def __call__(self, dto: SomeDTO) -> SomeResult`;
- begins with `async with self.tx:` whenever it touches state;
- delegates authentication to `self.idp.require_user()` when relevant;
- raises domain or application errors only — never HTTP-specific exceptions.

Input DTOs are co-located with the interactor in
`application/<feature>/dto.py`.

## 5. Repositories

- Repositories are `Protocol` types under `application/interfaces/repos.py`.
- Methods are `@abstractmethod` and `async`.
- They speak in domain types (`Track`, `Playlist`, `Job`), not rows or dicts.
- Concrete implementations under `infrastructure/persistence/` use
  hand-written SQL through `aiosqlite`. No ORM.
- A repository receives its connection from the current `Transaction`,
  which is REQUEST-scoped in Dishka.

## 6. Transactions

- A single `Transaction` protocol exists in
  `application/interfaces/tx.py`. It is an `AsyncContextManager[None]` and
  also exposes the active connection to repositories through an internal
  accessor.
- The SQLite implementation always opens with `BEGIN IMMEDIATE` so writers
  never deadlock against readers under WAL.
- Every interactor that mutates state must be wrapped in `async with
  self.tx:`.

## 7. Persistence

- Single SQLite database file, WAL mode, `busy_timeout=5000`.
- Schema lives under `infrastructure/persistence/migrations/` as numbered
  `.sql` files. The migration runner records applied versions in a
  `schema_version` table and applies pending migrations at startup of either
  `web` or `worker`, guarded by `BEGIN IMMEDIATE` to prevent races.
- No ORM. SQL is hand-written and parameterised.

## 8. Queue and worker

- The queue is the `jobs` table plus a `QueueGateway` protocol.
- Job claim is atomic: `BEGIN IMMEDIATE; SELECT ... pending ORDER BY
  next_run_at LIMIT 1; UPDATE status='running'; COMMIT;`.
- Worker dispatch resolves the concrete handler from a
  `dict[JobKind, type[Interactor]]` registered in Dishka. Each job runs in
  its own REQUEST-scoped Dishka sub-container.
- Cancellation: web sets `status='cancelled'` only when the row is still
  `pending`. The worker checks status between long-running phases.
- Failed jobs may be deleted via a dedicated interactor that also cleans up
  any half-written files referenced in the payload.
- YouTube rate limiting is implemented purely via `next_run_at` spacing,
  using `config.youtube.interval_seconds`.

## 9. Authentication

- OIDC code-flow against Authelia using `authlib`.
- Single-user gate: the configured `allowed_sub` is the only acceptable
  `sub` claim.
- Session is a signed cookie containing the subject. `UserIdProvider`
  reads it.
- Worker uses a `SystemUserIdProvider` that returns the configured user
  unconditionally.

## 10. Configuration

- YAML config loaded by `dature` into a `Config` dataclass tree under
  `bootstrap/config.py`.
- If usage of `dature` is uncertain at code time, leave the body of
  `load_config(path) -> Config` empty per the spec instruction.
- Config is provided to Dishka at APP scope.

## 11. Dependency injection (Dishka)

- One container per process. Built in `bootstrap/di/container.py`.
- Providers under `bootstrap/di/providers.py`, grouped by concern:
  `ConfigProvider`, `InfraProvider`, `RequestProvider`, `InteractorProvider`.
- Scopes:
  - APP: `Config`, connection pool, `YoutubeClient`, `AudioConverter`,
    `FileStorage`, `Clock`.
  - REQUEST (web request or worker job): `Transaction`, repositories,
    `UserIdProvider`, all interactors.
- Controllers use `FromDishka[...]` and the `@inject` decorator from
  `dishka.integrations.litestar`.
- The worker enters REQUEST scope manually:
  `async with container() as job_container: handler = await
  job_container.get(...)`.

## 12. Error handling

- Domain and application errors derive from `common.errors.AppError`.
- `presentation/http/error_handlers.py` exposes `map_error(err) ->
  (status_code, error_code)` with a single `match` statement that all error
  branches must register in.
- The Litestar exception handler renders a minimal HTML4 error page that
  shows the error code; no stack traces in production.
- HTTP-specific exceptions (`NotFoundException`, etc.) are never raised
  from `application/`.

## 13. Frontend constraints

- HTML 4.01 Strict doctype, CSS 2.1, ECMAScript 3 (1999).
- Layout uses tables and floats. No flex, grid, transitions, shadows or
  gradients.
- All features must work without JavaScript. Forms drive every state
  transition.
- A single optional `static/enhance.js` (ES3-compatible: `var` only, no
  arrow/let/const, no `addEventListener` shortcuts that fail on legacy
  browsers) may add quality-of-life features such as the audio player on
  modern browsers. Its absence must never break a flow.
- Material Design (Google Play Music 2014 redesign, m1.material.io) is
  approximated with solid colour blocks and the GPM palette
  (orange `#FF5722` + greys). No effects requiring CSS3.

## 14. Audio handling

- Default storage format: AAC 256 kbit in `.m4a`.
- Files are content-addressed: `<data_dir>/tracks/<uuid>.<ext>`. All
  metadata lives in the database; ffmpeg rewrites embedded tags but
  filenames never change after creation.
- Album covers stored both embedded and as
  `<data_dir>/covers/<uuid>.jpg` to avoid ffprobe on list rendering.
- Streaming uses HTTP `Range`. Legacy clients that lack `<audio>` follow
  the same URL as a download.
- Format conversion for download is a `ProcessConvertJob` when the source
  format differs from the requested format and the file is large; for
  small files it may be performed inline.

## 15. YouTube ingestion

- yt-dlp drives both search and download. Default audio extraction is the
  best audio stream, transcoded to AAC 256.
- Pieces for a single video default to `info['chapters']` from yt-dlp;
  if absent, fall back to the description regex parser. The user always
  reviews and may edit pieces before submission.
- Playlist downloads enqueue one `yt_playlist_item` job per enabled entry,
  linked via `parent_job_id`.

## 16. Testing

- `domain` is tested with pure unit tests, no fakes required.
- `application` is tested with in-memory fakes that implement the
  protocols (`FakeTrackRepo`, `NullTransaction`, etc.).
- `infrastructure` is tested against a temp-file SQLite database, a
  bundled tiny WAV for ffmpeg, and canned `yt_dlp` info dicts.
- `presentation` is tested with `httpx.AsyncClient` plus a Dishka
  container in which selected providers are overridden.
- A test must fail for the right reason: avoid mocking what we own; use
  fakes built against the protocols.

## 17. Coding standards

- Python 3.13. `uv` for dependency management. `ruff` for linting and
  formatting. `mypy --strict` for type checking.
- No top-level I/O at import time. Side effects belong in the
  bootstrap entrypoints.
- Public functions and protocols carry full type annotations. `Any` is a
  smell.
- Logging is structured (`logging` with extra fields). No `print` outside
  one-off scripts.
- Commit messages: imperative mood, one logical change per commit.
- **No `__all__` declarations.** Do not write `__all__` in any module.
  Re-exports happen through explicit imports in `__init__.py` files
  (or are simply not done).
- **No `from __future__ import annotations`.** Python 3.13 is the
  minimum; PEP 604 unions and PEP 695 generics are available natively.
  Forward references that the runtime cannot resolve are written as
  string literals on a case-by-case basis.
- **No module-level docstrings.** Use inline comments or a class/function
  docstring at the first definition instead. Keep modules' top matter to
  imports only.

## 18. Performance budget

- Combined RAM (web + worker) target: 300 MB peak.
- Uvicorn runs with `--workers 1` and a bounded `--limit-concurrency`.
- Avoid loading large models or libraries at import time.
- Album-cover thumbnails are pre-generated to avoid runtime image work.

## 19. Deployment

- Single Docker image (Python 3.13-slim + ffmpeg + yt-dlp).
- `docker-compose.yml` defines two services, `web` and `worker`, sharing
  the `/data` volume and the same image, differing only in the `command`.
- Memory limits are configured per service to enforce the RAM budget.
