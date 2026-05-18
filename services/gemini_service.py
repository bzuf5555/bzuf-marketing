"""
[OPUS] Gemini Vision Service — professional mahsulot tahlili.
gemini-2.5-flash bilan maksimal aniqlik:
- Aniq brend/model aniqlash (iPhone 17 Air ≠ Xiaomi)
- Brend+model topilsa MAJBURIY aniq query ishlatiladi
- GeminiQuotaError: 429 uchun retry mexanizmi
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


class GeminiQuotaError(Exception):
    def __init__(self, retry_after: int = 65):
        self.retry_after = retry_after
        super().__init__(f"Gemini quota, retry in {retry_after}s")


def _ensure_configured(api_key: str) -> None:
    global _configured
    if not _configured:
        genai.configure(api_key=api_key)
        _configured = True


# ─────────────────────────────────────────────────────────────────
#  PROFESSIONAL VISION PROMPT — aniq brend/model aniqlash uchun
# ─────────────────────────────────────────────────────────────────
VISION_PROMPT = """
Siz dunyo darajasidagi mahsulot tahlil qiluvchi AI ekspertisiz.
Rasmni MAKSIMAL aniqlik va professional darajada tahlil qiling.

## ASOSIY QOIDALAR:

### Smartfonlar uchun:
- Apple iPhone: Dynamic Island/notch shakli, kamera bloki (1/2/3 kamera),
  titanium/aluminum rama rangi, USB-C yoki Lightning, Action tugmasi,
  ultrathin profil (iPhone 17 Air), logotip joylashuvi
- Samsung Galaxy: kamera joylashuvi (S/A/Z seriya farqi), dizayn tili
- Xiaomi/POCO/Redmi: brend logotipi (MI/POCO), kamera moduli shakli
- HECH QACHON boshqa brendni iPhone deb yoki Xiaomi deb adashtirmang

### Elektronika uchun:
- Noutbuk: olma/Dell/HP/Lenovo logotipi, klaviatura tartibi, ekran nisbati
- Televizor: brend logotipi (LG/Samsung/Sony/Xiaomi), ekran o'lchami
- Konditsioner: brend, BTU/kVt quvvati

### Boshqa mahsulotlar:
- Kiyim/poyabzal: brend, rang, o'lcham (ko'rinsa)
- Mebel/uy jihozlari: materiallar, o'lcham, rang
- Oziq-ovqat: mahsulot nomi, brend, hajm

## MUHIM: Qidiruv so'zlari ANIQ bo'lishi SHART!
- ❌ YOMON: "telefon", "smartfon", "konditsioner"
- ✅ YAXSHI: "Apple iPhone 17 Air", "Samsung Galaxy S25 Ultra", "LG 12000 BTU"
- Agar brend+model aniq bo'lsa — aynan shuni qidiruv so'zi sifatida ishlating!

## JAVOB FORMATI — FAQAT JSON (markdown, izoh yozmang):

{
  "item_type": "to'liq mahsulot nomi o'zbek tilida (masalan: Apple iPhone 17 Air smartfon)",
  "category": "electronics|clothing|sports|home|beauty|food|auto|tools|toys|other",
  "brand": "ANIQ brend nomi (Apple, Samsung, Xiaomi, LG, Nike...) yoki null",
  "model": "ANIQ model nomi (iPhone 17 Air, Galaxy S25, Redmi Note 14...) yoki null",
  "color": "asosiy rang(lar) — aniq (Titanium Black, Desert Titanium, ko'k...)",
  "storage": "xotira hajmi agar ko'rinsa (128GB, 256GB, 512GB, 1TB) yoki null",
  "size": "o'lcham yoki ekran diagonali (6.7 dyuym, 55 dyuym...) yoki null",
  "condition": "yangi|ishlatilgan|noma'lum",
  "key_features": [
    "1-xususiyat: texnik aniq (masalan: Triple kamera tizimi, Dynamic Island)",
    "2-xususiyat: aniq (masalan: Titanium rama, USB-C port)",
    "3-xususiyat: aniq (masalan: 6.9 dyuym Super Retina XDR displey)"
  ],
  "confidence": "high|medium|low",
  "search_query_uz": "ANIQ qidiruv o'zbek tilida — brand+model+rang (Apple iPhone 17 Air Titanium)",
  "search_query_ru": "ТОЧНЫЙ запрос на русском — brand+model+цвет (Apple iPhone 17 Air Titanium)",
  "search_query_olx": "qisqa klassifikatsiya qidiruvi (iPhone 17 Air)",
  "description": "mahsulot haqida aniq 2 jumlali tavsif o'zbek tilida"
}

MISOL — Agar siz Apple iPhone 17 Air rasmini ko'rsangiz:
brand='Apple', model='iPhone 17 Air', search_query_uz='Apple iPhone 17 Air',
search_query_ru='Apple iPhone 17 Air'. XIAOMI yoki boshqa narsani yozmang.
"""


@dataclass
class ImageAnalysis:
    item_type: str
    category: str
    brand: Optional[str]
    model: Optional[str]
    color: str
    storage: Optional[str]
    size: Optional[str]
    condition: str
    key_features: list[str]
    confidence: str
    search_query_uz: str
    search_query_ru: str
    search_query_olx: str
    description: str


def _build_smart_query(data: dict) -> tuple[str, str, str]:
    """
    Brend+model aniqlanganida MAJBURIY aniq query hosil qiladi.
    Bu Xiaomi/konditsioner kabi noto'g'ri natijalarni to'sadi.
    """
    brand = data.get("brand") or ""
    model = data.get("model") or ""
    color = data.get("color") or ""
    item_type = data.get("item_type", "Mahsulot")

    # Brend va model ikkalasi topilgan — eng aniq query
    if brand and model:
        base = f"{brand} {model}"
        color_part = f" {color}" if color and color.lower() not in ("noma'lum", "unknown", "") else ""
        uz_query = f"{base}{color_part}"
        ru_query = data.get("search_query_ru") or base
        # Agar ru query generic bo'lsa, brend+model ni ishlatamiz
        if not ru_query or len(ru_query) < 5 or any(g in ru_query.lower() for g in ["телефон", "смартфон", "устройство"]):
            ru_query = base
        olx_query = base
    elif brand:
        # Faqat brend topilgan
        uz_query = data.get("search_query_uz") or brand
        ru_query = data.get("search_query_ru") or brand
        olx_query = brand
    else:
        # Brend yo'q — Gemini generatsiyasidan foydalanamiz
        uz_query = data.get("search_query_uz") or item_type
        ru_query = data.get("search_query_ru") or item_type
        olx_query = data.get("search_query_olx") or item_type

    return uz_query.strip(), ru_query.strip(), olx_query.strip()


def _sync_analyze(image_bytes: bytes, api_key: str) -> ImageAnalysis:
    _ensure_configured(api_key)

    model = genai.GenerativeModel(
        "gemini-2.5-flash",
        generation_config=genai.types.GenerationConfig(
            temperature=0.05,     # Past temp = izchil, aniq natija
            max_output_tokens=2048,
        ),
    )

    image = PIL.Image.open(io.BytesIO(image_bytes))
    if max(image.size) > 1920:
        image.thumbnail((1920, 1920), PIL.Image.LANCZOS)

    response = model.generate_content([VISION_PROMPT, image])
    raw_text = response.text.strip()

    # gemini-2.5-flash thinking mode — JSON markdown blok yoki to'g'ridan-to'g'ri
    code_block = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", raw_text)
    if code_block:
        json_str = code_block.group(1)
    else:
        json_match = re.search(r"\{[\s\S]*\}", raw_text)
        if not json_match:
            raise ValueError(f"Gemini JSON qaytarmadi: {raw_text[:300]}")
        json_str = json_match.group()

    data = json.loads(json_str)

    # Smart query builder — brend+model aniq bo'lsa generic query o'rnini bosadi
    uz_query, ru_query, olx_query = _build_smart_query(data)

    analysis = ImageAnalysis(
        item_type=data.get("item_type", "Mahsulot"),
        category=data.get("category", "other"),
        brand=data.get("brand") or None,
        model=data.get("model") or None,
        color=data.get("color", "noma'lum"),
        storage=data.get("storage") or None,
        size=data.get("size") or None,
        condition=data.get("condition", "noma'lum"),
        key_features=data.get("key_features", [])[:3],
        confidence=data.get("confidence", "medium"),
        search_query_uz=uz_query,
        search_query_ru=ru_query,
        search_query_olx=olx_query,
        description=data.get("description", ""),
    )
    return analysis


async def analyze_image(image_bytes: bytes, api_key: str) -> ImageAnalysis:
    try:
        analysis = await asyncio.to_thread(_sync_analyze, image_bytes, api_key)
    except Exception as e:
        err_str = str(e)
        if "ResourceExhausted" in type(e).__name__ or "429" in err_str:
            retry_after = 65
            m = re.search(r"retry in (\d+(?:\.\d+)?)", err_str, re.IGNORECASE)
            if m:
                retry_after = int(float(m.group(1))) + 5
            logger.warning("Gemini 429 — retry after %ds", retry_after)
            raise GeminiQuotaError(retry_after) from e
        raise

    logger.info(
        "Vision ✅ | item='%s' brand='%s' model='%s' conf=%s | uz='%s' | ru='%s'",
        analysis.item_type, analysis.brand, analysis.model,
        analysis.confidence, analysis.search_query_uz, analysis.search_query_ru,
    )
    return analysis
