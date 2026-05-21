import os
import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from bot.callbacks import CALLBACKS
from bot import cart as cart_module
from bot import database as db
from bot.keyboards import (
    main_menu_keyboard, catalog_keyboard, products_keyboard,
    product_keyboard, cart_keyboard, checkout_keyboard,
    admin_panel_keyboard, admin_orders_keyboard, admin_order_actions_keyboard,
    admin_products_keyboard, STATUS_EMOJI,
    admin_promos_keyboard, admin_promo_type_keyboard, promo_entry_keyboard
)

logger = logging.getLogger(__name__)

ADMIN_IDS_ENV = os.environ.get("ADMIN_IDS", "")
ADMIN_IDS = set(int(x.strip()) for x in ADMIN_IDS_ENV.split(",") if x.strip().isdigit())

ADMIN_NAME, ADMIN_DESC, ADMIN_PRICE, ADMIN_CATEGORY, ADMIN_IMAGE = range(5)

# Conversation states for promo entry at checkout
ENTER_PROMO = 10

# Conversation states for admin add promo
ADMIN_PROMO_CODE, ADMIN_PROMO_TYPE, ADMIN_PROMO_VALUE, ADMIN_PROMO_EXPIRY = range(20, 24)


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def _order_text(order_id: str, order: dict) -> str:
    emoji = STATUS_EMOJI.get(order["status"], "❓")
    lines = [
        f"🧾 <b>Order #{order_id}</b>",
        f"👤 Customer: @{order['username']} (ID: {order['user_id']})",
        f"📌 Status: {emoji} <b>{order['status'].capitalize()}</b>\n",
    ]
    for item in order["items"]:
        lines.append(f"• {item['name']} x{item['qty']} = {item['subtotal']:.2f}€")
    
    subtotal = sum(item['subtotal'] for item in order['items'])
    if order.get("discount") and order["discount"] > 0:
        lines.append(f"\n💰 Subtotal: {subtotal:.2f}€")
        lines.append(f"🏷 Promo: {order.get('promo_code', 'N/A')} (-{order['discount']:.2f}€)")
        lines.append(f"✅ <b>Total: {order['total']:.2f}€</b>")
    else:
        lines.append(f"\n💰 <b>Total: {order['total']:.2f}€</b>")
        
    return "\n".join(lines)


def _build_checkout_text(cart: dict, products: dict, promo_code: str | None) -> tuple[str, float, float]:
    lines = ["📋 <b>Order Summary</b>\n"]
    total = 0.0
    for pid, qty in cart.items():
        p = products.get(pid)
        if p:
            subtotal = p["price"] * qty
            total += subtotal
            lines.append(f"• {p['name']} x{qty} = {subtotal:.2f}€")

    lines.append(f"\n💰 <b>Subtotal: {total:.2f}€</b>")

    discount_amount = 0.0
    if promo_code:
        promo_data = db.get_promo(promo_code)
        if promo_data:
            discount_amount = db.compute_discount(promo_data, total)
            type_label = f"{promo_data['value']}%" if promo_data["type"] == "percent" else f"{promo_data['value']:.2f}€"
            lines.append(f"🏷 Promo <code>{promo_code}</code> ({type_label}): -<b>{discount_amount:.2f}€</b>")
            final = round(total - discount_amount, 2)
            lines.append(f"✅ <b>Final Total: {final:.2f}€</b>")

    lines.append("\nConfirm your order?")
    return "\n".join(lines), total, discount_amount


# ── User Handlers ─────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        f"👋 Hello, <b>{user.first_name}</b>!\n\n"
        "Welcome to our clothing shop 👕\n"
        "Browse our catalog and place your order.\n\n"
        "Use the buttons below to get started:"
    )
    if update.message:
        await update.message.reply_html(text, reply_markup=main_menu_keyboard())
    else:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text, parse_mode="HTML", reply_markup=main_menu_keyboard()
        )


async def catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    categories = db.get_categories()
    text = "🛍 <b>Our Clothing Catalog</b>\n\nChoose a category:"
    kb = catalog_keyboard(categories) if categories else None

    if update.callback_query:
        await update.callback_query.answer()
        if not categories:
            await update.callback_query.edit_message_text("😕 No products available yet.")
            return
        await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)
    else:
        if not categories:
            await update.message.reply_text("😕 No products available yet.")
            return
        await update.message.reply_html(text, reply_markup=kb)


async def show_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    category = query.data.split(":", 1)[1]
    products = db.get_products_by_category(category)
    if not products:
        await query.edit_message_text(f"😕 No items in <b>{category}</b>.", parse_mode="HTML")
        return
    await query.edit_message_text(
        f"👕 <b>{category}</b>\n\nChoose an item:",
        parse_mode="HTML",
        reply_markup=products_keyboard(products, category)
    )


async def show_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    product_id = query.data.split(":", 1)[1]
    product = db.get_product(product_id)
    if not product:
        await query.edit_message_text("❌ Product not found.")
        return

    text = (
        f"<b>{product['name']}</b>\n\n"
        f"📝 {product['description']}\n\n"
        f"💰 Price: <b>{product['price']:.2f}€</b>\n"
        f"🏷 Category: {product['category']}"
    )
    keyboard = product_keyboard(product_id, product["category"])

    if product.get("image_id"):
        try:
            await query.delete_message()
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=product["image_id"],
                caption=text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
            return
        except Exception:
            pass
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)


async def add_to_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    product_id = query.data.split(":", 1)[1]
    product = db.get_product(product_id)
    if not product:
        await query.answer("❌ Product not found.", show_alert=True)
        return
    cart_module.add_item(query.from_user.id, product_id)
    count = cart_module.cart_item_count(query.from_user.id)
    await query.answer(f"✅ {product['name']} added! ({count} items in cart)")


async def view_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        user_id = update.callback_query.from_user.id
        await update.callback_query.answer()
        send = update.callback_query.edit_message_text
    else:
        user_id = update.message.from_user.id
        send = None

    cart = cart_module.get_cart(user_id)
    products = db.get_products()

    if not cart:
        text = "🛒 Your cart is <b>empty</b>.\n\nUse /catalog to browse."
        kb = catalog_keyboard(db.get_categories())
        if send:
            await send(text, parse_mode="HTML", reply_markup=kb)
        else:
            await update.message.reply_html(text, reply_markup=kb)
        return

    lines = ["🛒 <b>Your Cart</b>\n"]
    total = 0.0
    for pid, qty in cart.items():
        p = products.get(pid)
        if p:
            subtotal = p["price"] * qty
            total += subtotal
            lines.append(f"• {p['name']} x{qty} = {subtotal:.2f}€")
    lines.append(f"\n💰 <b>Total: {total:.2f}€</b>")
    text = "\n".join(lines)
    kb = cart_keyboard(cart)

    if send:
        await send(text, parse_mode="HTML", reply_markup=kb)
    else:
        await update.message.reply_html(text, reply_markup=kb)


async def remove_from_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cart_module.remove_item(query.from_user.id, query.data.split(":", 1)[1])
    await view_cart(update, context)


async def clear_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cart_module.clear_cart(query.from_user.id)
    context.user_data.pop("promo_code", None)
    await query.edit_message_text(
        "🗑 Cart cleared!",
        reply_markup=main_menu_keyboard()
    )


async def checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    cart = cart_module.get_cart(user_id)

    if not cart:
        await query.edit_message_text("🛒 Your cart is empty!", reply_markup=main_menu_keyboard())
        return

    products = db.get_products()
    promo_code = context.user_data.get("promo_code")
    text, _, _ = _build_checkout_text(cart, products, promo_code)

    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=checkout_keyboard(has_promo=bool(promo_code))
    )


# ── Promo Code Conversation ───────────────────────────────────────────────────

async def apply_promo_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["promo_msg_id"] = query.message.message_id
    context.user_data["promo_chat_id"] = query.message.chat_id
    await query.edit_message_text(
        "🏷 <b>Enter Promo Code</b>\n\nType your promo code below:",
        parse_mode="HTML",
        reply_markup=promo_entry_keyboard()
    )
    return ENTER_PROMO


async def apply_promo_enter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip().upper()
    chat_id = context.user_data.get("promo_chat_id")
    msg_id = context.user_data.get("promo_msg_id")
    user_id = update.message.from_user.id

    try:
        await update.message.delete()
    except Exception:
        pass

    promo_data = db.get_promo(code)

    if not promo_data or not promo_data.get("active"):
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg_id,
            text=(
                f"❌ <b>Invalid promo code:</b> <code>{code}</code>\n\n"
                "Please try another code or press Cancel to go back:"
            ),
            parse_mode="HTML",
            reply_markup=promo_entry_keyboard()
        )
        return ENTER_PROMO

    if db.is_promo_expired(promo_data):
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg_id,
            text=(
                f"⏰ <b>Promo code expired:</b> <code>{code}</code>\n\n"
                "This code is no longer valid. Please try another code or press Cancel to go back:"
            ),
            parse_mode="HTML",
            reply_markup=promo_entry_keyboard()
        )
        return ENTER_PROMO

    context.user_data["promo_code"] = code
    cart = cart_module.get_cart(user_id)
    products = db.get_products()
    text, _, _ = _build_checkout_text(cart, products, code)

    await context.bot.edit_message_text(
        chat_id=chat_id,
        message_id=msg_id,
        text=text,
        parse_mode="HTML",
        reply_markup=checkout_keyboard(has_promo=True)
    )
    return ConversationHandler.END


async def apply_promo_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    cart = cart_module.get_cart(user_id)
    products = db.get_products()
    promo_code = context.user_data.get("promo_code")
    text, _, _ = _build_checkout_text(cart, products, promo_code)

    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=checkout_keyboard(has_promo=bool(promo_code))
    )
    return ConversationHandler.END


async def checkout_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    username = query.from_user.username or query.from_user.first_name
    cart = cart_module.get_cart(user_id)

    if not cart:
        await query.edit_message_text("🛒 Your cart is empty!", reply_markup=main_menu_keyboard())
        return

    promo_code = context.user_data.pop("promo_code", None)
    discount_amount = 0.0
    if promo_code:
        promo_data = db.get_promo(promo_code)
        if promo_data:
            products = db.get_products()
            subtotal = sum(
                products[pid]["price"] * qty
                for pid, qty in cart.items()
                if pid in products
            )
            discount_amount = db.compute_discount(promo_data, subtotal)

    order_id = db.save_order(user_id, username, cart, promo_code=promo_code, discount_amount=discount_amount)
    cart_module.clear_cart(user_id)

    confirm_lines = [f"🎉 <b>Order #{order_id} placed successfully!</b>\n"]
    if promo_code and discount_amount > 0:
        confirm_lines.append(f"🏷 Promo <code>{promo_code}</code> saved you <b>{discount_amount:.2f}€</b>!\n")
    confirm_lines.append("Thank you for your purchase! We'll be in touch soon.\n\nUse /start to return to the main menu.")

    await query.edit_message_text(
        "\n".join(confirm_lines),
        parse_mode="HTML",
        reply_markup=main_menu_keyboard()
    )

    # Notify admins
    if ADMIN_IDS:
        order = db.get_order(order_id)
        msg = _order_text(order_id, order) + "\n\n<i>New order — please review in /admin</i>"
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(admin_id, msg, parse_mode="HTML")
            except Exception as e:
                logger.warning(f"Could not notify admin {admin_id}: {e}")


# ── Admin handlers ─────────────────────────────────────────────────────────────

async def handle_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ You don't have admin access.")
        return
    pending = len(db.get_orders_by_status("pending"))
    await update.message.reply_html(
        "👑 <b>Admin Panel</b>",
        reply_markup=admin_panel_keyboard(pending)
    )


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        await query.edit_message_text("⛔ Access denied.")
        return
    pending = len(db.get_orders_by_status("pending"))
    await query.edit_message_text(
        "👑 <b>Admin Panel</b>",
        parse_mode="HTML",
        reply_markup=admin_panel_keyboard(pending)
    )


async def admin_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        await query.edit_message_text("⛔ Access denied.")
        return
    orders = db.get_orders()
    if not orders:
        await query.edit_message_text(
            "📋 No orders yet.",
            reply_markup=admin_panel_keyboard()
        )
        return
    pending = len([o for o in orders.values() if o["status"] == "pending"])
    await query.edit_message_text(
        f"📋 <b>All Orders</b> ({len(orders)} total, {pending} pending)\n\nSelect an order:",
        parse_mode="HTML",
        reply_markup=admin_orders_keyboard(orders)
    )


async def admin_order_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        await query.edit_message_text("⛔ Access denied.")
        return
    order_id = query.data.split(":", 1)[1]
    order = db.get_order(order_id)
    if not order:
        await query.edit_message_text("❌ Order not found.")
        return
    await query.edit_message_text(
        _order_text(order_id, order),
        parse_mode="HTML",
        reply_markup=admin_order_actions_keyboard(order_id, order["status"])
    )


async def admin_order_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return
    order_id = query.data.split(":", 1)[1]
    db.update_order_status(order_id, "confirmed")
    order = db.get_order(order_id)
    await query.edit_message_text(
        _order_text(order_id, order),
        parse_mode="HTML",
        reply_markup=admin_order_actions_keyboard(order_id, "confirmed")
    )
    try:
        await context.bot.send_message(
            order["user_id"],
            f"✅ <b>Your order #{order_id} has been confirmed!</b>\n"
            "We're preparing your clothing order.",
            parse_mode="HTML"
        )
    except Exception:
        pass


async def admin_order_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return
    order_id = query.data.split(":", 1)[1]
    db.update_order_status(order_id, "cancelled")
    order = db.get_order(order_id)
    await query.edit_message_text(
        _order_text(order_id, order),
        parse_mode="HTML",
        reply_markup=admin_order_actions_keyboard(order_id, "cancelled")
    )
    try:
        await context.bot.send_message(
            order["user_id"],
            f"❌ <b>Your order #{order_id} has been cancelled.</b>\n"
            "Please contact us if you have questions.",
            parse_mode="HTML"
        )
    except Exception:
        pass


async def admin_order_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return
    order_id = query.data.split(":", 1)[1]
    db.update_order_status(order_id, "done")
    order = db.get_order(order_id)
    await query.edit_message_text(
        _order_text(order_id, order),
        parse_mode="HTML",
        reply_markup=admin_order_actions_keyboard(order_id, "done")
    )
    try:
        await context.bot.send_message(
            order["user_id"],
            f"📦 <b>Your order #{order_id} is on its way!</b>\n"
            "Your clothing is packed and ready for delivery.",
            parse_mode="HTML"
        )
    except Exception:
        pass


async def admin_list_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        await query.edit_message_text("⛔ Access denied.")
        return
    products = db.get_products()
    if not products:
        await query.edit_message_text("🗂 No products yet.", reply_markup=admin_panel_keyboard())
        return
    await query.edit_message_text(
        f"🗂 <b>All Products ({len(products)})</b>\n\nTap to delete:",
        parse_mode="HTML",
        reply_markup=admin_products_keyboard(products)
    )


async def admin_delete_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return
    product_id = query.data.split(":", 1)[1]
    product = db.get_product(product_id)
    name = product["name"] if product else product_id
    db.delete_product(product_id)
    products = db.get_products()
    await query.edit_message_text(
        f"✅ <b>{name}</b> deleted.\n\n🗂 <b>Remaining ({len(products)})</b>",
        parse_mode="HTML",
        reply_markup=admin_products_keyboard(products) if products else admin_panel_keyboard()
    )


# ── Add Product Conversation ──────────────────────────────────────────────────

async def admin_add_product_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return ConversationHandler.END
    await query.edit_message_text(
        "➕ <b>Add New Product</b>\n\n"
        "Step 1/5: Enter the product <b>name</b>:\n"
        "<i>(or /cancel to abort)</i>",
        parse_mode="HTML"
    )
    return ADMIN_NAME


async def admin_add_product_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_product"] = {"name": update.message.text.strip()}
    await update.message.reply_html("Step 2/5: Enter the <b>description</b>:")
    return ADMIN_DESC


async def admin_add_product_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_product"]["description"] = update.message.text.strip()
    await update.message.reply_html("Step 3/5: Enter the <b>price</b> (e.g. 24.99):")
    return ADMIN_PRICE


async def admin_add_product_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = float(update.message.text.strip().replace(",", "."))
    except ValueError:
        await update.message.reply_text("❌ Invalid price. Enter a number like 24.99:")
        return ADMIN_PRICE
    context.user_data["new_product"]["price"] = price
    await update.message.reply_html(
        "Step 4/5: Enter the <b>category</b>:\n"
        "Options: <code>Shorts</code>, <code>Pants</code>, <code>Caps</code>"
    )
    return ADMIN_CATEGORY


async def admin_add_product_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_product"]["category"] = update.message.text.strip()
    await update.message.reply_html(
        "Step 5/5: Send a <b>photo</b> of the product, or type <code>skip</code>:"
    )
    return ADMIN_IMAGE


async def admin_add_product_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data.get("new_product", {})
    image_id = None

    if update.message.photo:
        image_id = update.message.photo[-1].file_id
    elif update.message.text and update.message.text.strip().lower() == "skip":
        image_id = None
    else:
        await update.message.reply_text("Please send a photo or type 'skip':")
        return ADMIN_IMAGE

    pid = db.add_product(
        name=data["name"],
        description=data["description"],
        price=data["price"],
        category=data["category"],
        image_id=image_id,
    )
    pending = len(db.get_orders_by_status("pending"))
    await update.message.reply_html(
        f"✅ <b>{data['name']}</b> added (ID #{pid})!",
        reply_markup=admin_panel_keyboard(pending)
    )
    context.user_data.pop("new_product", None)
    return ConversationHandler.END


# ── Admin Promo Handlers ───────────────────────────────────────────────────────

async def admin_promos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        await query.edit_message_text("⛔ Access denied.")
        return
    promos = db.get_promos()
    count = len(promos)
    await query.edit_message_text(
        f"🏷 <b>Promo Codes ({count})</b>\n\nTap a code to delete it, or add a new one:",
        parse_mode="HTML",
        reply_markup=admin_promos_keyboard(promos)
    )


async def admin_delete_promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return
    code = query.data.split(":", 1)[1]
    db.delete_promo(code)
    promos = db.get_promos()
    await query.edit_message_text(
        f"✅ Promo code <code>{code}</code> deleted.\n\n🏷 <b>Promo Codes ({len(promos)})</b>",
        parse_mode="HTML",
        reply_markup=admin_promos_keyboard(promos)
    )


async def admin_add_promo_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return ConversationHandler.END
    await query.edit_message_text(
        "➕ <b>Add Promo Code</b>\n\n"
        "Step 1/4: Enter the promo <b>code</b> (e.g. SUMMER20):\n"
        "<i>(or /cancel to abort)</i>",
        parse_mode="HTML"
    )
    return ADMIN_PROMO_CODE


async def admin_add_promo_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip().upper()
    if not code:
        await update.message.reply_text("❌ Code cannot be empty. Try again:")
        return ADMIN_PROMO_CODE
    context.user_data["new_promo"] = {"code": code}
    await update.message.reply_html(
        "Step 2/4: Choose the discount <b>type</b>:",
        reply_markup=admin_promo_type_keyboard()
    )
    return ADMIN_PROMO_TYPE


async def admin_add_promo_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    from bot.callbacks import CALLBACKS
    if query.data == CALLBACKS["ADMIN_PROMO_PERCENT"]:
        promo_type = "percent"
        prompt = "Step 3/4: Enter the discount <b>percentage</b> (e.g. 20 for 20% off):"
    else:
        promo_type = "fixed"
        prompt = "Step 3/4: Enter the <b>fixed discount amount</b> in € (e.g. 5.00):"
    context.user_data["new_promo"]["type"] = promo_type
    await query.edit_message_text(prompt, parse_mode="HTML")
    return ADMIN_PROMO_VALUE


async def admin_add_promo_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        value = float(update.message.text.strip().replace(",", "."))
        if value <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Invalid value. Enter a positive number (e.g. 15 or 5.00):")
        return ADMIN_PROMO_VALUE
    context.user_data["new_promo"]["value"] = value
    await update.message.reply_html(
        "Step 4/4: Enter an optional <b>expiry date</b> in YYYY-MM-DD format "
        "(e.g. <code>2025-12-31</code>), or type <code>skip</code> for no expiry:"
    )
    return ADMIN_PROMO_EXPIRY


async def admin_add_promo_expiry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from datetime import date
    text = update.message.text.strip()
    data = context.user_data.get("new_promo", {})
    expires_at = None

    if text.lower() != "skip":
        try:
            expiry = date.fromisoformat(text)
            if expiry <= date.today():
                await update.message.reply_text(
                    "❌ Expiry date must be in the future. Enter a future date (YYYY-MM-DD) or type <code>skip</code>:",
                    parse_mode="HTML"
                )
                return ADMIN_PROMO_EXPIRY
            expires_at = text
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid date format. Use YYYY-MM-DD (e.g. <code>2025-12-31</code>) or type <code>skip</code>:",
                parse_mode="HTML"
            )
            return ADMIN_PROMO_EXPIRY

    db.add_promo(
        code=data["code"],
        type_=data["type"],
        value=data["value"],
        expires_at=expires_at,
    )

    expiry_text = f" (expires {expires_at})" if expires_at else " (no expiry)"
    pending = len(db.get_orders_by_status("pending"))
    await update.message.reply_html(
        f"✅ Promo code <code>{data['code']}</code> added{expiry_text}!",
        reply_markup=admin_panel_keyboard(pending)
    )
    context.user_data.pop("new_promo", None)
    return ConversationHandler.END
