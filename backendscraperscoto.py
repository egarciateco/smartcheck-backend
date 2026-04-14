from .base import BaseScraper
from engine import register_scraper
from typing import List, Dict
import re

@register_scraper("Coto")
class CotoScraper(BaseScraper):
    BASE_URL = "https://www.cotodigital3.com.ar"

    async def fetch_prices(self, products: List[str], location: str) -> Dict:
        browser = await self._init_browser()
        page = await browser.new_page()
        
        item_prices = []
        try:
            for product in products:
                url = f"{self.BASE_URL}/site/busquedas?text={product.replace(' ', '+')}"
                await page.goto(url, wait_until="networkidle", timeout=10000)
                
                # Coto usa estructura dinámica, esperar grilla
                await page.wait_for_selector(".product-item", timeout=8000)
                
                price_el = await page.query_selector(".product-price span")
                if price_el:
                    raw = await price_el.inner_text()
                    clean = re.sub(r"[^\d]", "", raw)
                    price = float(clean) / 100 if len(clean) > 3 else float(clean)
                    
                    name_el = await page.query_selector(".product-name")
                    prod_name = await name_el.inner_text() if name_el else product
                    
                    item_prices.append({"item": prod_name, "price": price})
                else:
                    item_prices.append({"item": product, "price": 0})
                    
            return self._format_result("Coto Digital", f"Coto {location}", item_prices)
        except Exception as e:
            return {"name": "Coto", "status": "error", "message": f"Error scraping: {str(e)}"}
        finally:
            await browser.close()