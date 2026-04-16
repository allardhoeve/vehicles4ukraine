# Task 006: Filters and pipeline

Depends on task-001, task-002, task-003.

## Goal

Build the filter engine (applies criteria from config to vehicles) and the pipeline that orchestrates the full flow: scrape → filter → store → notify.

## Background

The pipeline is the core orchestrator. It runs enabled scrapers, filters results against user-defined criteria, stores in the database (deduplicating), and hands new/changed vehicles to notifiers.

## Context

- `v4u/models.py` — `Vehicle` dataclass
- `v4u/db.py` — `upsert_vehicle()`, `init_db()`
- `v4u/scrapers/base.py` — `get_scraper()`, `list_scrapers()`
- `config.yaml` — criteria and scraper settings

## Changes

### New: `v4u/filters.py`

**Function**: `apply_filters(vehicles: list[Vehicle], criteria: dict) -> list[Vehicle]`

**Contract**:
- Filters vehicles by criteria from config: `max_price`, `min_year`, `max_mileage`, `fuel_types`, `makes`, `exclude_makes`
- Unknown criteria keys are ignored (forward-compatible)
- Returns subset of input list
- Empty criteria = no filtering (pass-through)

### New: `v4u/pipeline.py`

**Function**: `run(config: dict, scraper_names: list[str] | None = None) -> list[Vehicle]`

**Contract**:
- Loads config, initializes DB
- For each enabled scraper (or `scraper_names` if specified):
  1. Call `scraper.search(criteria)`
  2. Call `apply_filters(vehicles, criteria)`
  3. Call `upsert_vehicle()` for each — collect new/changed ones
  4. Call notifiers for new/changed vehicles
- Returns list of new/changed vehicles
- Logs progress: how many found, filtered, new, changed per scraper
- Catches and logs scraper errors without aborting the whole run

## Tests

Add `tests/test_filters.py`:

- `test_filter_max_price()` — filters vehicles above max price
- `test_filter_min_year()` — filters vehicles below min year
- `test_filter_fuel_types()` — only matching fuel types pass
- `test_filter_empty_criteria()` — all vehicles pass through
- `test_filter_none_fields()` — vehicles with None price/year pass through (don't exclude unknowns)

Add `tests/test_pipeline.py`:

- `test_full_pipeline()` — mock scraper, verify vehicles end up in DB
- `test_scraper_error_continues()` — one scraper fails, others still run
- `test_only_new_vehicles_notified()` — run twice, second run produces no notifications

## Acceptance criteria

- [ ] Filters correctly apply all supported criteria
- [ ] Pipeline runs all enabled scrapers
- [ ] Pipeline survives individual scraper failures
- [ ] Only new/changed vehicles trigger notifications
- [ ] All tests pass

## Scope boundaries

- **In scope**: filter engine, pipeline orchestration
- **Out of scope**: specific scraper implementations, notification delivery, enrichment
