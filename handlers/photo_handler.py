import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ChatAction

from database.mongodb import user_exists, increment_search_count
from agents.vision_agent import process_image
from agents.search_agent import search_all_markets, format_results_message, get_best_image
from middleware.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)

NOT_REGISTERED_TEXT = (
    "⚠️ Avval ro'yxatdan o'ting!\n\n"
    "/start buyrug'ini yuboring va telefon raqamingizni ulashing."
)

PROCESSING_TEXT = (
    "🔍 Rasm tahlil qilinmoqda...\n"
    "⏳ 10 ta marketdan parallel qidirilmoqda."
)


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.effective_message

    if not user or not message or not message.photo:
        return

    # Rate limit tekshirish
    wait_seconds = await rate_limiter.check(user.id)
    if wait_seconds > 0:
        await message.reply_text(
            f"⏳ Iltimos, {wait_seconds:.0f} soniya kuting.\n"
            f"Tez-tez so'rov yubormaslik uchun cheklov mavjud."
        )
        return

    registered = await user_exists(user.id)
    if not registered:
        await message.reply_text(NOT_REGISTERED_TEXT)
        return

    processing_msg = await message.reply_text(PROCESSING_TEXT)
    await context.bot.send_chat_action(chat_id=message.chat_id, action=ChatAction.TYPING)

    try:
        photo = message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        image_bytes = bytes(await file.download_as_bytearray())

        gemini_api_key: str = context.bot_data["gemini_api_key"]
        config = context.bot_data["config"]

        vision_result = await process_image(image_bytes, gemini_api_key)
        await context.bot.send_chat_action(chat_id=message.chat_id, action=ChatAction.TYPING)

        search_results = await search_all_markets(
            vision=vision_result,
            max_results=config.MAX_SEARCH_RESULTS,
            timeout=config.SEARCH_TIMEOUT,
        )

        messages = format_results_message(search_results)
        best_image = get_best_image(search_results)

        await processing_msg.delete()

        # Birinchi xabar — tavsif + statistika
        first_msg = messages[0]
        if best_image:
            try:
                await message.reply_photo(
                    photo=best_image,
                    caption=first_msg,
                    parse_mode="HTML",
                )
            except Exception:
                await message.reply_text(first_msg, parse_mode="HTML", disable_web_page_preview=True)
        else:
            await message.reply_text(first_msg, parse_mode="HTML", disable_web_page_preview=True)

        # Har bir marketplace uchun alohida xabar
        for market_msg in messages[1:]:
            await context.bot.send_chat_action(chat_id=message.chat_id, action=ChatAction.TYPING)
            await message.reply_text(
                market_msg,
                parse_mode="HTML",
                disable_web_page_preview=False,
            )

        await increment_search_count(user.id)
        logger.info(
            "Done: user=%d item='%s' markets=%d results=%d cache=%s",
            user.id,
            vision_result.display_title,
            len(search_results.results_by_source),
            search_results.total_found,
            search_results.from_cache,
        )

    except ValueError as e:
        await processing_msg.delete()
        await message.reply_text(
            "😔 Rasmdan mahsulotni aniqlay olmadim.\n"
            "Yaxshiroq yorug'lik bilan qayta urinib ko'ring."
        )
        logger.warning("Vision error user=%d: %s", user.id, e)

    except Exception as e:
        await processing_msg.delete()
        await message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")
        logger.error("Photo error user=%d: %s", user.id, e, exc_info=True)
