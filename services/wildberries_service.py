import logging
import urllib.parse
from typing import Optional

import httpx

from services.uzum_service import ProductResult

logger = logging.getLogger(__name__)

WB_SEARCH_API = "https://search.wb.ru/exactmatch/ru/male/v4/search"
WB_PRODUCT_BASE = "https://www.wildberries.uz/catalog"
WB_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Origin": "https://www.wildberries.uz",
    "Referer": "https://www.wildberries.uz/",
}


def _wb_image_url(nm_id: int) -> str:
    vol = nm_id // 100000
    part = nm_id // 1000
    ranges = [
        (143, "01"), (287, "02"), (431, "03"), (719, "04"),
        (1007, "05"), (1061, "06"), (1115, "07"), (1169, "08"),
        (1313, "09"), (1601, "10"), (1655, "11"), (1919, "12"),
        (2045, "13"), (2189, "14"), (2405, "15"), (2621, "16"),
        (2837, "17"),
    ]
    basket = "18"
    for max_vol, b in ranges:
        if vol <= max_vol:
            basket = b
            break
    return f"https://basket-{basket}.wbbasket.ru/vol{vol}/part{part}/{nm_id}/images/big/1.jpg"


async def search_wildberries(query: str, max_results: int = 5, timeout: int = 12) -> list[ProductResult]:
    params = {
        "appType": "1",
        "curr": "uzs",
        "dest": "-1257786",
        "query": query,
        "resultset": "catalog",
        "sort": "popular",
        "spp": "30",
        "suppressSpellCheck": "false",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout, headers=WB_HEADERS) as client:
            response = await client.get(WB_SEARCH_API, params=params)
            response.raise_for_status()
            data = response.json()

        products = data.get("data", {}).get("products", [])
        results = []

        for item in products[:max_results]:
            try:
                nm_id = item.get("id")
                title = item.get("name", "Noma'lum")
                brand = item.get("brand", "")
                full_title = f"{brand} {title}".strip() if brand else title

                price_val = item.get("salePriceU", item.get("priceU", 0))
                price = f"{price_val // 100:,} so'm".replace(",", " ") if price_val else "Narx ko'rsatilmagan"

                image_url = _wb_image_url(nm_id) if nm_id else None
                product_url = f"{WB_PRODUCT_BASE}/{nm_id}/detail.aspx" if nm_id else ""

                results.append(ProductResult(
                    title=full_title,
                    price=price,
                    image_url=image_url,
                    product_url=product_url,
                    source="Wildberries",
                ))
            except (KeyError, TypeError) as e:
                logger.debug("WB parse error: %s", e)
                continue

        logger.info("WB: '%s' — %d natija", query, len(results))
        return results

    except httpx.TimeoutException:
        logger.warning("WB timeout: '%s'", query)
        return []
    except Exception as e:
        logger.error("WB error: %s", e)
        return []
