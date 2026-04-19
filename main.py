from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import json, os, time
from typing import List, Dict

app = FastAPI(title="SmartCheck-API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔥 API DE MERCADOLIBRE (oficial y gratis)
MELI_API_BASE = "https://api.mercadolibre.com"

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
    return {"app": "SmartCheck-API", "status": "running", "version": "3.0.0"}

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

# 🔍 BUSCAR EN MERCADOLIBRE
async def search_meli(producto: str, localidad: str) -> List[Dict]:
    """Busca productos en MercadoLibre Argentina"""
    results = []
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Buscar productos
            search_url = f"{MELI_API_BASE}/sites/MLA/search"
            params = {
                "q": producto,
                "limit": 20,
                "condition": "new"
            }
            
            response = await client.get(search_url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                for item in data.get("results", [])[:10]:
                    # Filtrar solo supermercados conocidos
                    seller = item.get("seller", {})
                    seller_name = seller.get("nickname", "").lower()
                    
                    # Supermercados oficiales en MercadoLibre
                    supermercados_oficiales = ["carrefour", "coto", "jumbo", "disco", "vital", "supermercados"]
                    
                    es_supermercado = any(super in seller_name for super in supermercados_oficiales)
                    
                    # O si tiene envío full (más confiable)
                    tiene_full = item.get("shipping", {}).get("free_shipping", False)
                    
                    if es_supermercado or tiene_full:
                        price = item.get("price", 0)
                        if price and price > 0 and price < 50000:
                            # Obtener nombre del vendedor
                            store_name = seller.get("nickname", "Tienda Oficial")
                            
                            # Mapear a nombres más amigables
                            store_map = {
                                "carrefour": "Carrefour",
                                "coto": "Coto Digital",
                                "jumbo": "Jumbo",
                                "disco": "Disco",
                                "vital": "Vital",
                            }
                            
                            for key, value in store_map.items():
                                if key in seller_name.lower():
                                    store_name = value
                                    break
                            
                            results.append({
                                "store": store_name,
                                "product": item.get("title", "")[:80],
                                "price": round(price, 2),
                                "url": item.get("permalink", ""),
                                "location": localidad,
                                "address": f"{store_name} - Envío a {localidad}",
                                "delivery_time": "24-48 hs" if item.get("shipping", {}).get("free_shipping") else "48-72 hs",
                                "metodos_pago": ["Efectivo", "Débito", "Crédito", "Mercado Pago"],
                                "source": "mercadolibre_api",
                                "fetched_at": time.time()
                            })
    except Exception as e:
        print(f"Error buscando en MercadoLibre: {e}")
    
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
    
    # Buscar en MercadoLibre
    all_results = []
    
    for producto in product_list:
        results = await search_meli(producto, localidad)
        all_results.extend(results)
    
    # Si hay resultados, agrupar por comercio
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
                    "source": "mercadolibre_api",
                    "fetched_at": result["fetched_at"]
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
            "source": "mercadolibre_api",
            "all_stores": all_stores,
            "cheapest": {"name": all_stores[0]["name"], "total": all_stores[0]["total"]},
            "timestamp": time.time(),
            "fetched_from": "MercadoLibre Argentina",
            "note": "Precios reales obtenidos de la API oficial de MercadoLibre. Supermercados con tienda oficial en la plataforma."
        }
    
    # No hay resultados
    return {
        "location": {"provincia": provincia, "localidad": localidad},
        "categoria": categoria,
        "products": product_list,
        "source": "no_results",
        "all_stores": [],
        "cheapest": None,
        "timestamp": time.time(),
        "message": "No se encontraron productos en MercadoLibre",
        "suggestion": "Intentá con términos más genéricos (ej: 'leche' en vez de 'leche la serenisima descremada')"
    }

@app.get("/api/v1/premium/link")
def premium_link():
    return {"payment_url": "https://mpago.la/2GetRzy"}
