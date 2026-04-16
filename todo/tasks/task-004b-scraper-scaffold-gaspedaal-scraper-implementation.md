# Task 004b: Gaspedaal scraper implementation

Depends on task-001, task-003, task-004a.

## Goal

Implement the Gaspedaal scraper using the API findings from task-004a.

## Background

Gaspedaal is the first scraper and serves as the discovery layer — it finds candidates across multiple Dutch platforms. The full listing text lives on the source platform; Gaspedaal gives us enough to shortlist (price, year, mileage, make/model, source URL). Scraping source platform detail pages is a separate future task.

## Context

- `v4u/models.py` — `Vehicle` dataclass
- `v4u/scrapers/base.py` — `BaseScraper` to extend
- `docs/gaspedaal-api.md` — API documentation from task-004a
- `tests/fixtures/gaspedaal/` — sample JSON responses from task-004a

## Changes

### New: `v4u/scrapers/gaspedaal.py`

**Class**: `GaspedaalScraper(BaseScraper)`

**Attributes**:
- `name = "gaspedaal"`

**Method**: `search(criteria: dict) -> list[Vehicle]`

**Contract**:
- Translates criteria dict into Gaspedaal search parameters
- Makes HTTP requests to the XHR endpoint documented in task-004a
- Paginates through all results
- Maps JSON fields to `Vehicle` dataclass per the field mapping
- Sets `source_url` to the link pointing to the original listing on the source platform
- Rate-limits with delays between paginated requests
- Returns empty list on failure, logs errors
- Returns partial results on transient errors

## Tests

Add `tests/test_gaspedaal.py`:

- `test_parse_listing()` — given fixture JSON, correctly maps to Vehicle
- `test_pagination()` — handles multi-page results with mocked responses
- `test_empty_results()` — returns empty list, no crash
- `test_criteria_to_params()` — criteria dict maps to correct URL params
- `test_rate_limiting()` — requests are spaced apart

Uses fixture files from task-004a — no live site calls in tests.

## Verification

```bash
venv/bin/python -m pytest tests/test_gaspedaal.py -v
# Manual: test against live site
venv/bin/python -c "from v4u.scrapers.gaspedaal import GaspedaalScraper; results = GaspedaalScraper().search({'make': 'toyota', 'max_price': 500000}); print(f'{len(results)} vehicles found'); print(results[0] if results else 'none')"
```

## Pitfalls

- XHR endpoint may require specific headers to avoid 403s
- JSON structure may change — keep parsing defensive
- Gaspedaal may not expose license plates in summary data
- Source URLs may use redirects — store the final destination URL if possible

## Acceptance criteria

- [ ] `GaspedaalScraper` registers as "gaspedaal"
- [ ] Parses fixture JSON correctly into Vehicle instances
- [ ] Paginates through results
- [ ] Handles errors gracefully
- [ ] All tests pass

## Scope boundaries

- **In scope**: Gaspedaal search, JSON parsing, pagination
- **Out of scope**: following source URLs to scrape detail pages, enrichment
