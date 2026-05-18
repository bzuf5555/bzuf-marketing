import logging
import urllib.parse
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from services.uzum_service import ProductResult

logger = logging.getLogger(__name__)

OLX_BASE = "https://www.olx.uz"
OLX_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,uz;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
}


async def search_olx(query: str, max_results: int = 5, timeout: int = 12) -> list[ProductResult]:
    # To'g'ri OLX.uz qidiruv URL formati
    search_url = f"{OLX_BASE}/list/?search[q]={urllib.parse.quote(query)}"

    try:
        async with httpx.AsyncClient(
            timeout=timeout, headers=OLX_HEADERS,
            follow_redirects=True,
        ) as client:
            response = await client.get(search_url)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")
        results = []

        listings = soup.select("[data-cy='l-card']") or soup.select(".offer-wrapper") or soup.select("article")

        for listing in listings[:max_results]:
            try:
                title_el = listing.select_one("h6, h3, h4, [class*='title']")
                title = title_el.get_text(strip=True) if title_el else None
                if not title:
                    continue

                price_el = listing.select_one("[data-testid='ad-price'], [class*='price'], strong")
                price = price_el.get_text(strip=True) if price_el else "Narx kelishiladi"

                img_el = listing.select_one("img")
                image_url: Optional[str] = None
                if img_el:
                    image_url = img_el.get("src") or img_el.get("data-src")

                link_el = listing.select_one("a[href]") or (listing if listing.name == "a" else None)
                href = link_el.get("href", "") if link_el else ""
                product_url = href if href.startswith("http") else f"{OLX_BASE}{href}"

                if not product_url or product_url == OLX_BASE:
                    continue

                results.append(ProductResult(
                    title=title, price=price,
                    image_url=image_url, product_url=product_url,
                    source="OLX.uz",
                ))
            except Exception as e:
                logger.debug("OLX parse: %s", e)

        logger.info("OLX: '%s' — %d natija", query, len(results))
        return results

    except httpx.TimeoutException:
        logger.warning("OLX timeout: '%s'", query)
        return []
    except Exception as e:
        logger.error("OLX error: %s", e)
        return []
