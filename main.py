import asyncio
import logging
import signal

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


def _build_application(config) -> Application:
    application = (
        Application.builder()
        .token(config.BOT_TOKEN)
        .build()
    )
    application.bot_data["config"] = config
    application.bot_data["gemini_api_key"] = config.GEMINI_API_KEY

    application.add_handler(TypeHandler(Update, enforce_registration), group=-1)
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    application.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    return application


async def _webhook_handler(request: web.Request, application: Application) -> web.Response:
    """Telegram update ni qabul qiladi va application queue ga uzatadi."""
    try:
        secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        config = application.bot_data["config"]
        if secret != config.WEBHOOK_SECRET:
            return web.Response(status=403)
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.update_queue.put(update)
    except Exception as e:
        logger.error("Webhook request error: %s", e)
    return web.Response(status=200)


async def _health_handler(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok", "bot": "bzuf-marketing"})


async def _run_webhook(config) -> None:
    application = _build_application(config)

    base = config.RENDER_EXTERNAL_URL.rstrip("/")
    if not base.startswith("http"):
        base = f"https://{base}"
    webhook_url = f"{base}/{config.BOT_TOKEN}"

    async with application:
        await db_connect(config.MONGODB_URI)
        await application.start()
        await application.bot.set_webhook(
            url=webhook_url,
            secret_token=config.WEBHOOK_SECRET,
            allowed_updates=Update.ALL_TYPES,
        )
        logger.info("Webhook: %s", webhook_url)

        # aiohttp server — webhook + /health ikkalasi
        aioapp = web.Application()
        aioapp.router.add_post(f"/{config.BOT_TOKEN}",
                               lambda r: _webhook_handler(r, application))
        aioapp.router.add_get("/health", _health_handler)

        runner = web.AppRunner(aioapp)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", config.PORT)
        await site.start()
        logger.info("Server listening on port %d", config.PORT)

        stop_event = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, stop_event.set)
            except NotImplementedError:
                pass  # Windows da signal handler yo'q

        await stop_event.wait()
        await runner.cleanup()
        await application.stop()
        await db_disconnect()


def _run_polling(config) -> None:
    application = _build_application(config)

    async def _post_init(app: Application) -> None:
        await db_connect(config.MONGODB_URI)

    async def _post_shutdown(app: Application) -> None:
        await db_disconnect()

    application.post_init = _post_init
    application.post_shutdown = _post_shutdown

    logger.info("Polling mode (local development)")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


def main() -> None:
    config = load_config()
    if config.RENDER_EXTERNAL_URL:
        asyncio.run(_run_webhook(config))
    else:
        _run_polling(config)


if __name__ == "__main__":
    main()
