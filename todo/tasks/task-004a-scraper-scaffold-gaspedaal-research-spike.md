# Task 004a: Gaspedaal reverse-engineering research spike

Depends on nothing. Independent research task.

## Goal

Reverse-engineer Gaspedaal.nl's XHR/JSON endpoints to document everything needed to build a scraper: URLs, parameters, headers, JSON response structure, and pagination.

## Background

Gaspedaal.nl is a Dutch car listing aggregator. Its search results load via XHR returning JSON, making it a good scraping target. Before implementing the scraper we need to understand the API surface.

## Context

- Gaspedaal aggregates from AutoTrack, AutoTrader, AutoScout24, and others
- URL pattern: `gaspedaal.nl/[merk]/[model]`
- Summary data only: price, year, mileage, make/model, thumbnail, source URL
- Full listing details (including description text) are on the source platform

## Changes

### New: `docs/gaspedaal-api.md`

Document the following:

- **Search endpoint**: exact URL, HTTP method
- **Request headers**: required headers (User-Agent, Referer, cookies, auth tokens)
- **Query parameters**: how to filter by make, model, price range, year, mileage, fuel type
- **Pagination**: mechanism (offset, page, cursor), page size, max results
- **Response JSON structure**: annotated example response with field descriptions
- **Field mapping**: which JSON fields map to our Vehicle model fields
- **Rate limiting**: observed limits, recommended delays
- **Anti-bot**: what protections exist, what triggers blocks
- **Source URL format**: how to extract the link to the original listing

## Verification

- Sample `curl` commands that return valid JSON responses
- At least 3 example responses saved as test fixtures in `tests/fixtures/gaspedaal/`

## Acceptance criteria

- [ ] Endpoint URL and parameters are documented
- [ ] JSON response structure is annotated
- [ ] Field mapping to Vehicle model is defined
- [ ] Sample fixtures saved for use in task-004b tests
- [ ] curl commands verified working

## Scope boundaries

- **In scope**: Gaspedaal API research and documentation
- **Out of scope**: implementation, scraping source platform detail pages
