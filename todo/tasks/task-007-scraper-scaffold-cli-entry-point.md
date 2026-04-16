# Task 007: CLI entry point

Depends on task-006.

## Goal

Create the CLI that serves as the main entry point. Cron calls this. Humans call this.

## Background

The CLI is how the pipeline gets invoked — either manually or via cron on the VPS. It needs to load config, run the pipeline, and provide basic querying of stored vehicles.

## Context

- `v4u/pipeline.py` — `run()` function
- `v4u/db.py` — `get_vehicles()`, `init_db()`
- `config.yaml` — configuration file

## Changes

### New: `v4u/cli.py`

Uses `argparse` (no extra dependencies).

**Commands**:

- `python -m v4u run` — run all enabled scrapers through the pipeline
  - `--scraper NAME` — run only this scraper
  - `--config PATH` — config file path (default: `config.yaml`)
  - `--db PATH` — database path (default: `vehicles.db`)
- `python -m v4u list` — list stored vehicles
  - `--make MAKE` — filter by make
  - `--max-price N` — filter by max price
  - `--new` — only vehicles from last run
  - `--format {table,json}` — output format (default: table)
- `python -m v4u scrapers` — list available and enabled scrapers

### New: `v4u/__main__.py`

Enables `python -m v4u`. Calls `cli.main()`.

## Tests

Add `tests/test_cli.py`:

- `test_run_command()` — invokes run with a mock pipeline, no crash
- `test_list_command()` — lists vehicles from a pre-populated DB
- `test_scrapers_command()` — lists registered scrapers

## Acceptance criteria

- [ ] `python -m v4u run` executes the pipeline
- [ ] `python -m v4u list` shows stored vehicles
- [ ] `--scraper` flag limits to one scraper
- [ ] All tests pass

## Scope boundaries

- **In scope**: CLI, argument parsing, command dispatch
- **Out of scope**: daemon mode, web interface
