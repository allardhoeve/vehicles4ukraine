# Task 003: Base scraper interface

Depends on task-001.

## Goal

Define the abstract base class that all platform scrapers must implement, plus a scraper registry so the pipeline can discover and run them by name.

## Background

Each car platform needs its own scraper, but they all must speak the same language: accept search criteria, return `list[Vehicle]`. The base class enforces this contract. A registry allows the pipeline and CLI to look up scrapers by name.

## Context

- `v4u/models.py` — provides `Vehicle` dataclass

## Changes

### New: `v4u/scrapers/__init__.py`

Exports a `get_scraper(name: str) -> BaseScraper` function and a `list_scrapers() -> list[str]` function. Scrapers self-register on import.

### New: `v4u/scrapers/base.py`

**Class**: `BaseScraper(ABC)`

**Attributes**:
- `name: str` — unique identifier ("gaspedaal", "marktplaats", etc.)

**Methods**:
- `search(criteria: dict) -> list[Vehicle]` — abstract. Runs a search on the platform, returns matching vehicles.
- `__init_subclass__()` — auto-registers subclasses into the registry.

**Contract**:
- Subclasses must set `name` as a class attribute
- `search()` must return a list of `Vehicle` instances (may be empty)
- `search()` must not raise on transient errors — log and return partial results
- Each scraper handles its own HTTP session, rate limiting, and retries internally

## Tests

Add `tests/test_scraper_base.py`:

- `test_cannot_instantiate_base()` — BaseScraper is abstract
- `test_subclass_registers()` — creating a subclass with `name` makes it findable via `get_scraper()`
- `test_list_scrapers()` — lists registered scraper names
- `test_search_must_return_vehicles()` — a mock subclass returning non-Vehicle raises or is caught

## Acceptance criteria

- [ ] `BaseScraper` cannot be instantiated directly
- [ ] Subclasses auto-register by name
- [ ] `get_scraper()` and `list_scrapers()` work
- [ ] All tests pass

## Scope boundaries

- **In scope**: abstract base, registry mechanism
- **Out of scope**: any actual scraper implementations
