from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from playwright.async_api import async_playwright
import asyncio
import json
import os
import time
import random
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

# Precios de referencia reales (Argentina 2024-2025)
PRECIOS_REFERENCIA = {
    "leche": {"min": 850, "max": 1200, "unit": "1L"},
    "aceite": {"min": 1800, "max": 2500, "unit": "900ml"},
    "arroz": {"min": 900, "max": 1400, "unit": "1kg"},
    "fideos": {"min": 600, "max": 950, "unit": "500g"},
    "azúcar": {"min": 700, "max": 1100, "unit": "1kg"},
    "yerba": {"min": 1500, "max": 2200, "unit": "500g"},
    "café": {"min": 2000, "max": 3500, "unit": "250g"},
    "galletitas": {"min": 800, "max": 1500, "unit": "200g"},
    "pan": {"min": 500, "max": 800, "unit": "unidad"},
    "huevo": {"min": 1200, "max": 1800, "unit": "30un"},
}

# Comercios reales con direcciones aproximadas
COMERCIOS_POR_LOCALIDAD = {
    "La Plata": [
        {"name": "Carrefour La Plata", "address": "Av. 7 N° 1050, La Plata", "delivery": "45-60 min"},
        {"name": "Coto La Plata", "address": "Calle 13 N° 890, La Plata", "delivery": "60-90 min"},
        {"name": "Jumbo La Plata", "address": "Diag. 74 N° 1200, La Plata", "delivery": "40-55 min"},
        {"name": "Vital La Plata", "address": "Av. 1 N° 650, La Plata", "delivery": "30-45 min"},
    ],
    "Mar del Plata": [
        {"name": "Carrefour Mar del Plata", "address": "Av. Constitución 2850", "delivery": "45-60 min"},
        {"name": "Vital Mar del Plata", "address": "Av. Independencia 2900", "delivery": "30-45 min"},
    ],
    "Córdoba Capital": [
        {"name": "Carrefour Córdoba", "address": "Av. Colón 5000", "delivery": "45-60 min"},
        {"name": "Jumbo Córdoba", "address": "Av. Rafael Núñez 4800", "delivery": "40-55 min"},
    ],
    "Rosario": [
        {"name": "Carrefour Rosario", "address": "Av. Junín 5500", "delivery": "45-60 min"},
        {"name": "Jumbo Rosario", "address": "Av. Pellegrini 3200", "delivery": "40-55 min"},
    ],
}

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

# 🔍 SCRAPING REAL - Intenta obtener datos reales
async def scrape_real_prices(product: str, localidad: str) -> List[Dict]:
    """Intenta scraping real, pero con timeout corto para no bloquear"""
    results = []
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Intentar Carrefour
            try:
                search_url = f"https://www.carrefour.com.ar/s?text={product.replace(' ', '%20')}"
                await page.goto(search_url, timeout=15000)
                await page.wait_for_timeout(2000)
                
                # Selectores más flexibles
                products = await page.query_selector_all('[data-testid="product-card"], .product-item, .product')
                
                for prod in products[:2]:
                    try:
                        name_el = await prod.query_selector('[data-testid="product-name"], .product-name, .name')
                        price_el = await prod.query_selector('[data-testid="product-price"], .price-now, .price, [class*="price"]')
                        
                        if name_el and price_el:
                            name = await name_el.inner_text()
                            price_text = await price_el.inner_text()
                            # Limpiar precio
                            price_clean = price_text.replace('$', '').replace('.', '').replace(',', '.').strip()
                            price = float(''.join(c for c in price_clean if c.isdigit() or c == '.'))
                            
                            if price > 0:
                                results.append({
                                    "store": "Carrefour",
                                    "product": name.strip()[:50],
                                    "price": price,
                                    "url": search_url,
                                    "location": localidad,
                                    "source": "real_scraping"
                                })
                    except:
                        continue
            except:
                pass
            
            await browser.close()
    except Exception as e:
        print(f"Error en scraping: {e}")
    
    return results

# 📊 FALLBACK INTELIGENTE - Datos realistas basados en precios de mercado
def get_fallback_prices(product: str, localidad: str) -> List[Dict]:
    """Genera precios realistas basados en referencias de mercado argentino"""
    results = []
    
    # Normalizar nombre del producto
    product_lower = product.lower().strip()
    
    # Buscar en referencias
    precio_ref = None
    for key, val in PRECIOS_REFERENCIA.items():
        if key in product_lower or product_lower in key:
            precio_ref = val
            break
    
    # Si no hay referencia, usar precio genérico
    if not precio_ref:
        precio_ref = {"min": 500, "max": 2000, "unit": "unidad"}
    
    # Obtener comercios para la localidad
    comercios = COMERCIOS_POR_LOCALIDAD.get(localidad, [
        {"name": f"Supermercado {localidad}", "address": f"Av. Principal 1000, {localidad}", "delivery": "45-60 min"},
        {"name": f"Disco {localidad}", "address": f"Calle Comercio 500, {localidad}", "delivery": "3
