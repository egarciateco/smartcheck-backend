from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import time
import json
import os
import asyncio
from engine import scrape_all_stores

app = FastAPI(title="SmartCheck-REAL-LIVE", version="3.0.0")

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
        with open(os.path.join(backend_dir, filename), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Error cargando {filename}: {e}")
        return {}

@app.get("/")
def root():
    return {"app": "SmartCheck-REAL-LIVE 🛒", "status": "running", "data_source": "WEBS_COMERCIALES_LIVE"}

@app.get("/health")
def health():
    return {"status": "ok", "timestamp": time.time()}

@app.get("/api/v1/locations/provincias")
def get_provincias():
    return {"provincias": list(load_json("provincias.json").keys())}

@app.get("/api/v1/locations/localidades")
def get_localidades(provincia: str = Query(...)):
    data = load_json("provincias.json")
    if provincia not in data:
        raise HTTPException(404, "Provincia no encontrada")
    return {"provincia": provincia, "localidades": data[provincia]}

@app.get("/api/v1/categorias")
def get_categorias():
    return {"categorias": list(load_json("categorias.json").keys())}

@app.get("/api/v1/categorias/items")
def get_categoria_items(categoria: str = Query(...)):
    data = load_json("categorias.json")
    if categoria not in data:
        raise HTTPException(404, "Rubro no encontrado")
    return {"categoria": categoria, "items": data[categoria]}

# 🔍 COMPARACIÓN EN TIEMPO REAL (SIN SIMULACIÓN)
@app.get("/api/v1/compare")
async def compare_prices(
    products: str = Query(...),
    provincia: str = Query(...),
    localidad: str = Query(...),
    categoria: str = Query("General")
):
    product_list = [p.strip() for p in products.split(",") if p.strip()]
    if not product_list:
        raise HTTPException(400, "Faltan artículos")

    # 🛒 COMERCIOS A CONSULTAR EN TIEMPO REAL
    STORES_TO_SCRAPE = ["Carrefour", "Coto"]  # Agregar más según necesites
    
    # 🌐 EJECUTAR SCRAPING EN PARALELO (PRECIO ACTUAL DE CADA WEB)
    live_results = await scrape_all_stores(STORES_TO_SCRAPE, product_list, localidad)

    # Filtrar solo los que trajeron precios reales
    valid_stores = [r for r in live_results if r.get("status") == "success" and r.get("total", 0) > 0]
    error_stores = [r for r in live_results if r.get("status") != "success"]

    if not valid_stores and not error_stores:
        raise HTTPException(404, "Ningún comercio disponible en este momento")

    valid_stores.sort(key=lambda x: x["total"])

    return {
        "location": {"provincia": provincia, "localidad": localidad},
        "categoria": categoria,
        "products": product_list,
        "source": "WEB_SCRAPING_LIVE",
        "all_stores": valid_stores,
        "scraping_errors": error_stores,  # Transparencia total
        "cheapest": valid_stores[0] if valid_stores else None,
        "timestamp": time.time(),
        "note": "Precios extraídos EN VIVO de las páginas oficiales de cada comercio. Revisados en cada consulta."
    }

@app.get("/api/v1/premium/link")
def premium_link():
    return {"payment_url": "https://mpago.la/2GetRzy"}