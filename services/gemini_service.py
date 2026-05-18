import logging
from dataclasses import dataclass
from typing import Optional
import json
import re

import google.generativeai as genai

logger = logging.getLogger(__name__)

VISION_PROMPT = """
Siz savdo ekspertisiz. Ushbu rasmda ko'rsatilgan mahsulotni batafsil tahlil qiling.

Quyidagi JSON formatida javob bering (faqat JSON, boshqa narsa yozma):
{
  "item_type": "mahsulot turi (o'zbek tilida)",
  "brand": "brend/ishlab chiqaruvchi yoki null",
  "color": "rang(lar)",
  "size": "o'lcham/razmer yoki null",
  "model": "model nomi/raqami yoki null",
  "condition": "yangi/ishlatilgan/noma'lum",
  "key_features": ["xususiyat 1", "xususiyat 2"],
  "search_query_uz": "uzum va olcha uchun qidiruv so'zi (qisqa, aniq)",
  "search_query_olx": "olx uchun qidiruv so'zi (biroz keng)",
  "description": "mahsulot haqida qisqacha tavsif (2-3 jumla, o'zbek tilida)"
}

Muhim: brand, model, rang, o'lcham kabi tafsilotlarga e'tibor bering.
Agar ko'rinmasa null yozing.
"""


@dataclass
class ImageAnalysis:
    item_type: str
    brand: Optional[str]
    color: str
    size: Optional[str]
    model: Optional[str]
    condition: str
    key_features: list[str]
    search_query_uz: str
    search_query_olx: str
    description: str


async def analyze_image(image_bytes: bytes, api_key: str) -> ImageAnalysis:
    genai.configure(api_key=api_key)
    gemini_model = genai.GenerativeModel("gemini-1.5-flash")

    import PIL.Image
    import io
    image = PIL.Image.open(io.BytesIO(image_bytes))

    response = gemini_model.generate_content(
        [VISION_PROMPT, image],
        generation_config=genai.types.GenerationConfig(
            temperature=0.1,
            max_output_tokens=1024,
        ),
    )

    raw_text = response.text.strip()
    json_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if not json_match:
        raise ValueError(f"Gemini JSON javob bermadi: {raw_text[:200]}")

    data = json.loads(json_match.group())
    logger.info("Gemini tahlil: %s — %s", data.get("item_type"), data.get("brand"))

    return ImageAnalysis(
        item_type=data.get("item_type", "Mahsulot"),
        brand=data.get("brand"),
        color=data.get("color", "noma'lum"),
        size=data.get("size"),
        model=data.get("model"),
        condition=data.get("condition", "noma'lum"),
        key_features=data.get("key_features", []),
        search_query_uz=data.get("search_query_uz", data.get("item_type", "")),
        search_query_olx=data.get("search_query_olx", data.get("item_type", "")),
        description=data.get("description", ""),
    )
