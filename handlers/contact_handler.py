import logging

from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes

from database.mongodb import upsert_user

logger = logging.getLogger(__name__)

_SUCCESS_TEXT = """\
✅ <b>Ro'yxatdan o'tdingiz!</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━
📸 <b>Endi mahsulot rasmini yuboring</b>

Qanday ishlaydi:
  1️⃣  Rasm yuboring
  2️⃣  AI mahsulotni tahlil qiladi
  3️⃣  10 ta marketdan qidiradi
  4️⃣  Narx &amp; havola yuboriladi

━━━━━━━━━━━━━━━━━━━━━━━━━━
<i>🟠 Uzum · 🍒 Olcha · 🟢 OLX · 🍇 WB · 🔵 Ozon
⚡ Texnomart · 🛒 Makro · 📺 MediaPark · 🚀 Tezkor · 🛍 Asaxiy</i>\
"""


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
        _SUCCESS_TEXT,
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove(),
    )
    logger.info("Contact saved: user=%d phone=%s", user.id, phone)
