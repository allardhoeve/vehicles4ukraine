#!/usr/bin/env python3
"""Web UI for browsing and managing scouted vehicles."""

import json
import os
import sqlite3

from functools import wraps

from flask import Flask, Response, g, jsonify, redirect, render_template_string, request, url_for

DB_PATH = os.environ.get(
    "V4U_DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "vehicles.db"),
)

API_USER = os.environ.get("V4U_API_USER", "v4u")
API_PASS = os.environ.get("V4U_API_PASS", "")

app = Flask(__name__)
app.jinja_env.filters["dotfmt"] = lambda v: f"{v:,}".replace(",", ".") if v else "0"


def require_api_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not API_PASS or not auth or auth.username != API_USER or auth.password != API_PASS:
            return Response("Unauthorized", 401, {"WWW-Authenticate": 'Basic realm="v4u"'})
        return f(*args, **kwargs)
    return decorated

TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Vehicles4Ukraine</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, system-ui, sans-serif; background: #0f1419; color: #e0e0e0; padding: 1rem; }
  h1 { margin-bottom: .5rem; color: #ffd700; }
  .stats { color: #888; margin-bottom: 1rem; font-size: .9rem; }
  .filters { margin-bottom: 1rem; display: flex; gap: .5rem; flex-wrap: wrap; }
  .filters a { padding: .3rem .7rem; background: #1a2332; border: 1px solid #2a3a4a; border-radius: 4px;
               color: #aaa; text-decoration: none; font-size: .85rem; }
  .filters a.active { background: #1a3a5a; border-color: #3a6a9a; color: #fff; }
  .vehicle { background: #1a2332; border: 1px solid #2a3a4a; border-radius: 8px; padding: 1rem;
             margin-bottom: .75rem; display: flex; align-items: flex-start; gap: 1rem; }
  .vehicle img { width: 180px; height: 120px; object-fit: cover; border-radius: 6px; flex-shrink: 0; }
  .vehicle.new { border-left: 3px solid #4caf50; }
  .vehicle.price-changed { border-left: 3px solid #ff9800; }
  .info { flex: 1; }
  .info h3 { font-size: 1rem; margin-bottom: .3rem; }
  .info h3 a { color: #5dade2; text-decoration: none; }
  .info h3 a:hover { text-decoration: underline; }
  .meta { font-size: .85rem; color: #999; display: flex; flex-wrap: wrap; gap: .3rem 1rem; }
  .meta a.location { color: inherit; text-decoration: underline; }
  .meta .price { color: #4caf50; font-weight: bold; font-size: 1.1rem; }
  .meta .tag { background: #2a3a4a; padding: .1rem .4rem; border-radius: 3px; }
  .actions { display: flex; flex-direction: column; gap: .3rem; flex-shrink: 0; }
  .btn { padding: .4rem .8rem; border: none; border-radius: 4px; cursor: pointer; font-size: .8rem; }
  .btn-reject { background: #5a2a2a; color: #ff6b6b; }
  .btn-reject:hover { background: #7a3a3a; }
  .btn-undo { background: #2a3a2a; color: #6bff6b; }
  .btn-undo:hover { background: #3a5a3a; }
  .portals { font-size: .8rem; margin-top: .3rem; }
  .portals a { color: #5dade2; margin-right: .8rem; text-decoration: none; }
  .portals a:hover { text-decoration: underline; }
  .price-history { font-size: .8rem; color: #ff9800; margin-top: .2rem; }
  .empty { text-align: center; color: #666; padding: 3rem; }
  .first-seen { font-size: .75rem; color: #666; }
  .priority { padding: .1rem .4rem; border-radius: 3px; font-size: .75rem; font-weight: bold; }
  .priority-high { background: #2a4a2a; color: #4caf50; }
  .priority-medium { background: #3a3a1a; color: #ff9800; }
</style>
</head>
<body>
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:.5rem;">
  <h1>&#x1f1fa;&#x1f1e6; Vehicles4Ukraine</h1>
  <a href="/criteria" style="padding:.4rem .8rem; background:#1a3a5a; border:1px solid #3a6a9a; border-radius:4px; color:#fff; text-decoration:none; font-size:.85rem;">Search criteria</a>
</div>
<div class="stats">
  {{ vehicles|length }} vehicle{{ 's' if vehicles|length != 1 }} shown
  &middot; {{ total }} total in DB
  &middot; {{ rejected_count }} rejected
  {% if last_search %}
  &middot; Last search: {{ last_search.run_at }} &mdash; {{ last_search.total_found|dotfmt }} found, {{ last_search.matches }} matched
  {% endif %}
</div>

<div class="filters">
  <a href="?show=active" class="{{ 'active' if show == 'active' }}">Active</a>
  <a href="?show=new" class="{{ 'active' if show == 'new' }}">New today</a>
  <a href="?show=rejected" class="{{ 'active' if show == 'rejected' }}">Rejected</a>
  <a href="?show=all" class="{{ 'active' if show == 'all' }}">All</a>
</div>

{% if not vehicles %}
<div class="empty">No vehicles to show.</div>
{% endif %}

{% for v in vehicles %}
<div class="vehicle {{ 'new' if v.is_new else '' }} {{ 'price-changed' if v.price_changed else '' }}">
  {% if v.image_url %}
  <a href="{{ v.source_url }}" target="_blank"><img src="{{ v.image_url }}" alt="{{ v.title }}"></a>
  {% endif %}
  <div class="info">
    <h3><a href="{{ v.source_url }}" target="_blank">{{ v.title }}</a></h3>
    <div class="meta">
      <span class="price">&euro; {{ v.price|dotfmt }}</span>
      <span>{{ v.year }}</span>
      <span>{{ v.mileage_km|dotfmt }} km</span>
      <span class="tag">{{ v.fuel }}</span>
      <span class="tag">{{ v.transmission }}</span>
      {% if v.priority %}<span class="priority priority-{{ v.priority }}">{{ v.priority }}</span>{% endif %}
      {% if v.color %}<span>{{ v.color }}</span>{% endif %}
      {% if v.seller and v.location %}<span>{{ v.seller }}, <a class="location" href="https://www.google.com/maps/dir/?api=1&destination={{ v.location | urlencode }},Netherlands" target="_blank">&#x1F4CD; {{ v.location }}</a></span>
      {% elif v.seller %}<span>{{ v.seller }}</span>
      {% elif v.location %}<span><a class="location" href="https://www.google.com/maps/dir/?api=1&destination={{ v.location | urlencode }},Netherlands" target="_blank">&#x1F4CD; {{ v.location }}</a></span>{% endif %}
    </div>
    <div class="portals">
      {% for p in v.portals %}
        <a href="{{ p.url }}" target="_blank">{{ p.name }}</a>
      {% endfor %}
    </div>
    {% if v.price_history|length > 1 %}
    <div class="price-history">
      Price: {% for ph in v.price_history %}&euro;{{ ph[0]|dotfmt }} ({{ ph[1][:10] }}){{ ' &rarr; ' if not loop.last }}{% endfor %}
    </div>
    {% endif %}
    <div class="first-seen">First seen: {{ v.first_seen[:10] }}</div>
  </div>
  <div class="actions">
    {% if v.rejected %}
    <form method="POST" action="/unreject">
      <input type="hidden" name="source_url" value="{{ v.source_url }}">
      <button class="btn btn-undo" type="submit">Undo</button>
    </form>
    {% else %}
    <form method="POST" action="/reject">
      <input type="hidden" name="source_url" value="{{ v.source_url }}">
      <button class="btn btn-reject" type="submit">Reject</button>
    </form>
    {% endif %}
  </div>
</div>
{% endfor %}
</body>
</html>
"""


CRITERIA_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Search Criteria — Vehicles4Ukraine</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, system-ui, sans-serif; background: #0f1419; color: #e0e0e0; padding: 1rem; max-width: 800px; margin: 0 auto; }
  h1 { margin-bottom: .5rem; color: #ffd700; }
  h2 { color: #5dade2; margin: 1.5rem 0 .5rem; font-size: 1.1rem; }
  h3 { color: #ccc; margin: 1rem 0 .4rem; font-size: .95rem; }
  p, li { line-height: 1.5; color: #bbb; font-size: .9rem; }
  ul { margin-left: 1.2rem; margin-bottom: .5rem; }
  table { width: 100%; border-collapse: collapse; margin-bottom: 1rem; font-size: .85rem; }
  th { text-align: left; padding: .4rem .6rem; background: #1a2332; color: #aaa; border-bottom: 1px solid #2a3a4a; }
  td { padding: .4rem .6rem; border-bottom: 1px solid #1a2332; }
  .back { display: inline-block; margin-bottom: 1rem; padding: .4rem .8rem; background: #1a3a5a; border: 1px solid #3a6a9a;
          border-radius: 4px; color: #fff; text-decoration: none; font-size: .85rem; }
  .back:hover { background: #2a4a6a; }
  .tag-high { color: #4caf50; }
  .tag-med { color: #ff9800; }
  .tag-skip { color: #888; }
  td.num { text-align: right; font-variant-numeric: tabular-nums; }
</style>
</head>
<body>
<a href="/" class="back">&larr; Back to vehicles</a>
<h1>&#x1f1fa;&#x1f1e6; Search Criteria</h1>

<h2>What we're looking for</h2>
<ul>
  <li><strong>Pickup trucks</strong> — like the Mitsubishi L200</li>
  <li><strong>Off-road SUVs</strong> — Eastern Ukraine doesn't have good roads</li>
  <li><strong>Diesel</strong>, manual transmission</li>
  <li><strong>Easy to repair</strong> with good parts availability in Eastern Europe</li>
  <li>Max price: <strong>&euro;5,000</strong></li>
</ul>

<h2>Currently searching</h2>

<h3 class="tag-high">High priority</h3>
<table>
  <tr><th>Model</th><th>Type</th><th>Notes</th><th>Found</th><th>Matched</th></tr>
  <tr><td>Toyota Hilux</td><td>Pickup</td><td>Gold standard for conflict/aid zones. Indestructible.</td><td>{{ stats.get('toyota/hilux', {}).get('total_found', '—') }}</td><td>{{ stats.get('toyota/hilux', {}).get('matches', '—') }}</td></tr>
  <tr><td>Toyota Land Cruiser</td><td>SUV</td><td>The UN/NGO vehicle of choice. 70/80/100 series legendary.</td><td>{{ stats.get('toyota/land-cruiser', {}).get('total_found', '—') }}</td><td>{{ stats.get('toyota/land-cruiser', {}).get('matches', '—') }}</td></tr>
  <tr><td>Ford Ranger</td><td>Pickup</td><td>Very common in NL, good chance under &euro;5,000.</td><td>{{ stats.get('ford/ranger', {}).get('total_found', '—') }}</td><td>{{ stats.get('ford/ranger', {}).get('matches', '—') }}</td></tr>
</table>

<h3 class="tag-med">Medium priority</h3>
<table>
  <tr><th>Model</th><th>Type</th><th>Notes</th><th>Found</th><th>Matched</th></tr>
  <tr><td>Nissan Navara</td><td>Pickup</td><td>Solid workhorse, good diesel engines</td><td>{{ stats.get('nissan/navara', {}).get('total_found', '—') }}</td><td>{{ stats.get('nissan/navara', {}).get('matches', '—') }}</td></tr>
  <tr><td>Mitsubishi L200</td><td>Pickup</td><td>Very common, parts widely available</td><td>{{ stats.get('mitsubishi/l-200', {}).get('total_found', '—') }}</td><td>{{ stats.get('mitsubishi/l-200', {}).get('matches', '—') }}</td></tr>
  <tr><td>Nissan Patrol</td><td>SUV</td><td>Legendary off-road, older models affordable</td><td>{{ stats.get('nissan/patrol', {}).get('total_found', '—') }}</td><td>{{ stats.get('nissan/patrol', {}).get('matches', '—') }}</td></tr>
  <tr><td>Mitsubishi Pajero</td><td>SUV</td><td>Capable off-roader, good parts availability</td><td>{{ stats.get('mitsubishi/pajero', {}).get('total_found', '—') }}</td><td>{{ stats.get('mitsubishi/pajero', {}).get('matches', '—') }}</td></tr>
  <tr><td>Kia Sorento</td><td>SUV</td><td>Budget-friendly, decent off-road</td><td>{{ stats.get('kia/sorento', {}).get('total_found', '—') }}</td><td>{{ stats.get('kia/sorento', {}).get('matches', '—') }}</td></tr>
  <tr><td>Hyundai Terracan</td><td>SUV</td><td>Cheap, shares Mitsubishi drivetrain parts</td><td>{{ stats.get('hyundai/terracan', {}).get('total_found', '—') }}</td><td>{{ stats.get('hyundai/terracan', {}).get('matches', '—') }}</td></tr>
  <tr><td>Isuzu D-Max</td><td>Pickup</td><td>Underrated workhorse, potentially cheaper</td><td>{{ stats.get('isuzu/d-max', {}).get('total_found', '—') }}</td><td>{{ stats.get('isuzu/d-max', {}).get('matches', '—') }}</td></tr>
</table>

<h3 class="tag-skip">Skipped</h3>
<table>
  <tr><th>Model</th><th>Type</th><th>Why skipped</th></tr>
  <tr><td>Land Rover Defender</td><td>SUV</td><td>Capable but expensive to maintain, electrical issues</td></tr>
  <tr><td>Isuzu Trooper</td><td>SUV</td><td>Too old, parts availability declining</td></tr>
  <tr><td>Suzuki Jimny</td><td>SUV</td><td>Too small for hauling supplies</td></tr>
</table>

</body>
</html>
"""


def get_db():
    if "db" not in g:
        from search import init_db
        g.db = init_db(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


@app.route("/")
def index():
    db = get_db()
    show = request.args.get("show", "active")

    if show == "rejected":
        where = "WHERE rejected = 1"
    elif show == "new":
        where = "WHERE rejected = 0 AND date(first_seen_at) = date('now')"
    elif show == "all":
        where = ""
    else:
        where = "WHERE rejected = 0"

    rows = db.execute(
        f"SELECT * FROM vehicles {where} ORDER BY price"
    ).fetchall()

    total = db.execute("SELECT COUNT(*) FROM vehicles").fetchone()[0]
    rejected_count = db.execute("SELECT COUNT(*) FROM vehicles WHERE rejected = 1").fetchone()[0]

    vehicles = []
    for row in rows:
        portals = json.loads(row["portals"]) if row["portals"] else []
        price_history = db.execute(
            "SELECT price, seen_at FROM price_history WHERE source_url = ? ORDER BY seen_at",
            (row["source_url"],),
        ).fetchall()

        vehicles.append({
            "source_url": row["source_url"],
            "make": row["make"],
            "model": row["model"],
            "title": row["title"],
            "year": row["year"],
            "price": row["price"] or 0,
            "mileage_km": row["mileage_km"] or 0,
            "fuel": row["fuel"],
            "transmission": row["transmission"],
            "color": row["color"],
            "seller": row["seller"],
            "location": row["location"],
            "image_url": row["image_url"] if "image_url" in row.keys() else None,
            "priority": row["priority"] if "priority" in row.keys() else None,
            "portals": portals,
            "rejected": row["rejected"],
            "first_seen": row["first_seen_at"],
            "is_new": row["first_seen_at"][:10] == __import__("datetime").date.today().isoformat(),
            "price_changed": row["price_at_first_seen"] is not None and row["price"] != row["price_at_first_seen"],
            "price_history": [(ph[0], ph[1]) for ph in price_history],
        })

    # Last search run summary
    last_run = db.execute("""
        SELECT SUM(total_found), SUM(matches), MAX(run_at)
        FROM search_runs
        WHERE run_at = (SELECT MAX(run_at) FROM search_runs)
    """).fetchone()
    last_search = None
    if last_run and last_run[2]:
        last_search = {
            "total_found": last_run[0],
            "matches": last_run[1],
            "run_at": last_run[2][:16].replace("T", " "),
        }

    return render_template_string(TEMPLATE, vehicles=vehicles, total=total,
                                  rejected_count=rejected_count, show=show,
                                  last_search=last_search)


@app.route("/criteria")
def criteria():
    db = get_db()
    # Per-model stats from last run
    run_stats = db.execute("""
        SELECT slug, total_found, matches
        FROM search_runs
        WHERE run_at = (SELECT MAX(run_at) FROM search_runs)
    """).fetchall()
    stats_by_slug = {r[0]: {"total_found": r[1], "matches": r[2]} for r in run_stats}
    return render_template_string(CRITERIA_TEMPLATE, stats=stats_by_slug)


@app.route("/reject", methods=["POST"])
def reject():
    db = get_db()
    source_url = request.form["source_url"]
    db.execute("UPDATE vehicles SET rejected = 1 WHERE source_url = ?", (source_url,))
    db.commit()
    return redirect(request.referrer or url_for("index"))


@app.route("/unreject", methods=["POST"])
def unreject():
    db = get_db()
    source_url = request.form["source_url"]
    db.execute("UPDATE vehicles SET rejected = 0 WHERE source_url = ?", (source_url,))
    db.commit()
    return redirect(request.referrer or url_for("index"))


@app.route("/api/vehicles", methods=["POST"])
@require_api_auth
def api_vehicles():
    """Accept vehicles from a remote search process."""
    from search import init_db, upsert_vehicle, is_rejected, Vehicle

    data = request.get_json()
    if not data or "vehicles" not in data:
        return jsonify({"error": "missing 'vehicles' key"}), 400

    db = get_db()
    new_count = 0
    changed_count = 0
    skipped = 0

    for v_data in data["vehicles"]:
        v = Vehicle.from_dict(v_data)
        if not v.source_url:
            continue
        if is_rejected(db, v.source_url):
            skipped += 1
            continue
        result = upsert_vehicle(db, v)
        if result == "new":
            new_count += 1
        elif result == "price_changed":
            changed_count += 1

    for sr in data.get("search_runs", []):
        db.execute(
            "INSERT INTO search_runs (slug, total_found, matches, run_at) VALUES (?, ?, ?, ?)",
            (sr["slug"], sr["total_found"], sr["matches"], sr["run_at"]),
        )

    db.commit()
    return jsonify({
        "received": len(data["vehicles"]),
        "new": new_count,
        "price_changed": changed_count,
        "skipped_rejected": skipped,
    })


def run_production():
    """Entry point for production (gunicorn)."""
    import subprocess
    subprocess.run([
        "gunicorn", "web:app",
        "--bind", "0.0.0.0:5001",
        "--workers", "2",
    ])


if __name__ == "__main__":
    app.run(debug=True, port=5001)
