"""
[SONNET] Search Agent — 10 ta marketplace parallel qidiruv + cache.
- Uzbek query: Uzum, Olcha, OLX, Texnomart, Makro, MediaPark, Tezkor, Asaxiy
- Russian query: Wildberries, Ozon
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

_ICONS = {
    "Uzum Market":   "🟠",
    "Olcha.uz":      "🍒",
    "OLX.uz":        "🟢",
    "Wildberries":   "🍇",
    "Ozon.uz":       "🔵",
    "Texnomart.uz":  "⚡",
    "Korzinka.uz":   "🛒",
    "MediaPark.uz":  "📺",
    "Express24.uz":  "🚀",
    "Asaxiy.uz":     "🛍",
}

_SOURCES = list(_ICONS.keys())


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

    uz  = vision.search_query_uz
    ru  = vision.search_query_ru
    olx = vision.search_query_olx

    all_tasks = await asyncio.gather(
        search_uzum(uz, max_results, timeout),
        search_olcha(uz, max_results, timeout),
        search_olx(olx, max_results, timeout),
        search_wildberries(ru, max_results, timeout),
        search_ozon(ru, max_results, timeout),
        search_texnomart(uz, max_results, timeout),
        search_makro(uz, max_results, timeout),
        search_mediapark(uz, max_results, timeout),
        search_tezkor(uz, max_results, timeout),
        search_asaxiy(uz, max_results, timeout),
    )

    results_by_source: dict[str, list[ProductResult]] = {}
    total = 0
    for source, res_list in zip(_SOURCES, all_tasks):
        if res_list:
            results_by_source[source] = res_list[:max_results]
            total += len(results_by_source[source])

    search_cache.set(key, {"results_by_source": results_by_source, "total_found": total})
    log_task_to_md("marketplace_search", f"done ({total} results, {len(results_by_source)} markets)", model)
    logger.info("Search: %d results / %d markets | uz='%s' ru='%s'", total, len(results_by_source), uz, ru)

    return SearchResults(
        vision=vision,
        results_by_source=results_by_source,
        total_found=total,
        from_cache=False,
    )


# ──────────────────────────────────────────────────
#  MESSAGE FORMATTING  (elite UI)
# ──────────────────────────────────────────────────

def _num_emoji(n: int) -> str:
    return ("1️⃣", "2️⃣", "3️⃣")[n - 1] if 1 <= n <= 3 else f"{n}."


def format_header(results: SearchResults) -> str:
    """Birinchi xabar: mahsulot tavsifi + statistika."""
    v = results.vision
    a = v.analysis
    found = len(results.results_by_source)
    cache_tag = "  <i>⚡ keshdan</i>" if results.from_cache else ""

    lines = [
        "┌─────────────────────────────┐",
        f"│  🔍  <b>{v.display_title}</b>",
        "└─────────────────────────────┘",
    ]

    if a.brand:
        lines.append(f"\n🏷  Brend:   <b>{a.brand}</b>")
    if a.model:
        lines.append(f"📋  Model:   <b>{a.model}</b>")
    if a.color:
        lines.append(f"🎨  Rang:    {a.color}")
    if getattr(a, 'storage', None):
        lines.append(f"💾  Xotira:  {a.storage}")
    if a.size:
        lines.append(f"📐  O'lcham: {a.size}")
    lines.append(f"✅  Holat:   {a.condition}")
    conf = getattr(a, 'confidence', 'medium')
    if conf == 'high':
        lines.append(f"🎯  Aniqlik: <b>Yuqori</b>")
    elif conf == 'low':
        lines.append(f"⚠️  Aniqlik: Past — rasmni aniqroq yuboring")
    if a.key_features:
        lines.append(f"⚙️   {' · '.join(a.key_features[:3])}")

    lines.append(f"\n📝 <i>{a.description}</i>")

    if found == 0:
        lines.append(
            "\n\n😔 <b>Hech qaysi marketda topilmadi.</b>\n"
            "Yaxshiroq yorug'lik bilan boshqa rasm yuboring."
        )
    else:
        lines.append(
            f"\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🛒 <b>{results.total_found} ta mahsulot</b> · "
            f"<b>{found} ta market</b>{cache_tag}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )

    return "\n".join(lines)


def format_market_block(source: str, products: list[ProductResult]) -> str:
    """Har bir marketplace uchun alohida xabar bloki."""
    icon = _ICONS.get(source, "🛒")
    lines = [
        f"┌─── {icon}  <b>{source}</b> ───",
    ]
    for i, p in enumerate(products, 1):
        num = _num_emoji(i)
        lines.append(f"│")
        lines.append(f"│  {num}  <b>{p.title}</b>")
        lines.append(f"│      💰  {p.price}")
        lines.append(f"│      🔗  <a href='{p.product_url}'>Xarid qilish →</a>")
    lines.append("└────────────────────────────")
    return "\n".join(lines)


def format_results_message(results: SearchResults) -> list[str]:
    """
    Barcha xabarlar ro'yxatini qaytaradi.
    [0] = mahsulot header
    [1..N] = har bir marketplace bloki
    """
    messages = [format_header(results)]
    for source, products in results.results_by_source.items():
        messages.append(format_market_block(source, products))
    return messages


def get_best_image(results: SearchResults) -> str | None:
    for products in results.results_by_source.values():
        for p in products:
            if p.image_url:
                return p.image_url
    return None
