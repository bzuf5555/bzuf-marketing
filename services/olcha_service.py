import logging
from typing import Optional
import urllib.parse

import httpx
from bs4 import BeautifulSoup

from services.uzum_service import ProductResult

logger = logging.getLogger(__name__)

OLCHA_SEARCH_URL = "https://olcha.uz/search/"
OLCHA_BASE = "https://olcha.uz"
OLCHA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "uz-UZ,uz;q=0.9,ru;q=0.8",
}


async def search_olcha(query: str, max_results: int = 5, timeout: int = 10) -> list[ProductResult]:
    encoded_query = urllib.parse.quote(query)
    search_url = f"{OLCHA_SEARCH_URL}?q={encoded_query}"

    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            headers=OLCHA_HEADERS,
            follow_redirects=True,
        ) as client:
            response = await client.get(search_url)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        results = []

        product_cards = soup.select(".product-card, .product-item, [class*='product']")
        if not product_cards:
            product_cards = soup.select("a[href*='/product']")

        for card in product_cards[:max_results]:
            try:
                title_el = card.select_one(".product-name, .title, h3, h2, [class*='name']")
                title = title_el.get_text(strip=True) if title_el else None
                if not title:
                    continue

                price_el = card.select_one(".price, [class*='price']")
                price = price_el.get_text(strip=True) if price_el else "Narx ko'rsatilmagan"

                img_el = card.select_one("img")
                image_url: Optional[str] = None
                if img_el:
                    image_url = img_el.get("data-src") or img_el.get("src")
                    if image_url and image_url.startswith("//"):
                        image_url = "https:" + image_url

                link_el = card if card.name == "a" else card.select_one("a[href]")
                href = link_el.get("href", "") if link_el else ""
                product_url = href if href.startswith("http") else f"{OLCHA_BASE}{href}"

                results.append(ProductResult(
                    title=title,
                    price=price,
                    image_url=image_url,
                    product_url=product_url,
                    source="Olcha.uz",
                ))
            except Exception as e:
                logger.debug("Olcha card parse error: %s", e)
                continue

        logger.info("Olcha: '%s' uchun %d natija", query, len(results))
        return results

    except httpx.TimeoutException:
        logger.warning("Olcha timeout: '%s'", query)
        return []
    except Exception as e:
        logger.error("Olcha qidiruv xato: %s", e)
        return []
