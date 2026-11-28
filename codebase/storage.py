"""Local SQLite persistence for member profiles and finalized cart drafts."""
import json
import sqlite3
import uuid
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "lunchie.sqlite3"


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=10, isolation_level="IMMEDIATE")
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA journal_mode = WAL")
    return db


def initialize():
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS members (
          member_id TEXT PRIMARY KEY, name TEXT NOT NULL COLLATE NOCASE UNIQUE,
          allergies_json TEXT NOT NULL DEFAULT '[]', avoid_json TEXT NOT NULL DEFAULT '[]',
          vegetarian INTEGER NOT NULL DEFAULT 0, preferred_dish TEXT NOT NULL DEFAULT '',
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS orders (
          order_id TEXT PRIMARY KEY, restaurant_id TEXT NOT NULL, restaurant_name TEXT NOT NULL,
          menu_version INTEGER NOT NULL, created_at TEXT NOT NULL,
          total_food_vnd INTEGER NOT NULL, shipping_fee_vnd INTEGER NOT NULL,
          total_order_vnd INTEGER NOT NULL, cart_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS order_items (
          item_id INTEGER PRIMARY KEY AUTOINCREMENT, order_id TEXT NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
          member_id TEXT REFERENCES members(member_id) ON DELETE SET NULL,
          member_name TEXT NOT NULL, dish_id TEXT NOT NULL, dish_name TEXT NOT NULL,
          price_vnd INTEGER NOT NULL, ship_share_vnd INTEGER NOT NULL,
          total_member_vnd INTEGER NOT NULL, is_blind_bag INTEGER NOT NULL DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_order_items_member ON order_items(member_id);
        CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at DESC);
        CREATE TABLE IF NOT EXISTS schema_meta (version INTEGER NOT NULL);
        INSERT INTO schema_meta(version) SELECT 1 WHERE NOT EXISTS (SELECT 1 FROM schema_meta);
        """)


def list_members():
    initialize()
    with connect() as db:
        rows = db.execute("SELECT * FROM members ORDER BY name COLLATE NOCASE").fetchall()
    return [{"member_id": r["member_id"], "name": r["name"], "allergies": json.loads(r["allergies_json"]),
             "avoid_keywords": json.loads(r["avoid_json"]), "vegetarian": bool(r["vegetarian"]),
             "preferred_dish": r["preferred_dish"], "updated_at": r["updated_at"]} for r in rows]


def list_orders(limit=50):
    initialize()
    with connect() as db:
        orders = db.execute("SELECT * FROM orders ORDER BY created_at DESC, rowid DESC LIMIT ?", (min(max(int(limit), 1), 100),)).fetchall()
        result = []
        for order in orders:
            items = db.execute("SELECT member_name,dish_id,dish_name,price_vnd,ship_share_vnd,total_member_vnd,is_blind_bag FROM order_items WHERE order_id=? ORDER BY item_id", (order["order_id"],)).fetchall()
            result.append({"order_id": order["order_id"], "restaurant_id": order["restaurant_id"], "restaurant_name": order["restaurant_name"], "created_at": order["created_at"], "total_order_vnd": order["total_order_vnd"], "items": [dict(i) for i in items]})
    return result


def finalize(order_id, cart, members, save_profiles=False, menu_version=4):
    """Idempotently save a validated draft; optional profiles require explicit user opt-in."""
    if not isinstance(cart, dict) or not cart.get("ok"):
        raise ValueError("Không lưu được vì giỏ chưa qua kiểm tra.")
    order_id = str(order_id or uuid.uuid4().hex)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    initialize()
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        existing = db.execute("SELECT cart_json FROM orders WHERE order_id=?", (order_id,)).fetchone()
        if existing:
            return {"order_id": order_id, **json.loads(existing["cart_json"])}
        member_ids = {}
        if save_profiles:
            # SQLite NOCASE only folds ASCII. Reuse the stored spelling for Vietnamese names.
            stored_names = {unicodedata.normalize("NFC", row["name"]).casefold(): row["name"]
                            for row in db.execute("SELECT name FROM members")}
            for m in members:
                name = stored_names.setdefault(unicodedata.normalize("NFC", m["name"]).casefold(), m["name"])
                member_id = m.get("member_id") or uuid.uuid4().hex
                db.execute("""INSERT INTO members(member_id,name,allergies_json,avoid_json,vegetarian,preferred_dish,updated_at)
                  VALUES(?,?,?,?,?,?,?) ON CONFLICT(name) DO UPDATE SET allergies_json=excluded.allergies_json,
                  avoid_json=excluded.avoid_json,vegetarian=excluded.vegetarian,preferred_dish=excluded.preferred_dish,updated_at=excluded.updated_at""",
                           (member_id, name, json.dumps(m.get("allergies", []), ensure_ascii=False),
                            json.dumps(m.get("avoid_keywords", []) + m.get("avoid_allergens", []), ensure_ascii=False),
                            int(bool(m.get("vegetarian"))), m.get("preferred_dish", ""), now))
                row = db.execute("SELECT member_id FROM members WHERE name=? COLLATE NOCASE", (name,)).fetchone()
                member_ids[m["name"].casefold()] = row["member_id"]
        db.execute("INSERT INTO orders VALUES(?,?,?,?,?,?,?,?,?)", (order_id, cart["restaurant_id"], cart["restaurant_name"], menu_version, now, cart["total_food_vnd"], cart["shipping_fee_vnd"], cart["total_order_vnd"], json.dumps(cart, ensure_ascii=False)))
        for item in cart["items"]:
            db.execute("""INSERT INTO order_items(order_id,member_id,member_name,dish_id,dish_name,price_vnd,ship_share_vnd,total_member_vnd,is_blind_bag)
                        VALUES(?,?,?,?,?,?,?,?,?)""", (order_id, member_ids.get(item["member_name"].casefold()), item["member_name"], item["dish_id"], item["ten_mon"], item["price_vnd"], item["ship_share_vnd"], item["total_member_vnd"], int(bool(item.get("is_blind_bag")))))
    return {"order_id": order_id, **cart}


initialize()
