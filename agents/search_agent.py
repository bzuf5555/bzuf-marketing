"""
Search Agent — barcha marketlardan parallel qidiradi (MEDIUM complexity → Sonnet).
asyncio.gather bilan Uzum, Olcha, OLX dan bir vaqtda natija oladi.
"""
import asyncio
import logging
from dataclasses import dataclass

from agents.vision_agent import VisionResult
from agents.token_agent import get_model, log_task_to_md
from services.uzum_service import ProductResult, search_uzum
from services.olcha_service import search_olcha
from services.olx_service import search_olx

logger = logging.getLogger(__name__)


@dataclass
class SearchResults:
    vision: VisionResult
    all_results: list[ProductResult]
    total_found: int


async def search_all_markets(
    vision: VisionResult,
    max_results: int = 5,
    timeout: int = 10,
) -> SearchResults:
    model = get_model("marketplace_search")
    log_task_to_md("marketplace_search", "started", model)

    uzum_task = search_uzum(vision.search_query_primary, max_results, timeout)
    olcha_task = search_olcha(vision.search_query_primary, max_results, timeout)
    olx_task = search_olx(vision.search_query_secondary, max_results, timeout)

    uzum_res, olcha_res, olx_res = await asyncio.gather(
        uzum_task, olcha_task, olx_task
    )

    all_results: list[ProductResult] = []

    for res_list in [uzum_res, olcha_res, olx_res]:
        all_results.extend(res_list[:3])

    total = len(all_results)
    log_task_to_md("marketplace_search", f"completed ({total} results)", model)
    logger.info("Search completed: %d results total", total)

    return SearchResults(
        vision=vision,
        all_results=all_results,
        total_found=total,
    )


def format_results_message(results: SearchResults) -> str:
    vision = results.vision
    analysis = vision.analysis

    header_parts = [f"🔍 <b>{vision.display_title}</b>"]
    if analysis.brand:
        header_parts.append(f"🏷 Brend: {analysis.brand}")
    if analysis.color:
        header_parts.append(f"🎨 Rang: {analysis.color}")
    if analysis.size:
        header_parts.append(f"📐 O'lcham: {analysis.size}")
    if analysis.model:
        header_parts.append(f"📋 Model: {analysis.model}")
    if analysis.condition:
        header_parts.append(f"✅ Holat: {analysis.condition}")

    header_parts.append(f"\n📝 {analysis.description}")

    if not results.all_results:
        header_parts.append("\n\n😔 Afsuski, hech qaysi marketda topilmadi.")
        return "\n".join(header_parts)

    header_parts.append(f"\n\n🛒 <b>Topildi ({results.total_found} ta):</b>")
    message = "\n".join(header_parts)

    for i, product in enumerate(results.all_results, 1):
        message += f"\n\n<b>{i}. {product.source}</b>"
        message += f"\n📦 {product.title}"
        message += f"\n💰 {product.price}"
        message += f"\n🔗 <a href='{product.product_url}'>Xarid qilish</a>"

    return message
