from abc import ABC, abstractmethod
from typing import List, Dict
from playwright.async_api import async_playwright, Browser, Page

class BaseScraper(ABC):
    @abstractmethod
    async def fetch_prices(self, products: List[str], location: str) -> Dict:
        pass

    async def _init_browser(self) -> Browser:
        p = await async_playwright().start()
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
        return browser

    def _format_result(self, name: str, address: str, item_prices: List[Dict], status: str = "success") -> Dict:
        total = sum(p["price"] for p in item_prices if isinstance(p["price"], (int, float)))
        return {
            "name": name,
            "address": address,
            "total": total,
            "items_found": len(item_prices),
            "delivery_time": "20-60 min" if "super" in name.lower() else "Retiro en tienda",
            "metodos_pago": ["💳 Efectivo", "💳 Débito", "📱 Mercado Pago"],
            "item_prices": item_prices,
            "status": status
        }