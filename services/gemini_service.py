"""
[OPUS] Gemini Vision Service — rasm tahlili.
BUG FIX: sync PIL va genai calls → asyncio.to_thread (event loop bloklanmaydi)
BUG FIX: genai.configure() faqat bir marta chaqiriladi
"""
import asyncio
import io
import json
import logging
import re
from dataclasses import dataclass
from typing import Optional

import google.generativeai as genai
import PIL.Image

logger = logging.getLogger(__name__)

_configured = False


def _ensure_configured(api_key: str) -> None:
    global _configured
    if not _configured:
        genai.configure(api_key=api_key)
        _configured = True


VISION_PROMPT = """
Siz professional e-commerce ekspertisiz. Rasmni diqqat bilan ko'rib chiqing.

Faqat quyidagi JSON formatida javob bering (JSON blokidan tashqari hech narsa yozma):

{
  "item_type": "mahsulot turi (o'zbek tilida, masalan: velosiped, noutbuk, kiyim)",
  "category": "electronics|clothing|sports|home|beauty|food|auto|tools|toys|other",
  "brand": "brend nomi yoki null",
  "color": "asosiy rang(lar)",
  "size": "o'lcham, hajm yoki null",
  "model": "model nomi/raqami yoki null",
  "condition": "yangi|ishlatilgan|noma'lum",
  "key_features": ["eng muhim xususiyat 1", "xususiyat 2", "xususiyat 3"],
  "search_query_uz": "o'zbek tilida qidiruv (uzum/olcha/texnomart uchun, 2-4 so'z)",
  "search_query_ru": "поисковый запрос на русском (для Wildberries и Ozon, 2-4 слова)",
  "search_query_olx": "o'zbek tilida keng qidiruv (olx classifieds uchun, 1-3 so'z)",
  "description": "mahsulot haqida 2 jumlali tavsif o'zbek tilida"
}

Qoidalar:
- brand ko'rinmasa null yoz, taxmin qilma
- search_query_uz: brend+model+rang kombinatsiyasi bo'lsa aniqroq
- search_query_ru: rus tilidagi marketlar uchun, ruscha terminlar ishlatilsa yaxshiroq
- category: faqat berilgan 9 ta variantdan birini tanlash shart
- key_features: 3 ta, mahsulotni boshqasidan farq qiladigan xususiyatlar
"""


@dataclass
class ImageAnalysis:
    item_type: str
    category: str
    brand: Optional[str]
    color: str
    size: Optional[str]
    model: Optional[str]
    condition: str
    key_features: list[str]
    search_query_uz: str
    search_query_ru: str
    search_query_olx: str
    description: str


def _sync_analyze(image_bytes: bytes, api_key: str) -> ImageAnalysis:
    """Sync funksiya — asyncio.to_thread orqali chaqiriladi."""
    _ensure_configured(api_key)

    model = genai.GenerativeModel(
        "gemini-2.0-flash",
        generation_config=genai.types.GenerationConfig(
            temperature=0.05,
            max_output_tokens=1024,
            response_mime_type="application/json",
        ),
    )

    image = PIL.Image.open(io.BytesIO(image_bytes))
    if max(image.size) > 1280:
        image.thumbnail((1280, 1280), PIL.Image.LANCZOS)

    response = model.generate_content([VISION_PROMPT, image])
    raw_text = response.text.strip()

    json_match = re.search(r"\{[\s\S]*\}", raw_text)
    if not json_match:
        raise ValueError(f"Gemini JSON qaytarmadi: {raw_text[:200]}")

    data = json.loads(json_match.group())

    return ImageAnalysis(
        item_type=data.get("item_type", "Mahsulot"),
        category=data.get("category", "other"),
        brand=data.get("brand") or None,
        color=data.get("color", "noma'lum"),
        size=data.get("size") or None,
        model=data.get("model") or None,
        condition=data.get("condition", "noma'lum"),
        key_features=data.get("key_features", []),
        search_query_uz=data.get("search_query_uz") or data.get("item_type", ""),
        search_query_ru=data.get("search_query_ru") or data.get("item_type", ""),
        search_query_olx=data.get("search_query_olx") or data.get("item_type", ""),
        description=data.get("description", ""),
    )


async def analyze_image(image_bytes: bytes, api_key: str) -> ImageAnalysis:
    """Async wrapper — event loop ni bloklamaydi."""
    analysis = await asyncio.to_thread(_sync_analyze, image_bytes, api_key)
    logger.info(
        "Vision: %s | brand=%s | cat=%s | uz='%s' | ru='%s'",
        analysis.item_type, analysis.brand, analysis.category,
        analysis.search_query_uz, analysis.search_query_ru,
    )
    return analysis
