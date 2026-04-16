#!/usr/bin/env python3
"""Web UI for browsing and managing scouted vehicles."""

import json
import os
import sqlite3

from flask import Flask, g, jsonify, redirect, render_template_string, request, url_for

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vehicles.db")

app = Flask(__name__)

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
</style>
</head>
<body>
<h1>&#x1f1fa;&#x1f1e6; Vehicles4Ukraine</h1>
<div class="stats">
  {{ vehicles|length }} vehicle{{ 's' if vehicles|length != 1 }} shown
  &middot; {{ total }} total in DB
  &middot; {{ rejected_count }} rejected
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
      <span class="price">&euro; {{ "{:,}".format(v.price) }}</span>
      <span>{{ v.year }}</span>
      <span>{{ "{:,}".format(v.mileage_km) }} km</span>
      <span class="tag">{{ v.fuel }}</span>
      <span class="tag">{{ v.transmission }}</span>
      {% if v.color %}<span>{{ v.color }}</span>{% endif %}
      <span>{{ v.seller }}{% if v.location %}, {{ v.location }}{% endif %}</span>
    </div>
    <div class="portals">
      {% for p in v.portals %}
        <a href="{{ p.url }}" target="_blank">{{ p.name }}</a>
      {% endfor %}
    </div>
    {% if v.price_history|length > 1 %}
    <div class="price-history">
      Price: {% for ph in v.price_history %}&euro;{{ "{:,}".format(ph[0]) }} ({{ ph[1][:10] }}){{ ' &rarr; ' if not loop.last }}{% endfor %}
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


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
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
            "portals": portals,
            "rejected": row["rejected"],
            "first_seen": row["first_seen_at"],
            "is_new": row["first_seen_at"][:10] == __import__("datetime").date.today().isoformat(),
            "price_changed": row["price_at_first_seen"] is not None and row["price"] != row["price_at_first_seen"],
            "price_history": [(ph[0], ph[1]) for ph in price_history],
        })

    return render_template_string(TEMPLATE, vehicles=vehicles, total=total,
                                  rejected_count=rejected_count, show=show)


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


if __name__ == "__main__":
    app.run(debug=True, port=5001)
