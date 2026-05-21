import logging
import os
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ConversationHandler,
)
from bot.handlers import (
    start,
    catalog,
    show_category,
    show_product,
    add_to_cart,
    view_cart,
    remove_from_cart,
    checkout,
    checkout_confirm,
    clear_cart,
    handle_admin,
    admin_panel,
    admin_orders,
    admin_order_detail,
    admin_order_confirm,
    admin_order_cancel,
    admin_order_done,
    admin_add_product_start,
    admin_add_product_name,
    admin_add_product_desc,
    admin_add_product_price,
    admin_add_product_category,
    admin_add_product_image,
    admin_list_products,
    admin_delete_product,
    admin_panel,
    apply_promo_start,
    apply_promo_enter,
    apply_promo_cancel,
    admin_promos,
    admin_delete_promo,
    admin_add_promo_start,
    admin_add_promo_code,
    admin_add_promo_type,
    admin_add_promo_value,
    admin_add_promo_expiry,
    ADMIN_NAME,
    ADMIN_DESC,
    ADMIN_PRICE,
    ADMIN_CATEGORY,
    ADMIN_IMAGE,
    ENTER_PROMO,
    ADMIN_PROMO_CODE,
    ADMIN_PROMO_TYPE,
    ADMIN_PROMO_VALUE,
    ADMIN_PROMO_EXPIRY,
)    
from bot.callbacks import CALLBACKS

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN environment variable not set!")

    app = ApplicationBuilder().token(token).build()

    # Promo code entry conversation (during checkout)
    promo_entry_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                apply_promo_start, pattern=f"^{CALLBACKS['APPLY_PROMO']}$"
            )
        ],
        states={
            ENTER_PROMO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, apply_promo_enter),
                CallbackQueryHandler(
                    apply_promo_cancel, pattern=f"^{CALLBACKS['CANCEL_PROMO']}$"
                ),
            ],
        },
        fallbacks=[CommandHandler("cancel", apply_promo_cancel)],
        per_message=False,
    )

    # Admin add product conversation
    add_product_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                admin_add_product_start, pattern=f"^{CALLBACKS['ADMIN_ADD_PRODUCT']}$"
            )
        ],
        states={
            ADMIN_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_product_name)
            ],
            ADMIN_DESC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_product_desc)
            ],
            ADMIN_PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_product_price)
            ],
            ADMIN_CATEGORY: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, admin_add_product_category
                )
            ],
            ADMIN_IMAGE: [
                MessageHandler(
                    filters.PHOTO | (filters.TEXT & ~filters.COMMAND),
                    admin_add_product_image,
                )
            ],
        },
        fallbacks=[CommandHandler("cancel", start)],
        per_message=False,
    )

    # Admin add promo code conversation
    add_promo_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                admin_add_promo_start, pattern=f"^{CALLBACKS['ADMIN_ADD_PROMO']}$"
            )
        ],
        states={
            ADMIN_PROMO_CODE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_promo_code)
            ],
            ADMIN_PROMO_TYPE: [
                CallbackQueryHandler(
                    admin_add_promo_type,
                    pattern=f"^{CALLBACKS['ADMIN_PROMO_PERCENT']}$",
                ),
                CallbackQueryHandler(
                    admin_add_promo_type, pattern=f"^{CALLBACKS['ADMIN_PROMO_FIXED']}$"
                ),
            ],
            ADMIN_PROMO_VALUE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_promo_value)
            ],
            ADMIN_PROMO_EXPIRY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_promo_expiry)
            ],
        },
        fallbacks=[CommandHandler("cancel", start)],
        per_message=False,
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("catalog", catalog))
    app.add_handler(CommandHandler("cart", view_cart))
    app.add_handler(CommandHandler("admin", handle_admin))

    app.add_handler(promo_entry_conv)
    app.add_handler(add_product_conv)
    app.add_handler(add_promo_conv)

    app.add_handler(CallbackQueryHandler(catalog, pattern=f"^{CALLBACKS['CATALOG']}$"))
    app.add_handler(
        CallbackQueryHandler(show_category, pattern=f"^{CALLBACKS['CATEGORY']}:")
    )
    app.add_handler(
        CallbackQueryHandler(show_product, pattern=f"^{CALLBACKS['PRODUCT']}:")
    )
    app.add_handler(
        CallbackQueryHandler(add_to_cart, pattern=f"^{CALLBACKS['ADD_TO_CART']}:")
    )
    app.add_handler(
        CallbackQueryHandler(view_cart, pattern=f"^{CALLBACKS['VIEW_CART']}$")
    )
    app.add_handler(
        CallbackQueryHandler(
            remove_from_cart, pattern=f"^{CALLBACKS['REMOVE_FROM_CART']}:"
        )
    )
    app.add_handler(
        CallbackQueryHandler(clear_cart, pattern=f"^{CALLBACKS['CLEAR_CART']}$")
    )
    app.add_handler(
        CallbackQueryHandler(checkout, pattern=f"^{CALLBACKS['CHECKOUT']}$")
    )
    app.add_handler(
        CallbackQueryHandler(
            checkout_confirm, pattern=f"^{CALLBACKS['CHECKOUT_CONFIRM']}$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(admin_panel, pattern=f"^{CALLBACKS['ADMIN_PANEL']}$")
    )
    app.add_handler(
        CallbackQueryHandler(admin_orders, pattern=f"^{CALLBACKS['ADMIN_ORDERS']}$")
    )
    app.add_handler(
        CallbackQueryHandler(
            admin_order_detail, pattern=f"^{CALLBACKS['ADMIN_ORDER_DETAIL']}:"
        )
    )
    app.add_handler(
        CallbackQueryHandler(
            admin_order_confirm, pattern=f"^{CALLBACKS['ADMIN_ORDER_CONFIRM']}:"
        )
    )
    app.add_handler(
        CallbackQueryHandler(
            admin_order_cancel, pattern=f"^{CALLBACKS['ADMIN_ORDER_CANCEL']}:"
        )
    )
    app.add_handler(
        CallbackQueryHandler(
            admin_order_done, pattern=f"^{CALLBACKS['ADMIN_ORDER_DONE']}:"
        )
    )
    app.add_handler(
        CallbackQueryHandler(
            admin_list_products, pattern=f"^{CALLBACKS['ADMIN_LIST_PRODUCTS']}$"
        )
    )
    app.add_handler(
        CallbackQueryHandler(
            admin_delete_product, pattern=f"^{CALLBACKS['ADMIN_DELETE_PRODUCT']}:"
        )
    )
    app.add_handler(
        CallbackQueryHandler(admin_promos, pattern=f"^{CALLBACKS['ADMIN_PROMOS']}$")
    )
    app.add_handler(
        CallbackQueryHandler(
            admin_delete_promo, pattern=f"^{CALLBACKS['ADMIN_DELETE_PROMO']}:"
        )
    )

    logger.info("Bot started!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
