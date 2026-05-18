import asyncio
import logging
from time import time

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ChatAction

from database.mongodb import user_exists, increment_search_count
from agents.vision_agent import process_image
from agents.search_agent import search_all_markets, format_results_message

logger = logging.getLogger(__name__)

NOT_REGISTERED_TEXT = (
    "⚠️ Avval ro'yxatdan o'ting!\n\n"
    "/start buyrug'ini yuboring va telefon raqamingizni ulashing."
)

PROCESSING_TEXT = "🔍 Rasm tahlil qilinmoqda, iltimos kuting..."


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.effective_message

    if not user or not message or not message.photo:
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
        image_bytes = await file.download_as_bytearray()
        image_bytes = bytes(image_bytes)

        gemini_api_key: str = context.bot_data["gemini_api_key"]
        config = context.bot_data["config"]

        await context.bot.send_chat_action(chat_id=message.chat_id, action=ChatAction.TYPING)

        vision_result = await process_image(image_bytes, gemini_api_key)

        await context.bot.send_chat_action(chat_id=message.chat_id, action=ChatAction.TYPING)

        search_results = await search_all_markets(
            vision=vision_result,
            max_results=config.MAX_SEARCH_RESULTS,
            timeout=config.SEARCH_TIMEOUT,
        )

        result_text = format_results_message(search_results)

        keyboard = None
        if search_results.all_results:
            first = search_results.all_results[0]
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    f"🛒 {first.source} da ko'rish",
                    url=first.product_url,
                )]
            ])

        await processing_msg.delete()

        if search_results.all_results and search_results.all_results[0].image_url:
            try:
                await message.reply_photo(
                    photo=search_results.all_results[0].image_url,
                    caption=result_text,
                    parse_mode="HTML",
                    reply_markup=keyboard,
                )
            except Exception:
                await message.reply_text(
                    result_text,
                    parse_mode="HTML",
                    reply_markup=keyboard,
                    disable_web_page_preview=False,
                )
        else:
            await message.reply_text(
                result_text,
                parse_mode="HTML",
                reply_markup=keyboard,
                disable_web_page_preview=False,
            )

        await increment_search_count(user.id)
        logger.info("Photo processed for user %d: %s", user.id, vision_result.display_title)

    except ValueError as e:
        await processing_msg.delete()
        await message.reply_text(
            "😔 Rasmdan mahsulotni aniqlay olmadim. Boshqa rasm yuboring.",
        )
        logger.warning("Vision error for user %d: %s", user.id, e)

    except Exception as e:
        await processing_msg.delete()
        await message.reply_text(
            "❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
        )
        logger.error("Photo handler error for user %d: %s", user.id, e, exc_info=True)
