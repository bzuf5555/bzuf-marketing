import logging
import urllib.parse
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from services.uzum_service import ProductResult

logger = logging.getLogger(__name__)

# makro.uz DNS ishlamaydi — korzinka.uz ishlatamiz (ishlaydigan O'zbek marketplace)
KORZINKA_BASE = "https://korzinka.uz"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "uz-UZ,uz;q=0.9,ru;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://korzinka.uz/",
}


async def search_makro(query: str, max_results: int = 5, timeout: int = 12) -> list[ProductResult]:
    search_url = f"{KORZINKA_BASE}/search?q={urllib.parse.quote(query)}"

    try:
        async with httpx.AsyncClient(
            timeout=timeout, headers=_HEADERS,
            follow_redirects=True, verify=False,
        ) as client:
            response = await client.get(search_url)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")
        results = []
        cards = soup.select(".product-card, .product, [class*='product'], [class*='item']")

        for card in cards[:max_results]:
            try:
                title_el = card.select_one("h2, h3, h4, [class*='title'], [class*='name']")
                title = title_el.get_text(strip=True) if title_el else None
                if not title or len(title) < 3:
                    continue

                price_el = card.select_one("[class*='price']")
                price = price_el.get_text(strip=True) if price_el else "Narx ko'rsatilmagan"

                img_el = card.select_one("img")
                image_url: Optional[str] = None
                if img_el:
                    src = img_el.get("data-src") or img_el.get("src") or ""
                    image_url = src if src.startswith("http") else (f"{KORZINKA_BASE}{src}" if src.startswith("/") else None)

                link_el = card if card.name == "a" else card.select_one("a[href]")
                href = link_el.get("href", "") if link_el else ""
                product_url = href if href.startswith("http") else (f"{KORZINKA_BASE}{href}" if href else "")

                if not product_url:
                    continue

                results.append(ProductResult(
                    title=title, price=price,
                    image_url=image_url, product_url=product_url,
                    source="Korzinka.uz",
                ))
            except Exception as e:
                logger.debug("Korzinka parse: %s", e)

        logger.info("Korzinka: '%s' — %d natija", query, len(results))
        return results

    except httpx.TimeoutException:
        logger.warning("Korzinka timeout: '%s'", query)
        return []
    except Exception as e:
        logger.error("Korzinka error: %s", e)
        return []
