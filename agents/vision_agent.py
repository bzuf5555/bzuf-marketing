"""
[OPUS] Vision Agent — rasm tahlilini orchestrate qiladi.
Yangi: search_query_ru — WB/Ozon uchun rus tilidagi query.
"""
import logging
from dataclasses import dataclass

from services.gemini_service import ImageAnalysis, analyze_image
from agents.token_agent import get_model, log_task_to_md

logger = logging.getLogger(__name__)


@dataclass
class VisionResult:
    analysis: ImageAnalysis
    search_query_uz: str      # Uzum, Olcha, Texnomart, Makro, MediaPark, Tezkor, Asaxiy
    search_query_ru: str      # Wildberries, Ozon — rus tilida
    search_query_olx: str     # OLX — keng qidiruv
    display_title: str


async def process_image(image_bytes: bytes, gemini_api_key: str) -> VisionResult:
    model = get_model("image_analysis")
    log_task_to_md("image_analysis", "started", model)

    analysis = await analyze_image(image_bytes, gemini_api_key)

    # Display title uchun eng muhim ma'lumotlarni birlashtirish
    parts = [analysis.item_type]
    if analysis.brand:
        parts.insert(0, analysis.brand)
    if analysis.model:
        parts.append(analysis.model)

    display_title = " ".join(parts)

    log_task_to_md("image_analysis", "completed", model)
    logger.info(
        "VisionResult: '%s' | uz='%s' | ru='%s'",
        display_title, analysis.search_query_uz, analysis.search_query_ru,
    )

    return VisionResult(
        analysis=analysis,
        search_query_uz=analysis.search_query_uz or analysis.item_type,
        search_query_ru=analysis.search_query_ru or analysis.item_type,
        search_query_olx=analysis.search_query_olx or analysis.item_type,
        display_title=display_title,
    )
