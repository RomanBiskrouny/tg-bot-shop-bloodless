import json
import os
from datetime import date
from typing import Optional

DATA_FILE = "data/products.json"
ORDERS_FILE = "data/orders.json"
PROMOS_FILE = "data/promos.json"


def _load(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(path: str, data: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── Products ──────────────────────────────────────────────────────────────────

def get_products() -> dict:
    return _load(DATA_FILE)


def save_products(products: dict):
    _save(DATA_FILE, products)


def get_categories() -> list:
    products = get_products()
    cats = sorted({p["category"] for p in products.values()})
    return cats


def get_products_by_category(category: str) -> dict:
    return {pid: p for pid, p in get_products().items() if p["category"] == category}


def get_product(product_id: str) -> Optional[dict]:
    return get_products().get(product_id)


def add_product(name: str, description: str, price: float, category: str, image_id: Optional[str] = None) -> str:
    products = get_products()
    pid = str(max((int(k) for k in products.keys()), default=0) + 1)
    products[pid] = {
        "name": name,
        "description": description,
        "price": price,
        "category": category,
        "image_id": image_id,
    }
    save_products(products)
    return pid


def delete_product(product_id: str) -> bool:
    products = get_products()
    if product_id in products:
        del products[product_id]
        save_products(products)
        return True
    return False


# ── Promo Codes ───────────────────────────────────────────────────────────────

def get_promos() -> dict:
    return _load(PROMOS_FILE)


def save_promos(promos: dict):
    _save(PROMOS_FILE, promos)


def get_promo(code: str) -> Optional[dict]:
    return get_promos().get(code.upper())


def add_promo(code: str, type_: str, value: float, expires_at: Optional[str] = None) -> bool:
    promos = get_promos()
    key = code.upper().strip()
    if not key:
        return False
    entry: dict = {"type": type_, "value": value, "active": True}
    if expires_at:
        entry["expires_at"] = expires_at
    promos[key] = entry
    save_promos(promos)
    return True


def is_promo_expired(promo_data: dict) -> bool:
    expires_at = promo_data.get("expires_at")
    if not expires_at:
        return False
    try:
        expiry = date.fromisoformat(expires_at)
        return date.today() > expiry
    except ValueError:
        return False


def delete_promo(code: str) -> bool:
    promos = get_promos()
    key = code.upper()
    if key in promos:
        del promos[key]
        save_promos(promos)
        return True
    return False


def compute_discount(promo_data: dict, subtotal: float) -> float:
    if promo_data["type"] == "percent":
        return round(subtotal * promo_data["value"] / 100, 2)
    return round(min(promo_data["value"], subtotal), 2)


# ── Orders ────────────────────────────────────────────────────────────────────

def save_order(
    user_id: int,
    username: str,
    cart: dict,
    promo_code: Optional[str] = None,
    discount_amount: float = 0.0,
) -> str:
    orders = _load(ORDERS_FILE)
    oid = str(max((int(k) for k in orders.keys()), default=0) + 1)
    products = get_products()
    items = []
    total = 0.0
    for pid, qty in cart.items():
        p = products.get(pid)
        if p:
            subtotal = p["price"] * qty
            total += subtotal
            items.append({
                "product_id": pid,
                "name": p["name"],
                "price": p["price"],
                "qty": qty,
                "subtotal": subtotal,
            })
    final_total = round(max(total - discount_amount, 0.0), 2)
    order = {
        "user_id": user_id,
        "username": username,
        "items": items,
        "total": round(total, 2),
        "status": "pending",
    }
    if promo_code and discount_amount > 0:
        order["promo_code"] = promo_code
        order["discount"] = discount_amount
        order["final_total"] = final_total
    orders[oid] = order
    _save(ORDERS_FILE, orders)
    return oid


def get_orders() -> dict:
    return _load(ORDERS_FILE)


def get_order(order_id: str) -> Optional[dict]:
    return get_orders().get(order_id)


def update_order_status(order_id: str, status: str) -> bool:
    orders = get_orders()
    if order_id in orders:
        orders[order_id]["status"] = status
        _save(ORDERS_FILE, orders)
        return True
    return False


def get_orders_by_status(status: str) -> dict:
    return {oid: o for oid, o in get_orders().items() if o["status"] == status}
