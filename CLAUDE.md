# CLAUDE.md

## Project

Vehicle scouting system that crawls Dutch car platforms to find cheap, reliable vehicles for export to Ukraine.

## Tooling

- Python package/venv management: always use `uv` (not pip, not venv)
  - `uv init`, `uv add <package>`, `uv run python ...`
- Tasks/planning: `todo/tasks/` directory, follow `task-template.md`

## Running locally

```bash
uv run python search.py        # Run scraper once
uv run python search.py list    # List active vehicles in DB
uv run python search.py reject <url>  # Reject a vehicle
uv run python web.py            # Dev web server on :5001
```

## Docker

```bash
docker compose up web -d                        # Web UI on :5001
docker compose run --rm search                  # Run scraper once
```

Both services share a `/data` volume for `vehicles.db`. The `V4U_DB_PATH` env var controls DB location.
