import logging

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from database.mongodb import user_exists

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
#  Yangi foydalanuvchi uchun welcome ekrani
# ─────────────────────────────────────────
_WELCOME_NEW = """\
╔══════════════════════════╗
║   🛍  <b>BzUF Market Bot</b>    ║
╚══════════════════════════╝

Salom, <b>{name}</b>! 👋

<i>Mahsulot rasmi yuboring — O'zbekistondagi
10 ta yirik marketdan topib beraman!</i>

━━━━━━━━━━━━━━━━━━━━━━━━━━
🟠 Uzum    🍒 Olcha    🟢 OLX
🍇 WB      🔵 Ozon     ⚡ Texnomart
🛒 Makro   📺 MediaPk  🚀 Tezkor  🛍 Asaxiy
━━━━━━━━━━━━━━━━━━━━━━━━━━

🔐 Davom etish uchun <b>telefon raqamingizni</b>
ulashing — ma'lumotlaringiz xavfsiz saqlanadi.\
"""

# ─────────────────────────────────────────
#  Qaytib kelgan foydalanuvchi
# ─────────────────────────────────────────
_WELCOME_BACK = """\
╔══════════════════════════╗
║   🛍  <b>BzUF Market Bot</b>    ║
╚══════════════════════════╝

Qaytib keldingiz, <b>{name}</b>! 🎉

━━━━━━━━━━━━━━━━━━━━━━━━━━
📸 <b>Mahsulot rasmini yuboring</b>

Misol:
  🚲 Velosiped → barcha o'lcham &amp; narxlar
  💻 Noutbuk   → brend variantlari
  👟 Kiyim     → rang &amp; o'lchamlar

10 ta market — <b>bir zumda</b> ⚡\
"""


def _contact_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton("📱 Telefon raqamni ulashish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Telefon raqamni ulashish uchun bosing...",
    )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return

    name = user.first_name or "Do'st"

    already_registered = await user_exists(user.id)

    if already_registered:
        await update.message.reply_text(
            _WELCOME_BACK.format(name=name),
            parse_mode="HTML",
        )
        logger.info("Returning user /start: %d (@%s)", user.id, user.username)
        return

    await update.message.reply_text(
        _WELCOME_NEW.format(name=name),
        parse_mode="HTML",
        reply_markup=_contact_keyboard(),
    )
    logger.info("New user /start: %d (@%s)", user.id, user.username)
