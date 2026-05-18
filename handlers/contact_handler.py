import logging

from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes

from database.mongodb import upsert_user

logger = logging.getLogger(__name__)

SUCCESS_TEXT = (
    "✅ <b>Rahmat! Kontaktingiz saqlandi.</b>\n\n"
    "Endi menga mahsulot rasmini yuboring — "
    "men uni <b>Uzum Market</b>, <b>Olcha.uz</b> va <b>OLX.uz</b> dan topaman! 🛒\n\n"
    "📸 Rasm yuboring..."
)


async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    contact = update.effective_message.contact
    user = update.effective_user

    if not contact or not user:
        return

    phone = contact.phone_number
    if not phone.startswith("+"):
        phone = "+" + phone

    await upsert_user(
        user_id=user.id,
        phone=phone,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
    )

    await update.message.reply_text(
        SUCCESS_TEXT,
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove(),
    )
    logger.info("Contact saved: %d — %s", user.id, phone)
