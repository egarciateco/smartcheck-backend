from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from playwright.async_api import async_playwright
import asyncio
import json
import os
import time
from typing import List, Dict

app = FastAPI(title="SmartCheck-API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper para cargar JSONs
def load_json(filename):
    try:
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        filepath = os.path.join(backend_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

@app.get("/")
def root():
    return {"app": "SmartCheck-API", "status": "running", "version": "1.0.0"}

@app.get("/health")
def health():
    return {"status": "ok", "timestamp": time.time()}

@app.get("/api/v1/locations/provincias")
def get_provincias():
    data = load_json("provincias.json")
    provincias = list(data.keys()) if data and isinstance(data, dict) else []
    if not provincias:
        provincias = ["Buenos Aires", "CABA", "Córdoba", "Santa Fe"]
    return {"provincias": provincias}

@app.get("/api/v1/locations/localidades")
def get_localidades(provincia: str = Query(...)):
    data = load_json("provincias.json")
    if provincia not in data:
        raise HTTPException(status_code=404, detail="Provincia no encontrada")
    return {"provincia": provincia, "localidades": data[provincia]}

@app.get("/api/v1/categorias")
def get_categorias():
    data = load_json("categorias.json")
    categorias = list(data.keys()) if data and isinstance(data, dict) else []
    if not categorias:
        categorias = ["Supermercados", "Farmacias", "Electrónica"]
    return {"categorias": categorias}

@app.get("/api/v1/categorias/items")
def get_categoria_items(categoria: str = Query(...)):
    data = load_json("categorias.json")
    if categoria not in data:
        raise HTTPException(status_code=404, detail="Rubro no encontrado")
    items = data[categoria] if isinstance(data[categoria], list) else []
    if not items:
        items = ["leche", "aceite", "arroz", "fideos", "azúcar"]
    return {"categoria": categoria, "items": items}

# 🔍 SCRAPING REAL - Carrefour
async def scrape_carrefour(product: str, localidad: str) -> List[Dict]:
    results = []
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            search_url = f"https://www.carrefour.com.ar/s?text={product.replace(' ', '%20')}"
            await page.goto(search_url, timeout=30000)
            await page.wait_for_timeout(3000)
            products = await page.query_selector_all('.product-item')
            for prod in products[:3]:
                try:
                    name_el = await prod.query_selector('.product-name')
                    price_el = await prod.query_selector('.price-now')
                    if name_el and price_el:
                        name = await name_el.inner_text()
                        price_text = await price_el.inner_text()
                        price = float(price_text.replace('$', '').replace('.', '').replace(',', '.'))
                        results.append({
                            "store": "Carrefour",
                            "product": name.strip(),
                            "price": price,
                            "url": search_url,
                            "location": localidad
                        })
                except:
                    continue
            await browser.close()
    except Exception as e:
        print(f"Error scraping Carrefour: {e}")
    return results

# 🔍 SCRAPING REAL - Coto
async def scrape_coto(product: str, localidad: str) -> List[Dict]:
    results = []
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            search_url = f"https://www.cotodigital3.com.ar/sitios/cdigi/buscar/?buscar={product.replace(' ', '%20')}"
            await page.goto(search_url, timeout=30000)
            await page.wait_for_timeout(3000)
            products = await page.query_selector_all('.producto')
            for prod in products[:3]:
                try:
                    name_el = await prod.query_selector('.nombreProducto')
                    price_el = await prod.query_selector('.precioActual')
                    if name_el and price_el:
                        name = await name_el.inner_text()
                        price_text = await price_el.inner_text()
                        price = float(price_text.replace('$', '').replace('.', '').replace(',', '.'))
                        results.append({
                            "store": "Coto",
                            "product": name.strip(),
                            "price": price,
                            "url": search_url,
                            "location": localidad
                        })
                except:
                    continue
            await browser.close()
    except Exception as e:
        print(f"Error scraping Coto: {e}")
    return results

@app.get("/api/v1/compare")
async def compare_prices(
    products: str = Query(...),
    provincia: str = Query(...),
    localidad: str = Query(...),
    categoria: str = Query("General")
):
    product_list = [p.strip() for p in products.split(",") if p.strip()]
    if not product_list:
        raise HTTPException(status_code=400, detail="Faltan artículos")
    
    all_results = []
    for product in product_list:
        carrefour_results = await scrape_carrefour(product, localidad)
        coto_results = await scrape_coto(product, localidad)
        all_results.extend(carrefour_results)
        all_results.extend(coto_results)
    
    stores_dict = {}
    for result in all_results:
        store_name = result["store"]
        if store_name not in stores_dict:
            stores_dict[store_name] = {
                "name": store_name,
                "address": f"{store_name} {localidad}",
                "total": 0,
                "items_found": 0,
                "delivery_time": "45-60 min" if store_name == "Carrefour" else "60-90 min",
                "metodos_pago": ["Efectivo", "Débito", "Crédito", "Mercado Pago"],
                "item_prices": []
            }
        stores_dict[store_name]["item_prices"].append({
            "item": result["product"],
            "price": result["price"]
        })
        stores_dict[store_name]["total"] += result["price"]
        stores_dict[store_name]["items_found"] += 1
    
    all_stores = list(stores_dict.values())
    all_stores.sort(key=lambda x: x["total"])
    
    if not all_stores:
        return {
            "location": {"provincia": provincia, "localidad": localidad},
            "categoria": categoria,
            "products": product_list,
            "source": "no_results",
            "all_stores": [],
            "cheapest": None,
            "timestamp": time.time(),
            "message": "No se encontraron resultados reales. Intentá con productos más comunes."
        }
    
    return {
        "location": {"provincia": provincia, "localidad": localidad},
        "categoria": categoria,
        "products": product_list,
        "source": "real_scraping",
        "all_stores": all_stores,
        "cheapest": {
            "name": all_stores[0]["name"],
            "total": all_stores[0]["total"]
        },
        "timestamp": time.time(),
        "scraped_from": ["Carrefour", "Coto"]
    }

@app.get("/api/v1/premium/link")
def premium_link():
    return {"payment_url": "https://mpago.la/2GetRzy"}
