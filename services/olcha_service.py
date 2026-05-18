import logging
import urllib.parse
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from services.uzum_service import ProductResult

logger = logging.getLogger(__name__)

OLCHA_BASE = "https://olcha.uz"
OLCHA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "uz-UZ,uz;q=0.9,ru;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
    "Referer": "https://olcha.uz/",
}


async def search_olcha(query: str, max_results: int = 5, timeout: int = 12) -> list[ProductResult]:
    search_url = f"{OLCHA_BASE}/search/?q={urllib.parse.quote(query)}"

    try:
        async with httpx.AsyncClient(
            timeout=timeout, headers=OLCHA_HEADERS,
            follow_redirects=True, verify=False,
        ) as client:
            response = await client.get(search_url)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")
        results = []

        cards = soup.select(".product-card, .product-item, [class*='product']") or soup.select("a[href*='/product']")

        for card in cards[:max_results]:
            try:
                title_el = card.select_one(".product-name, .title, h3, h2, [class*='name']")
                title = title_el.get_text(strip=True) if title_el else None
                if not title or len(title) < 3:
                    continue

                price_el = card.select_one("[class*='price']")
                price = price_el.get_text(strip=True) if price_el else "Narx ko'rsatilmagan"

                img_el = card.select_one("img")
                image_url: Optional[str] = None
                if img_el:
                    src = img_el.get("data-src") or img_el.get("src") or ""
                    image_url = ("https:" + src) if src.startswith("//") else (src if src.startswith("http") else None)

                link_el = card if card.name == "a" else card.select_one("a[href]")
                href = link_el.get("href", "") if link_el else ""
                product_url = href if href.startswith("http") else f"{OLCHA_BASE}{href}"

                results.append(ProductResult(
                    title=title, price=price,
                    image_url=image_url, product_url=product_url,
                    source="Olcha.uz",
                ))
            except Exception as e:
                logger.debug("Olcha parse: %s", e)

        logger.info("Olcha: '%s' — %d natija", query, len(results))
        return results

    except httpx.TimeoutException:
        logger.warning("Olcha timeout: '%s'", query)
        return []
    except Exception as e:
        logger.error("Olcha error: %s", e)
        return []
