import logging
import urllib.parse
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from services.uzum_service import ProductResult

logger = logging.getLogger(__name__)

TEZKOR_BASE = "https://tezkor.uz"
TEZKOR_SEARCH = "https://tezkor.uz/search"
TEZKOR_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "uz-UZ,uz;q=0.9,ru;q=0.8",
}


async def search_tezkor(query: str, max_results: int = 5, timeout: int = 10) -> list[ProductResult]:
    params = {"q": query}

    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            headers=TEZKOR_HEADERS,
            follow_redirects=True,
        ) as client:
            response = await client.get(TEZKOR_SEARCH, params=params)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")
        results = []

        cards = soup.select(".product, .product-card, [class*='product'], .item-card")
        if not cards:
            cards = soup.select("a[href*='/product'], a[href*='/item'], [data-id]")

        for card in cards[:max_results]:
            try:
                title_el = card.select_one("h3, h4, [class*='title'], [class*='name']")
                title = title_el.get_text(strip=True) if title_el else None
                if not title or len(title) < 3:
                    continue

                price_el = card.select_one("[class*='price']")
                price = price_el.get_text(strip=True) if price_el else "Narx ko'rsatilmagan"

                img_el = card.select_one("img")
                image_url: Optional[str] = None
                if img_el:
                    src = img_el.get("data-src") or img_el.get("src") or ""
                    image_url = src if src.startswith("http") else (TEZKOR_BASE + src if src.startswith("/") else None)

                link_el = card if card.name == "a" else card.select_one("a[href]")
                href = link_el.get("href", "") if link_el else ""
                product_url = href if href.startswith("http") else (TEZKOR_BASE + href if href.startswith("/") else "")

                if not product_url:
                    continue

                results.append(ProductResult(
                    title=title,
                    price=price,
                    image_url=image_url,
                    product_url=product_url,
                    source="Tezkor.uz",
                ))
            except Exception as e:
                logger.debug("Tezkor parse: %s", e)
                continue

        logger.info("Tezkor: '%s' — %d natija", query, len(results))
        return results

    except httpx.TimeoutException:
        logger.warning("Tezkor timeout: '%s'", query)
        return []
    except Exception as e:
        logger.error("Tezkor error: %s", e)
        return []
