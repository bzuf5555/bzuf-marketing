"""
Search Agent — O'zbekistondagi BARCHA marketlardan parallel qidiradi (MEDIUM → Sonnet).
Jami 10 ta marketplace: Uzum, Olcha, OLX, Wildberries, Ozon,
Texnomart, Makro, MediaPark, Tezkor, Asaxiy.
asyncio.gather — hammasi bir vaqtda, birortasi ishlamasa o'tkazib yuboriladi.
"""
import asyncio
import logging
from dataclasses import dataclass

from agents.vision_agent import VisionResult
from agents.token_agent import get_model, log_task_to_md
from services.uzum_service import ProductResult, search_uzum
from services.olcha_service import search_olcha
from services.olx_service import search_olx
from services.wildberries_service import search_wildberries
from services.ozon_service import search_ozon
from services.texnomart_service import search_texnomart
from services.makro_service import search_makro
from services.mediapark_service import search_mediapark
from services.tezkor_service import search_tezkor
from services.asaxiy_service import search_asaxiy

logger = logging.getLogger(__name__)

MARKETPLACE_ICONS = {
    "Uzum Market":   "🟠",
    "Olcha.uz":      "🍒",
    "OLX.uz":        "🟢",
    "Wildberries":   "🍇",
    "Ozon.uz":       "🔵",
    "Texnomart.uz":  "⚡",
    "Makro.uz":      "🛒",
    "MediaPark.uz":  "📺",
    "Tezkor.uz":     "⚡",
    "Asaxiy.uz":     "🛍",
}


@dataclass
class SearchResults:
    vision: VisionResult
    results_by_source: dict[str, list[ProductResult]]
    total_found: int


async def search_all_markets(
    vision: VisionResult,
    max_results: int = 3,
    timeout: int = 12,
) -> SearchResults:
    model = get_model("marketplace_search")
    log_task_to_md("marketplace_search", "started", model)

    pq = vision.search_query_primary    # Uzum/Olcha/WB/Ozon/Texnomart/Makro/MediaPark/Tezkor/Asaxiy
    sq = vision.search_query_secondary  # OLX uchun (biroz keng)

    tasks = await asyncio.gather(
        search_uzum(pq, max_results, timeout),
        search_olcha(pq, max_results, timeout),
        search_olx(sq, max_results, timeout),
        search_wildberries(pq, max_results, timeout),
        search_ozon(pq, max_results, timeout),
        search_texnomart(pq, max_results, timeout),
        search_makro(pq, max_results, timeout),
        search_mediapark(pq, max_results, timeout),
        search_tezkor(pq, max_results, timeout),
        search_asaxiy(pq, max_results, timeout),
    )

    sources = [
        "Uzum Market", "Olcha.uz", "OLX.uz", "Wildberries", "Ozon.uz",
        "Texnomart.uz", "Makro.uz", "MediaPark.uz", "Tezkor.uz", "Asaxiy.uz",
    ]

    results_by_source: dict[str, list[ProductResult]] = {}
    total = 0
    for source, res_list in zip(sources, tasks):
        if res_list:
            results_by_source[source] = res_list[:max_results]
            total += len(results_by_source[source])

    log_task_to_md("marketplace_search", f"completed ({total} results, {len(results_by_source)} markets)", model)
    logger.info("Search done: %d results from %d markets", total, len(results_by_source))

    return SearchResults(
        vision=vision,
        results_by_source=results_by_source,
        total_found=total,
    )


def format_results_message(results: SearchResults) -> list[str]:
    """
    Telegram xabar uzunligi 4096 belgidan oshmasligi uchun
    bir nechta xabar qaytaradi: birinchisi mahsulot tavsifi,
    keyingisi har bir marketplace uchun.
    """
    vision = results.vision
    analysis = vision.analysis

    lines = [f"🔍 <b>{vision.display_title}</b>"]
    if analysis.brand:
        lines.append(f"🏷 Brend: <b>{analysis.brand}</b>")
    if analysis.color:
        lines.append(f"🎨 Rang: {analysis.color}")
    if analysis.size:
        lines.append(f"📐 O'lcham: {analysis.size}")
    if analysis.model:
        lines.append(f"📋 Model: {analysis.model}")
    lines.append(f"✅ Holat: {analysis.condition}")
    lines.append(f"\n📝 {analysis.description}")

    found_sources = len(results.results_by_source)
    if found_sources == 0:
        lines.append("\n\n😔 Hech qaysi marketda topilmadi. Boshqa rasm yuboring.")
        return ["\n".join(lines)]

    lines.append(f"\n\n🛒 <b>{results.total_found} ta mahsulot, {found_sources} ta marketdan topildi:</b>")
    header_msg = "\n".join(lines)

    messages = [header_msg]

    for source, products in results.results_by_source.items():
        icon = MARKETPLACE_ICONS.get(source, "🛒")
        block_lines = [f"{icon} <b>{source}</b>"]

        for i, p in enumerate(products, 1):
            block_lines.append(f"\n<b>{i}.</b> {p.title}")
            block_lines.append(f"   💰 {p.price}")
            block_lines.append(f"   🔗 <a href='{p.product_url}'>Ko'rish →</a>")

        messages.append("\n".join(block_lines))

    return messages


def get_best_image(results: SearchResults) -> str | None:
    """Natijalar ichidan birinchi rasmli mahsulot rasmini qaytaradi."""
    for products in results.results_by_source.values():
        for p in products:
            if p.image_url:
                return p.image_url
    return None
