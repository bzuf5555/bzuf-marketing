"""
[SONNET] Search Agent — 10 ta marketplace parallel qidiruv + cache.
- Uzbek query: Uzum, Olcha, OLX, Texnomart, Makro, MediaPark, Tezkor, Asaxiy
- Russian query: Wildberries, Ozon (rus tilida yaxshiroq natija beradi)
- Cache: bir xil query 30 daqiqa davomida qayta API chaqirmaydi
"""
import asyncio
import logging
from dataclasses import dataclass

from agents.vision_agent import VisionResult
from agents.token_agent import get_model, log_task_to_md
from utils.cache import search_cache
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
    "Tezkor.uz":     "🚀",
    "Asaxiy.uz":     "🛍",
}


@dataclass
class SearchResults:
    vision: VisionResult
    results_by_source: dict[str, list[ProductResult]]
    total_found: int
    from_cache: bool = False


def _cache_key(vision: VisionResult) -> str:
    return f"{vision.search_query_uz}|{vision.search_query_ru}".lower().strip()


async def search_all_markets(
    vision: VisionResult,
    max_results: int = 3,
    timeout: int = 12,
) -> SearchResults:
    model = get_model("marketplace_search")
    log_task_to_md("marketplace_search", "started", model)

    # Cache tekshirish
    key = _cache_key(vision)
    cached = search_cache.get(key)
    if cached is not None:
        logger.info("Cache HIT: '%s'", key[:50])
        return SearchResults(
            vision=vision,
            results_by_source=cached["results_by_source"],
            total_found=cached["total_found"],
            from_cache=True,
        )

    uz = vision.search_query_uz    # O'zbek tilidagi marketlar uchun
    ru = vision.search_query_ru    # Wildberries, Ozon uchun
    olx = vision.search_query_olx  # OLX — keng qidiruv

    all_tasks = await asyncio.gather(
        search_uzum(uz, max_results, timeout),
        search_olcha(uz, max_results, timeout),
        search_olx(olx, max_results, timeout),
        search_wildberries(ru, max_results, timeout),   # rus query
        search_ozon(ru, max_results, timeout),          # rus query
        search_texnomart(uz, max_results, timeout),
        search_makro(uz, max_results, timeout),
        search_mediapark(uz, max_results, timeout),
        search_tezkor(uz, max_results, timeout),
        search_asaxiy(uz, max_results, timeout),
    )

    sources = [
        "Uzum Market", "Olcha.uz", "OLX.uz", "Wildberries", "Ozon.uz",
        "Texnomart.uz", "Makro.uz", "MediaPark.uz", "Tezkor.uz", "Asaxiy.uz",
    ]

    results_by_source: dict[str, list[ProductResult]] = {}
    total = 0
    for source, res_list in zip(sources, all_tasks):
        if res_list:
            results_by_source[source] = res_list[:max_results]
            total += len(results_by_source[source])

    # Cahelash
    search_cache.set(key, {"results_by_source": results_by_source, "total_found": total})

    log_task_to_md("marketplace_search", f"done ({total} results, {len(results_by_source)} markets)", model)
    logger.info("Search: %d results from %d markets | uz='%s' ru='%s'", total, len(results_by_source), uz, ru)

    return SearchResults(
        vision=vision,
        results_by_source=results_by_source,
        total_found=total,
        from_cache=False,
    )


def format_results_message(results: SearchResults) -> list[str]:
    """
    Bir nechta xabar qaytaradi (Telegram 4096 belgi limiti).
    Birinchi: mahsulot tavsifi + statistika.
    Keyingilar: har bir market bloki alohida.
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
    if analysis.key_features:
        lines.append(f"⚙️ {' · '.join(analysis.key_features[:3])}")
    lines.append(f"\n📝 {analysis.description}")

    found_sources = len(results.results_by_source)
    cache_note = " ⚡ (keshdan)" if results.from_cache else ""
    if found_sources == 0:
        lines.append("\n\n😔 Hech qaysi marketda topilmadi.\nBoshqa rasm yuboring.")
        return ["\n".join(lines)]

    lines.append(f"\n\n🛒 <b>{results.total_found} mahsulot, {found_sources} marketdan{cache_note}</b>")
    messages = ["\n".join(lines)]

    for source, products in results.results_by_source.items():
        icon = MARKETPLACE_ICONS.get(source, "🛒")
        block = [f"{icon} <b>{source}</b>"]
        for i, p in enumerate(products, 1):
            block.append(f"\n<b>{i}.</b> {p.title}")
            block.append(f"   💰 {p.price}")
            block.append(f"   🔗 <a href='{p.product_url}'>Ko'rish →</a>")
        messages.append("\n".join(block))

    return messages


def get_best_image(results: SearchResults) -> str | None:
    for products in results.results_by_source.values():
        for p in products:
            if p.image_url:
                return p.image_url
    return None
