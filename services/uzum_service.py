import logging
from dataclasses import dataclass
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

UZUM_SEARCH_URL = "https://api.uzum.uz/api/search"
UZUM_PRODUCT_BASE = "https://uzum.uz/product"
UZUM_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "uz-UZ,uz;q=0.9,ru;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Origin": "https://uzum.uz",
    "Referer": "https://uzum.uz/",
    "x-iid": "1234567890abcdef",
}


@dataclass
class ProductResult:
    title: str
    price: str
    image_url: Optional[str]
    product_url: str
    source: str


async def search_uzum(query: str, max_results: int = 5, timeout: int = 10) -> list[ProductResult]:
    params = {
        "text": query,
        "size": max_results,
        "pageNumber": 0,
        "showAdultContent": "FALSE",
        "sort": "BY_RELEVANCE_DESC",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout, headers=UZUM_HEADERS) as client:
            response = await client.get(UZUM_SEARCH_URL, params=params)
            response.raise_for_status()
            data = response.json()

        # Yangi API strukturasi
        products = (
            data.get("productList", {}).get("products", [])
            or data.get("payload", {}).get("products", [])
            or data.get("products", [])
            or []
        )
        results = []

        for item in products[:max_results]:
            try:
                title = item.get("title", item.get("name", "Noma'lum"))
                sku = item.get("skuList", [{}])
                price_val = 0
                if sku:
                    price_val = sku[0].get("purchasePrice", sku[0].get("fullPrice", 0))
                price = f"{price_val:,} so'm".replace(",", " ") if price_val else "Narx ko'rsatilmagan"

                photos = item.get("photos", item.get("images", []))
                image_url = None
                if photos:
                    img = photos[0]
                    if isinstance(img, dict):
                        src = img.get("photo", {}).get("high") or img.get("url") or img.get("src", "")
                    else:
                        src = str(img)
                    image_url = src if src.startswith("http") else (f"https://cdn.uzum.uz/{src}" if src else None)

                product_id = item.get("id", "")
                slug = item.get("productUrl", item.get("slug", ""))
                product_url = f"{UZUM_PRODUCT_BASE}/{slug}-{product_id}" if slug else f"{UZUM_PRODUCT_BASE}/{product_id}"

                results.append(ProductResult(
                    title=title, price=price,
                    image_url=image_url, product_url=product_url,
                    source="Uzum Market",
                ))
            except Exception as e:
                logger.debug("Uzum item parse: %s", e)

        logger.info("Uzum: '%s' — %d natija", query, len(results))
        return results

    except httpx.HTTPStatusError as e:
        logger.warning("Uzum HTTP %d: '%s'", e.response.status_code, query)
        return []
    except httpx.TimeoutException:
        logger.warning("Uzum timeout: '%s'", query)
        return []
    except Exception as e:
        logger.error("Uzum error: %s", e)
        return []
