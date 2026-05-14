# Mijnstroom

Self-hosted music storage and streaming service. See `spec/` for design and
implementation details.

## Quick start

```sh
uv sync
uv run python -m mijnstroom.bootstrap.main
```

## Development

```sh
uv sync --all-groups
uv run pytest
uv run ruff check
uv run mypy src/mijnstroom
```
