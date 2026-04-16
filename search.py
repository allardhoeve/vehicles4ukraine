#!/usr/bin/env python3
"""Gaspedaal.nl vehicle searcher.

Searches for target make/model combinations, extracts vehicle listings
from Next.js RSC payload embedded in the page. This gives us richer data
than the schema.org JSON-LD, including working click-through URLs.

Crashes with full HTTP details on rate limiting or unexpected responses.
"""

import json
import os
import re
import sqlite3
import sys
import time
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime


# --- Configuration ---

TARGETS = [
    ("nissan", "navara"),
    ("mitsubishi", "l-200"),
    ("nissan", "patrol"),
    ("mitsubishi", "pajero"),
]

MAX_PRICE = 5000  # EUR
FUEL_TYPE = "DIESEL"
TRANSMISSION = "HANDMATIG"

DELAY_BETWEEN_REQUESTS = 2  # seconds

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vehicles.db")

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


# --- Data ---

@dataclass
class Vehicle:
    make: str
    model: str
    title: str
    year: int | None
    price: int | None
    mileage_km: int | None
    fuel: str | None
    transmission: str | None
    color: str | None
    seller: str | None
    location: str | None
    source_url: str | None  # click-through to actual listing
    image_url: str | None = None
    portals: list[dict] = field(default_factory=list)  # all portal links
    scraped_at: datetime = field(default_factory=datetime.now)


# --- HTTP ---

class RateLimitError(Exception):
    """Raised when we get an unexpected HTTP response."""

    def __init__(self, url, status_code, body):
        self.url = url
        self.status_code = status_code
        self.body = body
        super().__init__(
            f"HTTP {status_code} from {url}\n"
            f"Body ({len(body)} bytes):\n{body[:2000]}"
        )


def fetch(url: str) -> str:
    """Fetch a URL. Crash with details on non-200 responses."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RateLimitError(url, e.code, body) from None


# --- Parsing ---

def extract_occasions(html: str) -> list[dict]:
    """Extract the occasions array from the Next.js RSC payload."""
    chunks = re.findall(
        r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', html, re.DOTALL
    )
    for chunk in chunks:
        if r'\"occasions\"' not in chunk:
            continue

        unescaped = chunk.encode().decode("unicode_escape")
        occ_start = unescaped.find('"occasions":')
        if occ_start < 0:
            continue

        s = unescaped[occ_start + len('"occasions":'):]
        depth = 0
        for j, c in enumerate(s):
            if c == "[":
                depth += 1
            elif c == "]":
                depth -= 1
            if depth == 0:
                return json.loads(s[: j + 1])

    return []


def occasion_to_vehicle(occ: dict) -> Vehicle:
    """Convert a Gaspedaal occasion dict to a Vehicle."""
    auto = occ.get("autogegevens", {})
    alg = auto.get("algemeen", {})
    gesch = auto.get("geschiedenis", {})
    aanbieder = occ.get("aanbieder", {})
    gegevens = aanbieder.get("aanbiedergegevens", {})
    portalen = occ.get("portalen", [])
    fotos = occ.get("gpFotos", {})
    image_url = fotos.get("fotoXl") or fotos.get("fotoGroot") or fotos.get("fotoOrigineel")

    # Price: take the lowest across portals, or the first one
    prices = [p["prijs"] for p in portalen if p.get("prijs")]
    price = min(prices) if prices else None

    # Pick best source URL: prefer AutoTrack/Marktplaats over dealer sites
    preferred = ["AutoTrack", "Marktplaats", "AutoScout24", "ANWB"]
    source_url = None
    for pref in preferred:
        for p in portalen:
            if p.get("portaalBeschrijving") == pref:
                source_url = p.get("klikUrl")
                break
        if source_url:
            break
    if not source_url and portalen:
        source_url = portalen[0].get("klikUrl")

    return Vehicle(
        make=alg.get("merknaam", ""),
        model=alg.get("modelnaam", ""),
        title=f"{alg.get('merknaam', '')} {alg.get('modelnaam', '')} - {alg.get('uitvoering', '')}",
        year=gesch.get("bouwjaar"),
        price=price,
        mileage_km=gesch.get("kilometerstand"),
        fuel=alg.get("brandstofsoort"),
        transmission=alg.get("transmissietype"),
        color=alg.get("kleur"),
        seller=gegevens.get("naamsvermelding") or gegevens.get("naam"),
        location=gegevens.get("plaatsnaam"),
        source_url=source_url,
        image_url=image_url,
        portals=[
            {"name": p.get("portaalBeschrijving"), "url": p.get("klikUrl")}
            for p in portalen
        ],
    )


def parse_vehicles(html: str) -> list[Vehicle]:
    """Extract vehicles from Gaspedaal page HTML."""
    occasions = extract_occasions(html)
    return [occasion_to_vehicle(occ) for occ in occasions]


# --- Database ---

def init_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vehicles (
            source_url TEXT PRIMARY KEY,
            make TEXT,
            model TEXT,
            title TEXT,
            year INTEGER,
            price INTEGER,
            mileage_km INTEGER,
            fuel TEXT,
            transmission TEXT,
            color TEXT,
            seller TEXT,
            location TEXT,
            image_url TEXT,
            portals TEXT,
            first_seen_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            price_at_first_seen INTEGER,
            rejected INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            source_url TEXT NOT NULL,
            price INTEGER,
            seen_at TEXT NOT NULL,
            FOREIGN KEY (source_url) REFERENCES vehicles(source_url)
        )
    """)
    conn.commit()
    return conn


def upsert_vehicle(conn: sqlite3.Connection, v: Vehicle) -> str | None:
    """Insert or update a vehicle. Returns 'new', 'price_changed', or None."""
    now = datetime.now().isoformat()

    row = conn.execute(
        "SELECT price, first_seen_at FROM vehicles WHERE source_url = ?",
        (v.source_url,),
    ).fetchone()

    if row is None:
        conn.execute(
            """INSERT INTO vehicles
               (source_url, make, model, title, year, price, mileage_km,
                fuel, transmission, color, seller, location, image_url,
                portals, first_seen_at, last_seen_at, price_at_first_seen)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (v.source_url, v.make, v.model, v.title, v.year, v.price,
             v.mileage_km, v.fuel, v.transmission, v.color,
             v.seller, v.location, v.image_url, json.dumps(v.portals),
             now, now, v.price),
        )
        conn.execute(
            "INSERT INTO price_history (source_url, price, seen_at) VALUES (?, ?, ?)",
            (v.source_url, v.price, now),
        )
        return "new"

    old_price = row[0]
    conn.execute(
        """UPDATE vehicles SET
           price = ?, mileage_km = ?, last_seen_at = ?, image_url = ?, portals = ?
           WHERE source_url = ?""",
        (v.price, v.mileage_km, now, v.image_url, json.dumps(v.portals), v.source_url),
    )

    if old_price != v.price:
        conn.execute(
            "INSERT INTO price_history (source_url, price, seen_at) VALUES (?, ?, ?)",
            (v.source_url, v.price, now),
        )
        return "price_changed"

    return None


def is_rejected(conn: sqlite3.Connection, source_url: str) -> bool:
    row = conn.execute(
        "SELECT rejected FROM vehicles WHERE source_url = ?", (source_url,)
    ).fetchone()
    return row is not None and row[0] == 1


# --- Filtering ---

def matches_criteria(v: Vehicle) -> bool:
    if v.price is not None and v.price > MAX_PRICE:
        return False
    if FUEL_TYPE and v.fuel != FUEL_TYPE:
        return False
    if TRANSMISSION and v.transmission != TRANSMISSION:
        return False
    return True


# --- Main ---

def main():
    conn = init_db(DB_PATH)
    all_matches = []

    for i, (make, model) in enumerate(TARGETS):
        if i > 0:
            time.sleep(DELAY_BETWEEN_REQUESTS)

        url = f"https://www.gaspedaal.nl/{make}/{model}"
        print(f"[{i+1}/{len(TARGETS)}] {make}/{model} ... ", end="", flush=True)

        html = fetch(url)  # crashes on non-200
        vehicles = parse_vehicles(html)
        matches = [v for v in vehicles if matches_criteria(v)]

        print(f"{len(vehicles)} found, {len(matches)} match criteria")
        all_matches.extend(matches)

    # Store and detect changes
    new_vehicles = []
    price_changes = []
    seen_again = 0

    for v in all_matches:
        if not v.source_url:
            continue
        # Skip rejected vehicles
        if is_rejected(conn, v.source_url):
            continue
        result = upsert_vehicle(conn, v)
        if result == "new":
            new_vehicles.append(v)
        elif result == "price_changed":
            price_changes.append(v)
        else:
            seen_again += 1

    conn.commit()

    # Report
    total_in_db = conn.execute("SELECT COUNT(*) FROM vehicles").fetchone()[0]
    rejected_count = conn.execute(
        "SELECT COUNT(*) FROM vehicles WHERE rejected = 1"
    ).fetchone()[0]

    print(f"\n{'='*70}")
    print(f"  {len(all_matches)} matched criteria | {len(new_vehicles)} NEW | "
          f"{len(price_changes)} price changed | {seen_again} seen before")
    print(f"  DB total: {total_in_db} vehicles ({rejected_count} rejected)")
    print(f"{'='*70}")

    if new_vehicles:
        print(f"\n  NEW VEHICLES:\n")
        for v in sorted(new_vehicles, key=lambda x: x.price or 99999):
            print(
                f"  EUR {v.price:>7,}  {v.year}  {v.mileage_km:>7,}km  "
                f"{v.make} {v.model}  [{v.location}]"
            )
            print(f"           {v.title}")
            print(f"           {v.source_url}")
            print()

    if price_changes:
        print(f"\n  PRICE CHANGES:\n")
        for v in price_changes:
            history = conn.execute(
                "SELECT price, seen_at FROM price_history WHERE source_url = ? ORDER BY seen_at",
                (v.source_url,),
            ).fetchall()
            old_price = history[-2][0] if len(history) >= 2 else "?"
            print(
                f"  EUR {old_price:>7,} -> {v.price:>7,}  "
                f"{v.make} {v.model}  [{v.location}]"
            )
            print(f"           {v.source_url}")
            print()

    if not new_vehicles and not price_changes:
        print("\n  No changes since last run.\n")

    conn.close()


def cmd_reject(source_url: str):
    """Mark a vehicle as rejected so it won't show up again."""
    conn = init_db(DB_PATH)
    conn.execute("UPDATE vehicles SET rejected = 1 WHERE source_url = ?", (source_url,))
    if conn.total_changes == 0:
        print(f"Vehicle not found: {source_url}")
    else:
        row = conn.execute(
            "SELECT make, model, title FROM vehicles WHERE source_url = ?",
            (source_url,),
        ).fetchone()
        print(f"Rejected: {row[0]} {row[1]} - {row[2]}")
    conn.commit()
    conn.close()


def cmd_list():
    """List all active (non-rejected) vehicles in the database."""
    conn = init_db(DB_PATH)
    rows = conn.execute(
        """SELECT make, model, title, year, price, mileage_km, location, source_url, first_seen_at
           FROM vehicles WHERE rejected = 0 ORDER BY price""",
    ).fetchall()
    print(f"{len(rows)} active vehicles in database:\n")
    for r in rows:
        make, model, title, year, price, km, loc, url, first_seen = r
        print(f"  EUR {price:>7,}  {year}  {km:>7,}km  {make} {model}  [{loc}]")
        print(f"           {title}")
        print(f"           {url}")
        print(f"           (first seen: {first_seen[:10]})")
        print()
    conn.close()


if __name__ == "__main__":
    try:
        if len(sys.argv) > 1 and sys.argv[1] == "reject":
            if len(sys.argv) < 3:
                print("Usage: search.py reject <source_url>")
                sys.exit(1)
            cmd_reject(sys.argv[2])
        elif len(sys.argv) > 1 and sys.argv[1] == "list":
            cmd_list()
        else:
            main()
    except RateLimitError as e:
        print(f"\n\nRATE LIMITED / BLOCKED\n", file=sys.stderr)
        print(str(e), file=sys.stderr)
        sys.exit(1)
