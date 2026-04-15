from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import time
import os
import json

app = FastAPI(title="SmartCheck-API", version="1.0.0")

# CORS para permitir conexiones desde cualquier origen
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper para cargar JSONs desde el directorio del backend
def load_json(filename):
    try:
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        filepath = os.path.join(backend_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Error cargando {filename}: {e}")
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
    # Si el JSON tiene formato { "Provincia": [...] }, extraemos las claves
    provincias = list(data.keys()) if data and isinstance(data, dict) else []
    # Fallback si el JSON está vacío
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

@app.get("/api/v1/compare")
def compare_prices(
    products: str = Query(...),
    provincia: str = Query(...),
    localidad: str = Query(...),
    categoria: str = Query("General")
):
    product_list = [p.strip() for p in products.split(",") if p.strip()]
    if not product_list:
        raise HTTPException(status_code=400, detail="Faltan artículos")
    
    total = sum([1250 for _ in product_list])
    
    return {
        "location": {"provincia": provincia, "localidad": localidad},
        "categoria": categoria,
        "products": product_list,
        "source": "mock_data",
        "all_stores": [
            {
                "name": f"Comercio Demo {localidad}",
                "address": f"Av. Prueba 123, {localidad}",
                "total": total,
                "items_found": len(product_list),
                "delivery_time": "30 min",
                "metodos_pago": ["Efectivo", "Débito", "Mercado Pago"],
                "item_prices": [{"item": p, "price": 1250} for p in product_list]
            }
        ],
        "cheapest": {"name": f"Comercio Demo {localidad}", "total": total},
        "timestamp": time.time()
    }

@app.get("/api/v1/premium/link")
def premium_link():
    return {"payment_url": "https://mpago.la/2GetRzy"}
