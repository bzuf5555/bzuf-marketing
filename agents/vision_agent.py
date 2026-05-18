"""
[OPUS] Vision Agent — professional mahsulot tahlili orchestratori.
- Aniq brend+model qidiruv → noto'g'ri natija yo'q
- confidence past bo'lsa foydalanuvchiga ogohlantirish
"""
import logging
from dataclasses import dataclass

from services.gemini_service import ImageAnalysis, analyze_image
from agents.token_agent import get_model, log_task_to_md

logger = logging.getLogger(__name__)


@dataclass
class VisionResult:
    analysis: ImageAnalysis
    search_query_uz: str      # Uzum, Olcha, Texnomart, Mediapark, Korzinka, Express24, Asaxiy
    search_query_ru: str      # Wildberries, Ozon
    search_query_olx: str     # OLX
    display_title: str
    low_confidence: bool      # True bo'lsa foydalanuvchiga yaxshiroq rasm so'rash


async def process_image(image_bytes: bytes, gemini_api_key: str) -> VisionResult:
    model = get_model("image_analysis")
    log_task_to_md("image_analysis", "started", model)

    analysis = await analyze_image(image_bytes, gemini_api_key)

    # Display title — brend+model+rang kombinatsiyasi
    parts = []
    if analysis.brand:
        parts.append(analysis.brand)
    if analysis.model:
        parts.append(analysis.model)
    if not parts:
        parts.append(analysis.item_type)
    if analysis.storage:
        parts.append(analysis.storage)
    if analysis.color and analysis.color.lower() not in ("noma'lum", "unknown"):
        parts.append(analysis.color)

    display_title = " ".join(parts)
    low_confidence = analysis.confidence == "low"

    log_task_to_md("image_analysis", "completed", model)
    logger.info(
        "VisionResult: '%s' | uz='%s' ru='%s' | conf=%s",
        display_title, analysis.search_query_uz,
        analysis.search_query_ru, analysis.confidence,
    )

    return VisionResult(
        analysis=analysis,
        search_query_uz=analysis.search_query_uz,
        search_query_ru=analysis.search_query_ru,
        search_query_olx=analysis.search_query_olx,
        display_title=display_title,
        low_confidence=low_confidence,
    )
