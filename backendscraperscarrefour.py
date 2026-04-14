from .base import BaseScraper
from engine import register_scraper
from typing import List, Dict
import re

@register_scraper("Carrefour")
class CarrefourScraper(BaseScraper):
    BASE_URL = "https://www.carrefour.com.ar"

    async def fetch_prices(self, products: List[str], location: str) -> Dict:
        browser = await self._init_browser()
        page = await browser.new_page()
        await page.set_extra_http_headers({"Accept-Language": "es-AR"})
        
        item_prices = []
        try:
            for product in products:
                search_url = f"{self.BASE_URL}/busqueda?text={product.replace(' ', '+')}"
                await page.goto(search_url, wait_until="domcontentloaded", timeout=10000)
                await page.wait_for_selector(".product-price", timeout=8000)
                
                # Extraer primer resultado válido
                price_el = await page.query_selector(".product-price")
                if price_el:
                    raw_price = await price_el.inner_text()
                    # Limpiar formato: "$ 1.299" -> 1299
                    clean_price = re.sub(r"[^\d]", "", raw_price)
                    price = float(clean_price) / 100 if len(clean_price) > 3 else float(clean_price)
                    
                    name_el = await page.query_selector(".product-name")
                    prod_name = await name_el.inner_text() if name_el else product
                    
                    item_prices.append({"item": prod_name, "price": price})
                else:
                    item_prices.append({"item": product, "price": 0})
                    
            return self._format_result("Carrefour", f"Carrefour {location}", item_prices)
        except Exception as e:
            return {"name": "Carrefour", "status": "error", "message": f"Error scraping: {str(e)}"}
        finally:
            await browser.close()