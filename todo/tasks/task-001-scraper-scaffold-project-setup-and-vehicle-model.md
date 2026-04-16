# Task 001: Project setup and vehicle model

Independent of other tasks.

## Goal

Bootstrap the Python project structure, dependencies, and the core `Vehicle` dataclass that all scrapers output.

## Background

This is the foundation of the Vehicles4Ukraine scraper framework. Every other component depends on having a project structure and a shared vehicle data model.

## Context

- Greenfield project — empty directory
- Python + SQLite chosen as stack
- Plugin-based scraper architecture planned

## Changes

### New: `pyproject.toml`

Project metadata, dependencies, and `[project.scripts]` entry point for `v4u` CLI.

Dependencies: `httpx`, `beautifulsoup4`, `pyyaml`, `lxml`.

### New: `v4u/__init__.py`

Package init. Empty or version only.

### New: `v4u/models.py`

**Dataclass**: `Vehicle`

**Fields**:
- `source: str` — scraper name ("gaspedaal", "marktplaats", etc.)
- `source_id: str` — platform-specific unique ID
- `source_url: str` — link to the listing
- `title: str` — listing title
- `make: str | None` — brand
- `model: str | None`
- `year: int | None`
- `price: int | None` — EUR cents
- `mileage: int | None` — km
- `fuel_type: str | None`
- `license_plate: str | None`
- `apk_expiry: date | None` — filled by RDW enrichment
- `body_type: str | None`
- `engine_cc: int | None`
- `weight: int | None`
- `first_registration: date | None`
- `scraped_at: datetime` — defaults to now

**Contract**:
- Immutable after creation (frozen dataclass or similar)
- `dedup_key` property returns `(source, source_id)`
- `to_dict()` for DB serialization

### New: `config.yaml`

Default configuration file with criteria placeholders and scraper enable/disable flags.

## Tests

Add `tests/test_models.py`:

- `test_vehicle_creation()` — create a Vehicle with all fields
- `test_vehicle_defaults()` — None fields default correctly, scraped_at auto-populates
- `test_dedup_key()` — returns `(source, source_id)`
- `test_to_dict()` — serializes all fields

## Verification

```bash
pip install -e . && python -c "from v4u.models import Vehicle; print(Vehicle.__dataclass_fields__.keys())"
venv/bin/python -m pytest tests/test_models.py -v
```

## Acceptance criteria

- [ ] `pip install -e .` succeeds
- [ ] `from v4u.models import Vehicle` works
- [ ] All tests pass
- [ ] `config.yaml` exists with documented structure

## Scope boundaries

- **In scope**: project skeleton, Vehicle model, config file
- **Out of scope**: database, scrapers, CLI, pipeline
