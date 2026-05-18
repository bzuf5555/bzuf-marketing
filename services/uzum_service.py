import logging
from dataclasses import dataclass
from typing import Optional
import asyncio

import httpx

logger = logging.getLogger(__name__)

UZUM_API_URL = "https://api.uzum.uz/api/main/search"
UZUM_PRODUCT_BASE = "https://uzum.uz/product"
UZUM_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Accept-Language": "uz-UZ,uz;q=0.9,ru;q=0.8",
    "Origin": "https://uzum.uz",
    "Referer": "https://uzum.uz/",
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
        "query": query,
        "size": max_results,
        "page": 0,
        "showAdultContent": "FALSE",
        "sort": "BY_RELEVANCE_DESC",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout, headers=UZUM_HEADERS) as client:
            response = await client.get(UZUM_API_URL, params=params)
            response.raise_for_status()
            data = response.json()

        products = data.get("payload", {}).get("products", [])
        results = []

        for item in products[:max_results]:
            try:
                title = item.get("title", "Noma'lum")
                price_val = item.get("skuList", [{}])[0].get("purchasePrice", 0)
                price = f"{price_val:,} so'm".replace(",", " ") if price_val else "Narx ko'rsatilmagan"

                photos = item.get("photos", [])
                image_url = photos[0].get("photo", {}).get("high", None) if photos else None
                if image_url and not image_url.startswith("http"):
                    image_url = f"https://cdn.uzum.uz/{image_url}"

                product_id = item.get("id", "")
                slug = item.get("productUrl", "")
                product_url = f"{UZUM_PRODUCT_BASE}/{slug}-{product_id}" if slug else f"{UZUM_PRODUCT_BASE}/{product_id}"

                results.append(ProductResult(
                    title=title,
                    price=price,
                    image_url=image_url,
                    product_url=product_url,
                    source="Uzum Market",
                ))
            except (KeyError, IndexError, TypeError) as e:
                logger.debug("Uzum product parse error: %s", e)
                continue

        logger.info("Uzum: '%s' uchun %d natija", query, len(results))
        return results

    except httpx.TimeoutException:
        logger.warning("Uzum timeout: '%s'", query)
        return []
    except Exception as e:
        logger.error("Uzum qidiruv xato: %s", e)
        return []
