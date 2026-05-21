from collections import defaultdict
from typing import Dict

# In-memory cart storage: {user_id: {product_id: quantity}}
_carts: Dict[int, Dict[str, int]] = defaultdict(dict)


def get_cart(user_id: int) -> Dict[str, int]:
    return dict(_carts[user_id])


def add_item(user_id: int, product_id: str, qty: int = 1):
    _carts[user_id][product_id] = _carts[user_id].get(product_id, 0) + qty


def remove_item(user_id: int, product_id: str):
    if product_id in _carts[user_id]:
        del _carts[user_id][product_id]


def clear_cart(user_id: int):
    _carts[user_id] = {}


def cart_total(user_id: int, products: dict) -> float:
    total = 0.0
    for pid, qty in _carts[user_id].items():
        p = products.get(pid)
        if p:
            total += p["price"] * qty
    return total


def cart_item_count(user_id: int) -> int:
    return sum(_carts[user_id].values())
