from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import time

app = FastAPI(title="SmartCheck-API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"app": "SmartCheck-API", "status": "running", "version": "1.0.0"}

@app.get("/health")
def health():
    return {"status": "ok", "timestamp": time.time()}

@app.get("/api/v1/locations/provincias")
def get_provincias():
    return {"provincias": ["Buenos Aires", "CABA", "Córdoba", "Santa Fe"]}

@app.get("/api/v1/locations/localidades")
def get_localidades(provincia: str = Query(...)):
    data = {
        "Buenos Aires": ["La Plata", "Mar del Plata", "Bahía Blanca"],
        "CABA": ["Palermo", "Recoleta", "Belgrano"],
        "Córdoba": ["Córdoba Capital", "Villa María"],
        "Santa Fe": ["Rosario", "Santa Fe Capital"]
    }
    if provincia not in data:
        raise HTTPException(status_code=404, detail="Provincia no encontrada")
    return {"provincia": provincia, "localidades": data[provincia]}

@app.get("/api/v1/categorias")
def get_categorias():
    return {"categorias": ["Supermercados", "Farmacias", "Electrónica"]}

@app.get("/api/v1/categorias/items")
def get_categoria_items(categoria: str = Query(...)):
    data = {
        "Supermercados": ["leche", "aceite", "arroz", "fideos", "azúcar"],
        "Farmacias": ["ibuprofeno", "paracetamol", "alcohol", "curitas"],
        "Electrónica": ["cable usb", "auriculares", "powerbank"]
    }
    if categoria not in data:
        raise HTTPException(status_code=404, detail="Rubro no encontrado")
    return {"categoria": categoria, "items": data[categoria]}

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
    
    # DATOS DE PRUEBA (para validar conexión frontend-backend)
    return {
        "location": {"provincia": provincia, "localidad": localidad},
        "categoria": categoria,
        "products": product_list,
        "source": "mock_data_for_testing",
        "all_stores": [
            {
                "name": f"Comercio Demo {localidad}",
                "address": f"Av. Prueba 123, {localidad}",
                "total": sum([1250 for _ in product_list]),
                "items_found": len(product_list),
                "delivery_time": "30 min",
                "metodos_pago": ["💳 Efectivo", "💳 Débito", "📱 Mercado Pago"],
                "item_prices": [{"item": p, "price": 1250} for p in product_list]
            },
            {
                "name": f"Otro Comercio {localidad}",
                "address": f"Calle Test 456, {localidad}",
                "total": sum([1350 for _ in product_list]),
                "items_found": len(product_list),
                "delivery_time": "45 min",
                "metodos_pago": ["💳 Efectivo", "📱 Mercado Pago"],
                "item_prices": [{"item": p, "price": 1350} for p in product_list]
            }
        ],
        "cheapest": {
            "name": f"Comercio Demo {localidad}",
            "total": sum([1250 for _ in product_list])
        },
        "timestamp": time.time(),
        "note": "Datos de prueba para validar conexión. Scraping real se activará después."
    }

@app.get("/api/v1/premium/link")
def premium_link():
    return {"payment_url": "https://mpago.la/2GetRzy"}
