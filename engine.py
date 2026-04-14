import asyncio
import time
from typing import List, Dict, Optional
from playwright.async_api import async_playwright

# Registro de scrapers disponibles
SCRAPERS = {}

def register_scraper(name: str):
    def decorator(cls):
        SCRAPERS[name] = cls
        return cls
    return decorator

def get_scraper(name: str):
    cls = SCRAPERS.get(name)
    if not cls:
        raise ValueError(f"Scraper '{name}' no registrado")
    return cls()

async def scrape_store(store_name: str, products: List[str], location: str, timeout: int = 15):
    """Ejecuta el scraper de un comercio con timeout y manejo de errores"""
    try:
        scraper = get_scraper(store_name)
        result = await asyncio.wait_for(
            scraper.fetch_prices(products, location),
            timeout=timeout
        )
        return result
    except asyncio.TimeoutError:
        return {"name": store_name, "status": "timeout", "message": "El comercio tardó demasiado en responder"}
    except Exception as e:
        return {"name": store_name, "status": "error", "message": str(e)}

async def scrape_all_stores(stores: List[str], products: List[str], location: str):
    """Ejecuta todos los scrapers en paralelo y devuelve resultados reales"""
    tasks = [scrape_store(store, products, location) for store in stores]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    final_results = []
    for res in results:
        if isinstance(res, Exception):
            final_results.append({"name": "Desconocido", "status": "error", "message": str(res)})
        elif res.get("status") == "success":
            final_results.append(res)
        else:
            final_results.append(res)
            
    return final_results