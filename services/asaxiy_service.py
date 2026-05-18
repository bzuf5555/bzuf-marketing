import logging
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from services.uzum_service import ProductResult

logger = logging.getLogger(__name__)

ASAXIY_BASE = "https://asaxiy.uz"
ASAXIY_SEARCH = "https://asaxiy.uz/product"
ASAXIY_API = "https://asaxiy.uz/product/items"
ASAXIY_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/html",
    "Accept-Language": "uz-UZ,uz;q=0.9,ru;q=0.8",
    "X-Requested-With": "XMLHttpRequest",
}


async def search_asaxiy(query: str, max_results: int = 5, timeout: int = 10) -> list[ProductResult]:
    params = {
        "key": query,
        "perPage": max_results,
        "sortBy": "viewed_count",
    }

    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            headers=ASAXIY_HEADERS,
            follow_redirects=True,
        ) as client:
            response = await client.get(ASAXIY_API, params=params)

        if response.status_code == 200:
            try:
                data = response.json()
                items = data.get("data", data.get("items", []))
                if isinstance(items, dict):
                    items = items.get("data", [])

                results = []
                for item in items[:max_results]:
                    try:
                        title = item.get("name") or item.get("title") or ""
                        if not title:
                            continue

                        price_val = item.get("price") or item.get("current_price") or 0
                        price = f"{int(price_val):,} so'm".replace(",", " ") if price_val else "Narx ko'rsatilmagan"

                        image = item.get("image") or item.get("main_image") or ""
                        image_url: Optional[str] = None
                        if image:
                            image_url = image if image.startswith("http") else f"{ASAXIY_BASE}/{image.lstrip('/')}"

                        slug = item.get("slug") or item.get("url") or item.get("id", "")
                        product_url = f"{ASAXIY_BASE}/product/{slug}" if slug else ""

                        if not product_url:
                            continue

                        results.append(ProductResult(
                            title=title,
                            price=price,
                            image_url=image_url,
                            product_url=product_url,
                            source="Asaxiy.uz",
                        ))
                    except Exception as e:
                        logger.debug("Asaxiy item parse: %s", e)
                        continue

                logger.info("Asaxiy: '%s' — %d natija", query, len(results))
                return results
            except Exception:
                pass

        # Fallback: HTML scraping
        async with httpx.AsyncClient(
            timeout=timeout,
            headers={**ASAXIY_HEADERS, "Accept": "text/html"},
            follow_redirects=True,
        ) as client:
            response = await client.get(ASAXIY_SEARCH, params={"key": query})

        soup = BeautifulSoup(response.text, "lxml")
        results = []
        cards = soup.select(".product-card, [class*='product-item'], .item")

        for card in cards[:max_results]:
            try:
                title_el = card.select_one("h3, h4, [class*='name'], [class*='title']")
                title = title_el.get_text(strip=True) if title_el else None
                if not title:
                    continue

                price_el = card.select_one("[class*='price']")
                price = price_el.get_text(strip=True) if price_el else "Narx ko'rsatilmagan"

                img_el = card.select_one("img")
                image_url = None
                if img_el:
                    src = img_el.get("data-src") or img_el.get("src") or ""
                    image_url = src if src.startswith("http") else (ASAXIY_BASE + src if src.startswith("/") else None)

                link_el = card if card.name == "a" else card.select_one("a[href]")
                href = link_el.get("href", "") if link_el else ""
                product_url = href if href.startswith("http") else (ASAXIY_BASE + href if href.startswith("/") else "")

                if not product_url:
                    continue

                results.append(ProductResult(
                    title=title,
                    price=price,
                    image_url=image_url,
                    product_url=product_url,
                    source="Asaxiy.uz",
                ))
            except Exception as e:
                logger.debug("Asaxiy HTML parse: %s", e)
                continue

        logger.info("Asaxiy: '%s' — %d natija (HTML)", query, len(results))
        return results

    except httpx.TimeoutException:
        logger.warning("Asaxiy timeout: '%s'", query)
        return []
    except Exception as e:
        logger.error("Asaxiy error: %s", e)
        return []
