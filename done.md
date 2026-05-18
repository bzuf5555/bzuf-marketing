# Done — Bajarilgan Vazifalar Arxivi

## [OPUS] Loyiha arxitekturasi — 2026-05-18
- Professional senior darajada arxitektura dizayn qilindi
- CLAUDE.md qonunlar yozildi
- Token tejash strategiyasi (Opus/Sonnet/Haiku) belgilandi
- Free stack tanlandi: Gemini Flash, MongoDB Atlas, Render, UptimeRobot

## [SONNET] Barcha asosiy kod — 2026-05-18
- main.py, config.py, render.yaml
- agents/: vision, search, token
- handlers/: start, photo, contact
- services/: gemini, uzum, olcha, olx
- database/mongodb.py

## [SONNET] 10 ta marketplace qo'shildi — 2026-05-18
- wildberries_service.py — search.wb.ru JSON API
- ozon_service.py — ozon.uz composer API
- texnomart_service.py, makro_service.py, mediapark_service.py
- tezkor_service.py, asaxiy_service.py
- search_agent.py yangilandi: asyncio.gather 10 parallel

## [HAIKU] Rate Limiting — 2026-05-18
- middleware/rate_limiter.py
- 15 soniya interval, asyncio.Lock bilan thread-safe
- photo_handler.py ga integratsiya

## [SONNET] In-memory TTL Cache — 2026-05-18
- utils/cache.py — TTLCache (30 daqiqa, 500 max entry)
- search_agent.py ga integratsiya: query → cache key
- Bir xil qidiruv qayta API chaqirmaydi

## [OPUS] Query Optimization — 2026-05-18
- gemini_service.py: yangi VISION_PROMPT (temperature=0.05, JSON mime type)
- Yangi field: search_query_ru — Wildberries/Ozon uchun rus tilidagi query
- Yangi field: category — 9 ta kategoriya
- vision_agent.py: search_query_ru qo'shildi
- search_agent.py: WB/Ozon → ru query, qolganlar → uz query
