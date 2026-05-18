import logging

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatAction

from database.mongodb import user_exists, increment_search_count
from agents.vision_agent import process_image
from agents.search_agent import search_all_markets, format_results_message, get_best_image
from middleware.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)

# Telegram caption limiti 1024 char — header bu limitdan oshib ketmasligi uchun
_CAPTION_LIMIT = 900

_STEP1 = (
    "┌──────────────────────────┐\n"
    "│  🔍  Rasm tahlil qilinmoqda  │\n"
    "└──────────────────────────┘\n\n"
    "⏳ AI skannerlamoqda..."
)

_STEP2 = (
    "┌──────────────────────────┐\n"
    "│  🔍  Rasm tahlil qilinmoqda  │\n"
    "└──────────────────────────┘\n\n"
    "✅ Mahsulot aniqlandi\n"
    "⏳ 10 ta marketdan qidirilmoqda..."
)

_RATE_LIMIT_TPL = (
    "⏳ <b>Biroz kuting</b>\n\n"
    "Keyingi qidiruv <b>{sec:.0f} soniyadan</b> so'ng.\n"
    "<i>Sifatli natija uchun cheklov mavjud.</i>"
)


async def _safe_delete(message) -> None:
    """BUG FIX: delete xatosini jimgina o'tkazib yuboradi."""
    try:
        await message.delete()
    except Exception:
        pass


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.effective_message

    if not user or not message or not message.photo:
        return

    wait = await rate_limiter.check(user.id)
    if wait > 0:
        await message.reply_text(
            _RATE_LIMIT_TPL.format(sec=wait),
            parse_mode="HTML",
        )
        return

    progress = await message.reply_text(_STEP1)
    await context.bot.send_chat_action(chat_id=message.chat_id, action=ChatAction.TYPING)

    try:
        photo = message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        image_bytes = bytes(await file.download_as_bytearray())

        gemini_api_key: str = context.bot_data["gemini_api_key"]
        config = context.bot_data["config"]

        vision_result = await process_image(image_bytes, gemini_api_key)

        await progress.edit_text(_STEP2)
        await context.bot.send_chat_action(chat_id=message.chat_id, action=ChatAction.TYPING)

        search_results = await search_all_markets(
            vision=vision_result,
            max_results=config.MAX_SEARCH_RESULTS,
            timeout=config.SEARCH_TIMEOUT,
        )

        msgs = format_results_message(search_results)
        best_image = get_best_image(search_results)
        header_text = msgs[0]

        await _safe_delete(progress)

        # BUG FIX: caption > 900 char bo'lsa, rasmni captionsiz, textni alohida yuboramiz
        if best_image and search_results.total_found > 0:
            if len(header_text) <= _CAPTION_LIMIT:
                try:
                    await message.reply_photo(
                        photo=best_image,
                        caption=header_text,
                        parse_mode="HTML",
                    )
                except Exception:
                    await message.reply_text(
                        header_text,
                        parse_mode="HTML",
                        disable_web_page_preview=True,
                    )
            else:
                # Rasm alohida, tavsif alohida
                try:
                    await message.reply_photo(photo=best_image)
                except Exception:
                    pass
                await message.reply_text(
                    header_text,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
        else:
            await message.reply_text(
                header_text,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )

        for market_msg in msgs[1:]:
            await context.bot.send_chat_action(chat_id=message.chat_id, action=ChatAction.TYPING)
            await message.reply_text(
                market_msg,
                parse_mode="HTML",
                disable_web_page_preview=False,
            )

        await increment_search_count(user.id)
        logger.info(
            "Done: user=%d item='%s' markets=%d total=%d cache=%s",
            user.id, vision_result.display_title,
            len(search_results.results_by_source),
            search_results.total_found,
            search_results.from_cache,
        )

    except ValueError as e:
        await _safe_delete(progress)
        await message.reply_text(
            "┌─────────────────────────┐\n"
            "│  😔  Mahsulot aniqlanmadi  │\n"
            "└─────────────────────────┘\n\n"
            "Quyidagilarni sinab ko'ring:\n"
            "  • Yaxshiroq yorug'likda surating\n"
            "  • Mahsulot aniq ko'rinsin\n"
            "  • Fon shovqini kamaytiring"
        )
        logger.warning("Vision error user=%d: %s", user.id, e)

    except Exception as e:
        await _safe_delete(progress)
        await message.reply_text("❌ Xatolik yuz berdi.\nIltimos, qayta urinib ko'ring.")
        logger.error("Photo error user=%d: %s", user.id, e, exc_info=True)
