import logging

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes

from database.mongodb import user_exists

logger = logging.getLogger(__name__)

WELCOME_TEXT = (
    "👋 <b>Assalomu alaykum!</b>\n\n"
    "Men <b>BzUF Market Bot</b>man 🤖\n\n"
    "📸 Istalgan mahsulot rasmini yuboring — "
    "men uni Uzum Market, Olcha.uz va OLX.uz da topib beraman!\n\n"
    "Davom etish uchun <b>telefon raqamingizni ulashing</b> 👇"
)

ALREADY_REGISTERED_TEXT = (
    "✅ Siz allaqachon ro'yxatdan o'tgansiz!\n\n"
    "📸 Menga mahsulot rasmini yuboring — men uni marketlarda topaman!"
)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return

    already = await user_exists(user.id)

    if already:
        await update.message.reply_text(
            ALREADY_REGISTERED_TEXT,
            parse_mode="HTML",
        )
        logger.info("Returning user: %d", user.id)
        return

    contact_button = KeyboardButton("📱 Telefon raqamni ulashish", request_contact=True)
    keyboard = ReplyKeyboardMarkup(
        [[contact_button]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    await update.message.reply_text(
        WELCOME_TEXT,
        parse_mode="HTML",
        reply_markup=keyboard,
    )
    logger.info("New user /start: %d (@%s)", user.id, user.username)
