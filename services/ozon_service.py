import logging
import urllib.parse
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from services.uzum_service import ProductResult

logger = logging.getLogger(__name__)

OZON_SEARCH_URL = "https://www.ozon.uz/search/"
OZON_BASE = "https://www.ozon.uz"
OZON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,uz;q=0.8,en;q=0.7",
}
OZON_API_URL = "https://www.ozon.uz/api/composer-api.bx/page/json/v2"


async def search_ozon(query: str, max_results: int = 5, timeout: int = 12) -> list[ProductResult]:
    encoded = urllib.parse.quote(query)
    params = {"url": f"/search/?text={encoded}&from_global=true"}

    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            headers=OZON_HEADERS,
            follow_redirects=True,
        ) as client:
            response = await client.get(OZON_API_URL, params=params)
            response.raise_for_status()
            data = response.json()

        results = []
        widget_states = data.get("widgetStates", {})

        for key, value in widget_states.items():
            if "searchResultsV2" not in key and "tileGrid" not in key:
                continue
            if not isinstance(value, str):
                continue

            import json as json_mod
            try:
                widget_data = json_mod.loads(value)
            except Exception:
                continue

            items = widget_data.get("items", [])
            for item in items[:max_results]:
                try:
                    action = item.get("action", {})
                    link = action.get("link", "")
                    product_url = f"{OZON_BASE}{link}" if link.startswith("/") else link

                    main_state = item.get("mainState", [])
                    title = ""
                    price = "Narx ko'rsatilmagan"
                    image_url: Optional[str] = None

                    for state in main_state:
                        if state.get("id") == "name":
                            content = state.get("atom", {}).get("textAtom", {})
                            title = content.get("text", "")
                        if state.get("id") == "price":
                            content = state.get("atom", {}).get("priceAtom", {})
                            price = content.get("price", price)

                    tile_image = item.get("tileImage", {})
                    if tile_image:
                        image_url = tile_image.get("imageURL") or tile_image.get("src")

                    if not title or not product_url:
                        continue

                    results.append(ProductResult(
                        title=title,
                        price=price,
                        image_url=image_url,
                        product_url=product_url,
                        source="Ozon.uz",
                    ))
                except Exception as e:
                    logger.debug("Ozon item parse: %s", e)
                    continue

            if results:
                break

        logger.info("Ozon: '%s' — %d natija", query, len(results))
        return results[:max_results]

    except httpx.TimeoutException:
        logger.warning("Ozon timeout: '%s'", query)
        return []
    except Exception as e:
        logger.error("Ozon error: %s", e)
        return []
