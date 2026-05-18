"""
Vision Agent — rasmni tahlil qiladi (HIGH complexity → Gemini Flash ishlatiladi).
Claude Opus darajasidagi mantiq: prompt engineering + tahlil tekshirish.
"""
import logging
from dataclasses import dataclass

from services.gemini_service import ImageAnalysis, analyze_image
from agents.token_agent import get_model, log_task_to_md

logger = logging.getLogger(__name__)


@dataclass
class VisionResult:
    analysis: ImageAnalysis
    search_query_primary: str
    search_query_secondary: str
    display_title: str


async def process_image(image_bytes: bytes, gemini_api_key: str) -> VisionResult:
    model = get_model("image_analysis")
    log_task_to_md("image_analysis", "started", model)

    analysis = await analyze_image(image_bytes, gemini_api_key)

    parts = [analysis.item_type]
    if analysis.brand:
        parts.append(analysis.brand)
    if analysis.model:
        parts.append(analysis.model)
    if analysis.color and analysis.color != "noma'lum":
        parts.append(analysis.color)

    display_title = " ".join(parts)

    primary_query = analysis.search_query_uz
    secondary_query = analysis.search_query_olx

    if not primary_query:
        primary_query = analysis.item_type
    if not secondary_query:
        secondary_query = analysis.item_type

    log_task_to_md("image_analysis", "completed", model)
    logger.info("Vision: '%s' — primary: '%s'", display_title, primary_query)

    return VisionResult(
        analysis=analysis,
        search_query_primary=primary_query,
        search_query_secondary=secondary_query,
        display_title=display_title,
    )
