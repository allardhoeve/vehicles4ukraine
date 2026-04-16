# Task 002: SQLite schema and database layer

Depends on task-001.

## Goal

Create the SQLite database layer: schema, insert/upsert with deduplication, and query helpers.

## Background

All scraped vehicles funnel into a single SQLite database. Deduplication across sources is critical — the same car may appear on Gaspedaal, AutoTrack, and Marktplaats. Primary dedup key is `(source, source_id)`. Price changes should be tracked over time.

## Context

- `v4u/models.py` — provides the `Vehicle` dataclass and `to_dict()`

## Design decisions (resolved)

| Question | Decision |
|----------|----------|
| Dedup strategy | `(source, source_id)` as unique key, upsert on conflict |
| Price history | Separate `price_history` table, insert a row when price changes |
| Cross-source dedup | Later phase — license plate matching across sources |

## Changes

### New: `v4u/db.py`

**Function**: `init_db(db_path: str) -> sqlite3.Connection`
**Contract**: Creates tables if not exist, returns connection. Tables: `vehicles`, `price_history`.

**Function**: `upsert_vehicle(conn, vehicle: Vehicle) -> bool`
**Contract**: Insert or update. Returns `True` if vehicle is new or price changed. Logs price change to `price_history`.

**Function**: `get_vehicles(conn, filters: dict | None) -> list[dict]`
**Contract**: Query vehicles with optional filters (make, max_price, etc.). Returns list of dicts.

**Function**: `get_new_since(conn, since: datetime) -> list[dict]`
**Contract**: Returns vehicles first seen after `since`.

**Schema — `vehicles` table**:
- All Vehicle fields as columns
- `source, source_id` as unique constraint
- `first_seen_at`, `last_seen_at` timestamps
- `price_changed_at` — last time price changed

**Schema — `price_history` table**:
- `vehicle_source, vehicle_source_id, price, recorded_at`

## Tests

Add `tests/test_db.py`:

- `test_init_db()` — tables exist after init
- `test_insert_new_vehicle()` — vehicle inserted, returns True
- `test_upsert_same_vehicle()` — no duplicate, returns False
- `test_upsert_price_change()` — price updated, history row added, returns True
- `test_get_vehicles_filtered()` — filter by make/price works
- `test_get_new_since()` — only returns recently added

## Verification

```bash
venv/bin/python -m pytest tests/test_db.py -v
```

## Acceptance criteria

- [ ] `init_db()` creates a usable database
- [ ] Duplicate inserts are idempotent
- [ ] Price changes are tracked in `price_history`
- [ ] All tests pass

## Scope boundaries

- **In scope**: SQLite schema, CRUD operations, dedup, price history
- **Out of scope**: cross-source dedup by license plate, migrations
