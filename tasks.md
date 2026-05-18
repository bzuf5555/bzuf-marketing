# Tasks — BzUF Marketing Bot

## [OPUS] Loyiha arxitekturasi va CLAUDE.md
- Barcha komponentlarni professional dizayn qilish
- Token tejash strategiyasini belgilash
- Holat: ✅ Done → done.md ga ko'chirildi

---

## [SONNET] Gemini Vision integratsiyasi
- `services/gemini_service.py` — rasm tahlili
- `agents/vision_agent.py` — tahlil orchestrator
- Prompt engineering: brand, rang, o'lcham, model aniqlash
- Holat: ✅ Done

---

## [SONNET] Marketplace servislar
- `services/uzum_service.py` — Uzum API integratsiyasi
- `services/olcha_service.py` — Olcha.uz scraper
- `services/olx_service.py` — OLX.uz scraper
- Parallel qidiruv (asyncio.gather)
- Holat: ✅ Done

---

## [HAIKU] MongoDB CRUD
- `database/mongodb.py` — motor async driver
- users collection, upsert pattern
- Holat: ✅ Done

---

## [HAIKU] Telegram handlers
- `/start` → kontakt so'rash
- Kontakt → MongoDB saqlash
- Rasm → vision + search pipeline
- Holat: ✅ Done

---

## [SONNET] Render deployment
- `render.yaml` konfiguratsiya
- Webhook setup
- Health check endpoint
- Holat: ✅ Done

---

## Keyingi vazifalar (Backlog)

### [HAIKU] Rate limiting middleware
- Foydalanuvchi so'rovlarini cheklash
- Holat: 📋 Backlog

### [SONNET] Cache qidiruv natijalari
- Redis yoki in-memory cache (bepul)
- Bir xil qidiruv → qayta API chaqirmay
- Holat: 📋 Backlog

### [OPUS] Natijalar sifatini yaxshilash
- Gemini natijasiga asoslanib qidiruv query optimizatsiyasi
- Holat: 📋 Backlog
