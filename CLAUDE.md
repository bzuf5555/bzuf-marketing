# CLAUDE.md — BzUF Marketing Telegram Bot

## Loyiha haqida
Telegram bot: foydalanuvchi rasm yuboradi → Gemini Vision tahlil qiladi → Uzum, Olcha, OLX da qidiradi → natija qaytaradi.

## Arxitektura

```
main.py                  # Webhook entry point (Render)
config.py                # Barcha env o'zgaruvchilar
agents/
  vision_agent.py        # Gemini Vision — rasm tahlili
  search_agent.py        # Marketplace qidiruv orchestrator
  token_agent.py         # Model tanlash (Opus/Sonnet/Haiku)
handlers/
  start_handler.py       # /start — kontakt so'rash
  photo_handler.py       # Rasm qabul va qayta ishlash
  contact_handler.py     # Kontakt saqlash
services/
  gemini_service.py      # Google Gemini Vision API
  uzum_service.py        # uzum.uz scraper/API
  olcha_service.py       # olcha.uz scraper
  olx_service.py         # olx.uz scraper
database/
  mongodb.py             # MongoDB Atlas CRUD
tasks.md                 # Joriy vazifalar (model belgilanadi)
done.md                  # Bajarilgan vazifalar arxivi
```

## Qonunlar (Senior Darajadagi Standartlar)

### 1. Kod yozish
- **Barcha kod async/await** — bot to'liq asynchronous ishlaydi
- **Type hints majburiy** — har bir funksiya parametri va return type belgilanadi
- **Har bir servis o'z exception** handling qiladi, xatolar yuqoriga ko'tarilmaydi
- **Loglash**: `logging` moduli, har bir agentda `logger = logging.getLogger(__name__)`
- **Magic number yo'q** — barcha konstantalar `config.py` da
- **Import tartibi**: stdlib → third-party → local

### 2. Token Tejash (token_agent.py orqali)
```
Murakkablik darajasi → Model
HIGH   (arxitektura, vision prompt)    → claude-opus-4-7
MEDIUM (qidiruv, scraping, format)     → claude-sonnet-4-6
LOW    (CRUD, oddiy format, log)       → claude-haiku-4-5
```
- Har bir agent `token_agent.py`dan model oladi
- Gemini Flash (bepul) — rasm tahlili uchun asosiy AI
- Claude faqat agent orchestration va prompt yaxshilash uchun

### 3. Tasks boshqaruvi
- Yangi vazifa: `tasks.md` ga `[OPUS/SONNET/HAIKU]` belgisi bilan yoz
- Bajarilgan: `tasks.md`dan o'chirib `done.md`ga ko'chir
- Format: `## [MODEL] Vazifa nomi\n- Tavsif\n- Holat: Done/Progress`

### 4. Xavfsizlik
- **Hech qachon** token, API key, MongoDB URI ni kodga yozma
- Barcha sirlar `.env` faylda, `.gitignore` da
- Bot token GitHub ga push bo'lmasligi shart
- `.env.example` — faqat kalit nomlar, qiymat yo'q

### 5. Deployment (Render)
- **Webhook mode** — polling emas (Render free tier uchun samaraliroq)
- Health check endpoint: `GET /health` → `{"status": "ok"}`
- `render.yaml` orqali avtomatik deploy
- UptimeRobot bilan har 5 daqiqada ping (bepul 24/7)
- PORT: Render avtomatik beradi `os.environ["PORT"]`

### 6. Marketplace qidiruv
- Barcha qidiruv **parallel** (asyncio.gather)
- Har bir servis maksimum **5 natija** qaytaradi
- Timeout: har bir so'rov uchun **10 soniya**
- Agar servis ishlamasa, o'sha servis natijasi o'tkazib yuboriladi (fail-soft)

### 7. MongoDB
- Collection: `users` — kontaktlar saqlanadi
- Unique index: `user_id` (Telegram user ID)
- Upsert pattern — dublikat yo'q
- Connection pooling: `motor` (async MongoDB driver)

### 8. Rate Limiting
- Gemini free: 60 req/min, 1500 req/day
- Foydalanuvchi so'rovlari orasida minimum 2 soniya kutish
- `asyncio.Semaphore` bilan parallel so'rovlarni cheklash

## Free Stack
| Xizmat | Bepul limit | Maqsad |
|--------|-------------|--------|
| Google Gemini Flash | 1500 req/day | Rasm tahlili |
| MongoDB Atlas M0 | 512MB | Kontaktlar |
| Render Free | 750h/month | Hosting |
| UptimeRobot | 50 monitor | Uyqu oldini olish |
| GitHub | Unlimited | Kod |

## Yangi agent qo'shish tartibi
1. `agents/` papkasida yangi fayl
2. `token_agent.py`dan model ol
3. `tasks.md`ga vazifani yoz
4. `main.py`da import qil
5. Bajarilgach `done.md`ga ko'chir
