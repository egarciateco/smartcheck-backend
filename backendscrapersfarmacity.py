from .base import BaseScraper
from engine import register_scraper
from typing import List, Dict
import re

@register_scraper("Farmacity")
class FarmacityScraper(BaseScraper):
    BASE_URL = "https://www.farmacity.com"

    async def fetch_prices(self, products: List[str], location: str) -> Dict:
        browser = await self._init_browser()
        page = await browser.new_page()
        item_prices = []
        try:
            for product in products:
                url = f"{self.BASE_URL}/search?query={product.replace(' ', '+')}"
                await page.goto(url, wait_until="networkidle", timeout=12000)
                await page.wait_for_selector(".price-value", timeout=8000)
                price_el = await page.query_selector(".price-value")
                if price_el:
                    raw = await price_el.inner_text()
                    clean = re.sub(r"[^\d]", "", raw)
                    price = float(clean)
                    item_prices.append({"item": product, "price": price})
                else:
                    item_prices.append({"item": product, "price": 0})
            return self._format_result("Farmacity", f"Farmacity {location}", item_prices)
        except Exception as e:
            return {"name": "Farmacity", "status": "error", "message": str(e)}
        finally:
            await browser.close()