# Task 008: Log notifier

Depends on task-001.

## Goal

Build the notifier base class and a simple log/stdout notifier as the first implementation. This is the output end of the pipeline — how candidates reach humans.

## Background

The notification system is pluggable, like scrapers. For now we just log to stdout/file. Later implementations could push to Signal, email, or a webhook. The base class defines the contract.

## Context

- `v4u/models.py` — `Vehicle` dataclass
- `v4u/pipeline.py` — calls notifiers for new/changed vehicles

## Changes

### New: `v4u/notifiers/__init__.py`

Exports `get_notifier(name: str)` and `list_notifiers()`. Same registry pattern as scrapers.

### New: `v4u/notifiers/base.py`

**Class**: `BaseNotifier(ABC)`

**Attributes**:
- `name: str`

**Methods**:
- `notify(vehicles: list[Vehicle]) -> None` — abstract. Send/display the vehicles.
- `__init_subclass__()` — auto-registers.

### New: `v4u/notifiers/log.py`

**Class**: `LogNotifier(BaseNotifier)`

**Attributes**:
- `name = "log"`

**Method**: `notify(vehicles: list[Vehicle]) -> None`

**Contract**:
- Prints a formatted summary of each vehicle to stdout
- Includes: make, model, year, price, mileage, APK expiry, source URL
- Also logs to `logging` at INFO level

## Tests

Add `tests/test_notifiers.py`:

- `test_log_notifier_output()` — captures stdout, verifies vehicle info is printed
- `test_notifier_registry()` — LogNotifier is findable via `get_notifier("log")`
- `test_empty_list()` — no crash on empty vehicle list

## Acceptance criteria

- [ ] `LogNotifier` prints vehicle summaries to stdout
- [ ] Registry works
- [ ] All tests pass

## Scope boundaries

- **In scope**: base class, registry, log notifier
- **Out of scope**: Signal, email, webhook notifiers
