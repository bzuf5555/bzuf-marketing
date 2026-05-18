import logging
import urllib.parse
from typing import Optional

import httpx

from services.uzum_service import ProductResult

logger = logging.getLogger(__name__)

OZON_BASE = "https://www.ozon.ru"  # ozon.uz SSL xato beradi — ozon.ru ishlatamiz
OZON_API = "https://www.ozon.ru/api/composer-api.bx/page/json/v2"
OZON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ru-RU,ru;q=0.9,uz;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.ozon.ru/",
    "x-o3-app-name": "ozon-front",
    "x-o3-app-version": "7.0.4",
    "x-o3-language": "ru",
    "x-o3-currency": "UZS",
}


async def search_ozon(query: str, max_results: int = 5, timeout: int = 15) -> list[ProductResult]:
    encoded = urllib.parse.quote(query)
    params = {"url": f"/search/?text={encoded}&from_global=true"}

    try:
        async with httpx.AsyncClient(
            timeout=timeout, headers=OZON_HEADERS,
            follow_redirects=True,
            verify=False,  # SSL sertifikat muammolarini e'tiborsiz qoldirish
        ) as client:
            response = await client.get(OZON_API, params=params)
            response.raise_for_status()
            data = response.json()

        results = []
        import json as json_mod
        widget_states = data.get("widgetStates", {})

        for key, value in widget_states.items():
            if not isinstance(value, str):
                continue
            if "searchResultsV2" not in key and "tileGrid" not in key and "searchV2" not in key:
                continue

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
                    if not product_url:
                        continue

                    title = ""
                    price = "Narx ko'rsatilmagan"
                    image_url: Optional[str] = None

                    for state in item.get("mainState", []):
                        if state.get("id") == "name":
                            title = state.get("atom", {}).get("textAtom", {}).get("text", "")
                        if state.get("id") == "price":
                            price = state.get("atom", {}).get("priceAtom", {}).get("price", price)

                    tile_img = item.get("tileImage", {})
                    if tile_img:
                        image_url = tile_img.get("imageURL") or tile_img.get("src")

                    if not title:
                        continue

                    results.append(ProductResult(
                        title=title, price=price,
                        image_url=image_url, product_url=product_url,
                        source="Ozon.uz",
                    ))
                except Exception as e:
                    logger.debug("Ozon item parse: %s", e)

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
