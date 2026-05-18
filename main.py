import logging
from aiohttp import web

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    TypeHandler,
    filters,
)

from config import load_config
from database.mongodb import connect as db_connect, disconnect as db_disconnect
from handlers.start_handler import start_command
from handlers.contact_handler import contact_handler
from handlers.photo_handler import photo_handler
from middleware.registration_check import enforce_registration

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def health_check(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok", "bot": "bzuf-marketing"})


async def post_init(application: Application) -> None:
    config = application.bot_data["config"]
    await db_connect(config.MONGODB_URI)
    logger.info("Bot initialized — webhook mode: %s", bool(config.RENDER_EXTERNAL_URL))


async def post_shutdown(application: Application) -> None:
    await db_disconnect()
    logger.info("Bot shut down")


def main() -> None:
    config = load_config()

    application = (
        Application.builder()
        .token(config.BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    application.bot_data["config"] = config
    application.bot_data["gemini_api_key"] = config.GEMINI_API_KEY

    # group=-1 — barcha updatelardan OLDIN ishga tushadi
    # Ro'yxatdan o'tmagan foydalanuvchini /start va contact dan boshqa hamma narsadan to'sadi
    application.add_handler(TypeHandler(Update, enforce_registration), group=-1)

    # Asosiy handlerlar (group=0, default)
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    application.add_handler(MessageHandler(filters.PHOTO, photo_handler))

    if config.RENDER_EXTERNAL_URL:
        webhook_url = f"https://{config.RENDER_EXTERNAL_URL}/{config.BOT_TOKEN}"
        application.run_webhook(
            listen="0.0.0.0",
            port=config.PORT,
            url_path=config.BOT_TOKEN,
            webhook_url=webhook_url,
            secret_token=config.WEBHOOK_SECRET,
            allowed_updates=Update.ALL_TYPES,
        )
        logger.info("Webhook: %s", webhook_url)
    else:
        logger.info("Polling mode (local)")
        application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
