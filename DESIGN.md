# Design

## Purpose

Scout vehicles on Dutch car selling platforms for export to Ukraine. The cars are going to the front — APK status, cosmetics, registration class don't matter. What matters: cheap, reliable, diesel, manual transmission.

## Target vehicles

Priority models:
1. Nissan Navara (pickup)
2. Mitsubishi L200 (pickup)
3. Nissan Patrol (SUV)
4. Mitsubishi Pajero (SUV)

Secondary: other pickups and SUVs, to be expanded later.

Requirements: diesel, manual shift, running and functioning, under €5,000.

## Platform landscape

| Platform | Type | Difficulty | Notes |
|---|---|---|---|
| Gaspedaal.nl | Aggregator | Easy | Covers most Dutch platforms. Data in schema.org JSON-LD. |
| AutoKopen.nl | Direct | Easy | Small, server-rendered |
| AutoTrack.nl | Direct | Medium | schema.org/Car markup |
| AutoTrader.nl | Direct | Medium | Similar to AutoTrack |
| Marktplaats.nl | Direct | Hard | Akamai bot protection |
| AutoScout24.nl | Direct | Hard | Cloudflare |
| Mobile.de | Direct | Very hard | Aggressive countermeasures |

## Architecture

**Gaspedaal as discovery layer.** It aggregates listings from most Dutch platforms. Search results include schema.org JSON-LD with structured vehicle data (make, model, year, price, mileage, fuel, transmission, seller, location). No XHR or API reverse-engineering needed — the data is server-rendered in the HTML.

URL pattern: `gaspedaal.nl/{make}/{model}` (slugs vary, e.g. `l-200` not `l200`).

Each listing has a redirect URL (`/api/proxy/redirect/vehicle/{id}`) pointing to the original listing on the source platform (AutoTrack, Marktplaats, etc.).

**Two-phase scraping:**
1. Gaspedaal discovers candidates with summary data
2. Source platform scrapers (future) follow links to get full listing text — that's where reliability signals live (maintenance history, known issues, seller description)

**Pipeline:** scrape → filter → store (SQLite) → notify

**No RDW enrichment.** Vehicle registration data (APK, body class, etc.) is irrelevant for export to a conflict zone.

## What we learned from prototyping

- Gaspedaal serves all vehicle data as schema.org/ItemList JSON-LD in `<script type="application/ld+json">` tags
- No anti-bot issues with basic HTTP requests + User-Agent header
- 2-second delay between requests seems safe; rate limit detection built in (crash with HTTP status + body)
- Transmission values are in Dutch: "Handgeschakeld" (manual), "Automaat" (automatic)
- The listing title often contains useful signals: "Export", "motor defect", etc.
- ~97 total listings across the 4 target models, ~11 match diesel + manual + <€5k criteria
