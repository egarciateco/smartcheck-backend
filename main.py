from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from playwright.async_api import async_playwright
import json, os, time, asyncio
from typing import List, Dict

app = FastAPI(title="SmartCheck-API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    return {"app": "SmartCheck-API", "status": "running", "version": "2.0.0"}

@app.get("/health")
def health():
    return {"status": "ok", "timestamp": time.time()}

@app.get("/api/v1/locations/provincias")
def get_provincias():
    data = load_json("provincias.json")
    provincias = list(data.keys()) if data and isinstance(data, dict) else []
    if not provincias:
        provincias = ["Buenos Aires", "CABA", "Córdoba", "Santa Fe", "Entre Ríos"]
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

# 🔍 SCRAPING REAL - CARREFOUR
async def scrape_carrefour(producto: str, localidad: str) -> List[Dict]:
    results = []
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(user_agent="Mozilla/5.0")
            
            url = f"https://www.carrefour.com.ar/s?text={producto.replace(' ', '%20')}"
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)
            
            # Extraer productos
            products = await page.query_selector_all('[data-testid="product-card"], .product-item, .product')
            
            for prod in products[:5]:
                try:
                    name_el = await prod.query_selector('[data-testid="product-name"], .product-name, .name, h3')
                    price_el = await prod.query_selector('[data-testid="product-price"], .price-now, .price, [class*="price"]')
                    
                    if name_el and price_el:
                        name = await name_el.inner_text()
                        price_text = await price_el.inner_text()
                        
                        # Limpiar precio
                        price_clean = price_text.replace('$', '').replace('.', '').replace(',', '.').strip()
                        price_digits = ''.join(c for c in price_clean if c.isdigit() or c == '.')
                        
                        if price_digits:
                            price = float(price_digits)
                            if price > 0 and price < 50000:  # Validar precio razonable
                                results.append({
                                    "store": "Carrefour",
                                    "product": name.strip()[:80],
                                    "price": round(price, 2),
                                    "url": url,
                                    "location": localidad,
                                    "address": f"Carrefour {localidad}",
                                    "delivery_time": "45-60 min",
                                    "metodos_pago": ["Efectivo", "Débito", "Crédito", "Mercado Pago"],
                                    "source": "real_scraping",
                                    "scraped_at": time.time()
                                })
                except Exception as e:
                    print(f"Error extrayendo producto Carrefour: {e}")
                    continue
            
            await browser.close()
    except Exception as e:
        print(f"Error scraping Carrefour: {e}")
    
    return results

# 🔍 SCRAPING REAL - COTO
async def scrape_coto(producto: str, localidad: str) -> List[Dict]:
    results = []
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(user_agent="Mozilla/5.0")
            
            url = f"https://www.cotodigital3.com.ar/sitios/cdigi/buscar/?buscar={producto.replace(' ', '%20')}"
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)
            
            products = await page.query_selector_all('.producto, [class*="product"], .item')
            
            for prod in products[:5]:
                try:
                    name_el = await prod.query_selector('.nombreProducto, [class*="name"], h3')
                    price_el = await prod.query_selector('.precioActual, [class*="price"], .price')
                    
                    if name_el and price_el:
                        name = await name_el.inner_text()
                        price_text = await price_el.inner_text()
                        
                        price_clean = price_text.replace('$', '').replace('.', '').replace(',', '.').strip()
                        price_digits = ''.join(c for c in price_clean if c.isdigit() or c == '.')
                        
                        if price_digits:
                            price = float(price_digits)
                            if price > 0 and price < 50000:
                                results.append({
                                    "store": "Coto",
                                    "product": name.strip()[:80],
                                    "price": round(price, 2),
                                    "url": url,
                                    "location": localidad,
                                    "address": f"Coto {localidad}",
                                    "delivery_time": "60-90 min",
                                    "metodos_pago": ["Efectivo", "Débito", "Crédito", "Mercado Pago"],
                                    "source": "real_scraping",
                                    "scraped_at": time.time()
                                })
                except Exception as e:
                    print(f"Error extrayendo producto Coto: {e}")
                    continue
            
            await browser.close()
    except Exception as e:
        print(f"Error scraping Coto: {e}")
    
    return results

# 🔍 SCRAPING REAL - JUMBO
async def scrape_jumbo(producto: str, localidad: str) -> List[Dict]:
    results = []
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(user_agent="Mozilla/5.0")
            
            url = f"https://www.jumboargentina.com.ar/buscar?q={producto.replace(' ', '%20')}"
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)
            
            products = await page.query_selector_all('.producto, [data-product], .product-card')
            
            for prod in products[:5]:
                try:
                    name_el = await prod.query_selector('.nombre, [class*="name"], h3')
                    price_el = await prod.query_selector('.precio, [class*="price"], .price')
                    
                    if name_el and price_el:
                        name = await name_el.inner_text()
                        price_text = await price_el.inner_text()
                        
                        price_clean = price_text.replace('$', '').replace('.', '').replace(',', '.').strip()
                        price_digits = ''.join(c for c in price_clean if c.isdigit() or c == '.')
                        
                        if price_digits:
                            price = float(price_digits)
                            if price > 0 and price < 50000:
                                results.append({
                                    "store": "Jumbo",
                                    "product": name.strip()[:80],
                                    "price": round(price, 2),
                                    "url": url,
                                    "location": localidad,
                                    "address": f"Jumbo {localidad}",
                                    "delivery_time": "40-55 min",
                                    "metodos_pago": ["Efectivo", "Débito", "Crédito", "Mercado Pago"],
                                    "source": "real_scraping",
                                    "scraped_at": time.time()
                                })
                except Exception as e:
                    print(f"Error extrayendo producto Jumbo: {e}")
                    continue
            
            await browser.close()
    except Exception as e:
        print(f"Error scraping Jumbo: {e}")
    
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
    
    # Ejecutar scraping en paralelo
    all_results = []
    
    for producto in product_list:
        # Scraping en los 3 supermercados principales
        carrefour_results, coto_results, jumbo_results = await asyncio.gather(
            scrape_carrefour(producto, localidad),
            scrape_coto(producto, localidad),
            scrape_jumbo(producto, localidad),
            return_exceptions=True
        )
        
        # Filtrar excepciones
        if isinstance(carrefour_results, list):
            all_results.extend(carrefour_results)
        if isinstance(coto_results, list):
            all_results.extend(coto_results)
        if isinstance(jumbo_results, list):
            all_results.extend(jumbo_results)
    
    # Si hay resultados reales, agrupar por comercio
    if all_results:
        stores_dict = {}
        for result in all_results:
            store_name = result["store"]
            if store_name not in stores_dict:
                stores_dict[store_name] = {
                    "name": store_name,
                    "address": result["address"],
                    "total": 0,
                    "items_found": 0,
                    "delivery_time": result["delivery_time"],
                    "metodos_pago": result["metodos_pago"],
                    "item_prices": [],
                    "source": "real_scraping",
                    "scraped_at": result["scraped_at"]
                }
            stores_dict[store_name]["item_prices"].append({
                "item": result["product"],
                "price": result["price"]
            })
            stores_dict[store_name]["total"] += result["price"]
            stores_dict[store_name]["items_found"] += 1
        
        all_stores = list(stores_dict.values())
        all_stores.sort(key=lambda x: x["total"])
        
        return {
            "location": {"provincia": provincia, "localidad": localidad},
            "categoria": categoria,
            "products": product_list,
            "source": "real_scraping",
            "all_stores": all_stores,
            "cheapest": {"name": all_stores[0]["name"], "total": all_stores[0]["total"]},
            "timestamp": time.time(),
            "scraped_from": ["Carrefour", "Coto", "Jumbo"],
            "note": "Precios reales obtenidos directamente de los sitios web de los supermercados. Pueden variar según promoción y disponibilidad."
        }
    
    # ❌ NO HAY DATOS REALES - Ser transparente
    return {
        "location": {"provincia": provincia, "localidad": localidad},
        "categoria": categoria,
        "products": product_list,
        "source": "no_real_data",
        "all_stores": [],
        "cheapest": None,
        "timestamp": time.time(),
        "message": "No se encontraron precios reales en este momento. Esto puede deberse a:",
        "reasons": [
            "El producto no está disponible en los supermercados consultados",
            "Los sitios web están temporalmente indisponibles",
            "El scraping fue bloqueado por los sitios",
            "Intentá con otro producto más común (leche, aceite, arroz, fideos)"
        ],
        "suggestion": "Volvé a intentar en unos minutos o probá con productos de primera necesidad"
    }

@app.get("/api/v1/premium/link")
def premium_link():
    return {"payment_url": "https://mpago.la/2GetRzy"}
