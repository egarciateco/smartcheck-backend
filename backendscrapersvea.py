from .base import BaseScraper
from engine import register_scraper
from typing import List, Dict
import re

@register_scraper("Vea")
class VeaScraper(BaseScraper):
    BASE_URL = "https://www.vea.com.ar"

    async def fetch_prices(self, products: List[str], location: str) -> Dict:
        browser = await self._init_browser()
        page = await browser.new_page()
        await page.set_extra_http_headers({"Accept-Language": "es-AR"})
        item_prices = []
        try:
            for product in products:
                url = f"{self.BASE_URL}/search?q={product.replace(' ', '+')}"
                await page.goto(url, wait_until="networkidle", timeout=10000)
                price_el = await page.query_selector("._price_1h3z1_1")
                if price_el:
                    raw = await price_el.inner_text()
                    clean = re.sub(r"[^\d]", "", raw)
                    price = float(clean) / 100 if len(clean) > 3 else float(clean)
                    item_prices.append({"item": product, "price": price})
                else:
                    item_prices.append({"item": product, "price": 0})
            return self._format_result("Vea", f"Vea {location}", item_prices)
        except Exception as e:
            return {"name": "Vea", "status": "error", "message": str(e)}
        finally:
            await browser.close()