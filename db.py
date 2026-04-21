"""Database layer for Vehicles4Ukraine."""

import json
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime

DB_PATH = os.environ.get(
    "V4U_DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "vehicles.db"),
)


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
    priority: str | None = None  # high / medium
    portals: list[dict] = field(default_factory=list)  # all portal links
    scraped_at: datetime = field(default_factory=datetime.now)

    _FIELDS = [
        "make", "model", "title", "year", "price", "mileage_km",
        "fuel", "transmission", "color", "seller", "location",
        "source_url", "image_url", "priority", "portals",
    ]

    def to_dict(self) -> dict:
        return {f: getattr(self, f) for f in self._FIELDS}

    @classmethod
    def from_dict(cls, d: dict) -> "Vehicle":
        return cls(**{f: d.get(f) for f in cls._FIELDS})


def init_db(db_path: str = DB_PATH) -> sqlite3.Connection:
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
            priority TEXT,
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
    conn.execute("""
        CREATE TABLE IF NOT EXISTS search_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT NOT NULL,
            total_found INTEGER NOT NULL,
            matches INTEGER NOT NULL,
            run_at TEXT NOT NULL
        )
    """)
    # Migrate: add missing columns
    columns = [r[1] for r in conn.execute("PRAGMA table_info(vehicles)").fetchall()]
    if "priority" not in columns:
        conn.execute("ALTER TABLE vehicles ADD COLUMN priority TEXT")
    if "gone" not in columns:
        conn.execute("ALTER TABLE vehicles ADD COLUMN gone INTEGER NOT NULL DEFAULT 0")

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
                priority, portals, first_seen_at, last_seen_at, price_at_first_seen)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (v.source_url, v.make, v.model, v.title, v.year, v.price,
             v.mileage_km, v.fuel, v.transmission, v.color,
             v.seller, v.location, v.image_url, v.priority, json.dumps(v.portals),
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
           price = ?, mileage_km = ?, last_seen_at = ?, image_url = ?, priority = ?, portals = ?,
           gone = 0
           WHERE source_url = ?""",
        (v.price, v.mileage_km, now, v.image_url, v.priority, json.dumps(v.portals), v.source_url),
    )

    if old_price != v.price:
        conn.execute(
            "INSERT INTO price_history (source_url, price, seen_at) VALUES (?, ?, ?)",
            (v.source_url, v.price, now),
        )
        return "price_changed"

    return None


def mark_gone(conn: sqlite3.Connection, seen_urls: set[str]) -> int:
    """Mark vehicles not in seen_urls as gone. Returns count of newly gone vehicles."""
    if not seen_urls:
        return 0
    placeholders = ",".join("?" for _ in seen_urls)
    cursor = conn.execute(
        f"""UPDATE vehicles SET gone = 1
            WHERE rejected = 0 AND gone = 0
            AND source_url NOT IN ({placeholders})""",
        list(seen_urls),
    )
    return cursor.rowcount


def is_rejected(conn: sqlite3.Connection, source_url: str) -> bool:
    row = conn.execute(
        "SELECT rejected FROM vehicles WHERE source_url = ?", (source_url,)
    ).fetchone()
    return row is not None and row[0] == 1
