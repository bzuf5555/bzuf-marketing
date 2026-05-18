"""
Global registration enforcement.
Ro'yxatdan o'tmagan foydalanuvchi /start va contact dan
boshqa hech narsa qila olmaydi — kontakt talab qilinadi.
"""
import logging

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, ApplicationHandlerStop

from database.mongodb import user_exists

logger = logging.getLogger(__name__)

_CONTACT_REMINDER = (
    "👋 Siz hali ro'yxatdan o'tmagansiz!\n\n"
    "Botdan foydalanish uchun <b>telefon raqamingizni ulashing</b> 👇"
)


def _contact_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton("📱 Telefon raqamni ulashish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Telefon raqamni ulashish uchun tugmani bosing",
    )


async def enforce_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user

    if not message or not user:
        return

    # /start va contact ulashish — o'tkazib yuboriladi
    if message.text and message.text.startswith("/start"):
        return
    if message.contact:
        return

    registered = await user_exists(user.id)
    if not registered:
        await message.reply_text(
            _CONTACT_REMINDER,
            parse_mode="HTML",
            reply_markup=_contact_keyboard(),
        )
        logger.info("Unregistered user %d blocked: %s", user.id, message.text or "[non-text]")
        raise ApplicationHandlerStop
