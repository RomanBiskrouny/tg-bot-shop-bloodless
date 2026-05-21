from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from bot.callbacks import CALLBACKS

STATUS_EMOJI = {
    "pending": "🕐",
    "confirmed": "✅",
    "done": "📦",
    "cancelled": "❌",
}


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛍 Catalog", callback_data=CALLBACKS["CATALOG"])],
        [InlineKeyboardButton("🛒 My Cart", callback_data=CALLBACKS["VIEW_CART"])],
    ])


def catalog_keyboard(categories: list) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(f"👕 {cat}", callback_data=f"{CALLBACKS['CATEGORY']}:{cat}")]
        for cat in categories
    ]
    buttons.append([InlineKeyboardButton("🛒 My Cart", callback_data=CALLBACKS["VIEW_CART"])])
    return InlineKeyboardMarkup(buttons)


def products_keyboard(products: dict, category: str) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(
            f"{p['name']} — {p['price']:.2f}€",
            callback_data=f"{CALLBACKS['PRODUCT']}:{pid}"
        )]
        for pid, p in products.items()
    ]
    buttons.append([InlineKeyboardButton("⬅️ Back to Catalog", callback_data=CALLBACKS["CATALOG"])])
    buttons.append([InlineKeyboardButton("🛒 My Cart", callback_data=CALLBACKS["VIEW_CART"])])
    return InlineKeyboardMarkup(buttons)


def product_keyboard(product_id: str, category: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add to Cart", callback_data=f"{CALLBACKS['ADD_TO_CART']}:{product_id}")],
        [InlineKeyboardButton(f"⬅️ Back to {category}", callback_data=f"{CALLBACKS['CATEGORY']}:{category}")],
        [InlineKeyboardButton("🛒 My Cart", callback_data=CALLBACKS["VIEW_CART"])],
    ])


def cart_keyboard(cart: dict) -> InlineKeyboardMarkup:
    buttons = []
    for pid in cart:
        buttons.append([
            InlineKeyboardButton(f"❌ Remove #{pid}", callback_data=f"{CALLBACKS['REMOVE_FROM_CART']}:{pid}")
        ])
    buttons.append([
        InlineKeyboardButton("🗑 Clear", callback_data=CALLBACKS["CLEAR_CART"]),
        InlineKeyboardButton("✅ Checkout", callback_data=CALLBACKS["CHECKOUT"]),
    ])
    buttons.append([InlineKeyboardButton("🛍 Continue Shopping", callback_data=CALLBACKS["CATALOG"])])
    return InlineKeyboardMarkup(buttons)


def checkout_keyboard(has_promo: bool = False) -> InlineKeyboardMarkup:
    promo_label = "🔄 Change Promo Code" if has_promo else "🏷 Apply Promo Code"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirm Order", callback_data=CALLBACKS["CHECKOUT_CONFIRM"])],
        [InlineKeyboardButton(promo_label, callback_data=CALLBACKS["APPLY_PROMO"])],
        [InlineKeyboardButton("❌ Cancel", callback_data=CALLBACKS["VIEW_CART"])],
    ])


def promo_entry_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data=CALLBACKS["CANCEL_PROMO"])],
    ])


# ── Admin keyboards ────────────────────────────────────────────────────────────

def admin_panel_keyboard(pending_count: int = 0) -> InlineKeyboardMarkup:
    order_label = f"📋 Orders ({pending_count} new)" if pending_count else "📋 Orders"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(order_label, callback_data=CALLBACKS["ADMIN_ORDERS"])],
        [InlineKeyboardButton("➕ Add Product", callback_data=CALLBACKS["ADMIN_ADD_PRODUCT"])],
        [InlineKeyboardButton("🗂 Manage Products", callback_data=CALLBACKS["ADMIN_LIST_PRODUCTS"])],
        [InlineKeyboardButton("🏷 Manage Promo Codes", callback_data=CALLBACKS["ADMIN_PROMOS"])],
    ])


def admin_orders_keyboard(orders: dict) -> InlineKeyboardMarkup:
    buttons = []
    for oid, o in sorted(orders.items(), key=lambda x: int(x[0]), reverse=True):
        emoji = STATUS_EMOJI.get(o["status"], "❓")
        label = f"{emoji} Order #{oid} — @{o['username']} — {o['total']:.2f}€"
        buttons.append([InlineKeyboardButton(label, callback_data=f"{CALLBACKS['ADMIN_ORDER_DETAIL']}:{oid}")])
    buttons.append([InlineKeyboardButton("⬅️ Admin Panel", callback_data=CALLBACKS["ADMIN_PANEL"])])
    return InlineKeyboardMarkup(buttons)


def admin_order_actions_keyboard(order_id: str, status: str) -> InlineKeyboardMarkup:
    buttons = []
    if status == "pending":
        buttons.append([
            InlineKeyboardButton("✅ Confirm", callback_data=f"{CALLBACKS['ADMIN_ORDER_CONFIRM']}:{order_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"{CALLBACKS['ADMIN_ORDER_CANCEL']}:{order_id}"),
        ])
    elif status == "confirmed":
        buttons.append([
            InlineKeyboardButton("📦 Mark as Done", callback_data=f"{CALLBACKS['ADMIN_ORDER_DONE']}:{order_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"{CALLBACKS['ADMIN_ORDER_CANCEL']}:{order_id}"),
        ])
    buttons.append([InlineKeyboardButton("⬅️ All Orders", callback_data=CALLBACKS["ADMIN_ORDERS"])])
    return InlineKeyboardMarkup(buttons)


def admin_products_keyboard(products: dict) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(
            f"🗑 {p['name']} ({p['category']})",
            callback_data=f"{CALLBACKS['ADMIN_DELETE_PRODUCT']}:{pid}"
        )]
        for pid, p in products.items()
    ]
    buttons.append([InlineKeyboardButton("⬅️ Admin Panel", callback_data=CALLBACKS["ADMIN_PANEL"])])
    return InlineKeyboardMarkup(buttons)


def admin_promos_keyboard(promos: dict) -> InlineKeyboardMarkup:
    buttons = []
    for code, data in promos.items():
        type_label = f"{data['value']}%" if data["type"] == "percent" else f"{data['value']:.2f}€ off"
        expiry = data.get("expires_at")
        expiry_label = f" · expires {expiry}" if expiry else ""
        buttons.append([
            InlineKeyboardButton(
                f"🗑 {code} ({type_label}{expiry_label})",
                callback_data=f"{CALLBACKS['ADMIN_DELETE_PROMO']}:{code}"
            )
        ])
    buttons.append([InlineKeyboardButton("➕ Add Promo Code", callback_data=CALLBACKS["ADMIN_ADD_PROMO"])])
    buttons.append([InlineKeyboardButton("⬅️ Admin Panel", callback_data=CALLBACKS["ADMIN_PANEL"])])
    return InlineKeyboardMarkup(buttons)


def admin_promo_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Percentage (%)", callback_data=CALLBACKS["ADMIN_PROMO_PERCENT"]),
            InlineKeyboardButton("💶 Fixed Amount (€)", callback_data=CALLBACKS["ADMIN_PROMO_FIXED"]),
        ],
    ])
