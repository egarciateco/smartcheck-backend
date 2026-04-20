from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import json
import os
from datetime import datetime
from database import (
    init_database, get_db, verificar_limite_consultas, 
    incrementar_consulta, registrar_usuario, activar_suscripcion
)

app = FastAPI(title="SmartCheck-API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

COMERCIOS_FILE = os.path.join(os.path.dirname(__file__), 'comercios.json')
PRODUCTOS_FILE = os.path.join(os.path.dirname(__file__), 'productos.json')

def cargar_comercios():
    try:
        with open(COMERCIOS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {"comercios": []}

def cargar_productos():
    try:
        with open(PRODUCTOS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {"productos": []}

class UsuarioRegister(BaseModel):
    email: str
    password: str
    nombre: str
    telefono: Optional[str] = None
    es_anonimo: bool = True

class ProductoSeleccion(BaseModel):
    producto_id: int
    cantidad: int = 1

class ComparacionRequest(BaseModel):
    usuario_id: int
    productos: List[ProductoSeleccion]
    localidad: str
    provincia: str

class SuscripcionRequest(BaseModel):
    usuario_id: int
    plan: str = "mensual"

@app.on_event("startup")
async def startup_event():
    init_database()

@app.get("/")
def root():
    return {"app": "SmartCheck API", "version": "1.0.0"}

@app.post("/api/registro")
def registro_usuario(usuario: UsuarioRegister):
    exito, resultado = registrar_usuario(
        usuario.email, 
        usuario.password, 
        usuario.nombre,
        usuario.telefono,
        usuario.es_anonimo
    )
    
    if exito:
        return {"success": True, "usuario_id": resultado, "message": "Usuario registrado"}
    else:
        raise HTTPException(status_code=400, detail=resultado)

@app.post("/api/comparar")
def comparar_precios(request: ComparacionRequest):
    puede_consultar, mensaje = verificar_limite_consultas(request.usuario_id)
    
    if not puede_consultar:
        raise HTTPException(status_code=403, detail=mensaje)
    
    comercios = cargar_comercios()
    productos = cargar_productos()
    
    comercios_filtrados = [
        c for cadena in comercios.get('cadenas', {}).values()
        for c in cadena.get('locales', [])
        if c['localidad'].lower() == request.localidad.lower()
        and c['provincia'].lower() == request.provincia.lower()
    ]
    
    if not comercios_filtrados:
        raise HTTPException(status_code=404, detail="No hay comercios en esta localidad")
    
    resultados = []
    
    for comercio in comercios_filtrados:
        total = 0
        items = []
        
        for prod_sel in request.productos:
            producto = next((p for p in productos.get('productos', []) if p['id'] == prod_sel.producto_id), None)
            
            if producto:
                precio_comercio = next(
                    (pc for pc in comercio.get('precios', []) 
                     if pc['producto_id'] == prod_sel.producto_id),
                    None
                )
                
                if precio_comercio:
                    subtotal = precio_comercio['precio'] * prod_sel.cantidad
                    total += subtotal
                    items.append({
                        "producto": producto['nombre'],
                        "cantidad": prod_sel.cantidad,
                        "precio_unitario": precio_comercio['precio'],
                        "subtotal": subtotal
                    })
        
        if items:
            resultados.append({
                "comercio": comercio,
                "items": items,
                "total": round(total, 2)
            })
    
    resultados.sort(key=lambda x: x['total'])
    
    incrementar_consulta(request.usuario_id)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO consultas (usuario_id, productos, total_mas_barato, comercio_mas_barato)
        VALUES (?, ?, ?, ?)
    ''', (
        request.usuario_id,
        json.dumps([p.producto_id for p in request.productos]),
        resultados[0]['total'] if resultados else 0,
        resultados[0]['comercio']['nombre'] if resultados else ""
    ))
    conn.commit()
    conn.close()
    
    return {
        "success": True,
        "resultados": resultados,
        "ahorro_maximo": round(resultados[-1]['total'] - resultados[0]['total'], 2) if len(resultados) > 1 else 0,
        "consultas_restantes": 5 - (verificar_limite_consultas(request.usuario_id)[1].split(": ")[-1] if "Consultas" in verificar_limite_consultas(request.usuario_id)[1] else 0)
    }

@app.get("/api/usuario/{usuario_id}/estado")
def obtener_estado_usuario(usuario_id: int):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT email, nombre, es_anonimo, consultas_gratis, consultas_usadas,
               subscription_activa, subscription_expira, ultima_consulta
        FROM usuarios WHERE id = ?
    ''', (usuario_id,))
    
    usuario = cursor.fetchone()
    conn.close()
    
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    consultas_restantes = usuario['consultas_gratis'] - usuario['consultas_usadas']
    
    return {
        "usuario_id": usuario_id,
        "email": usuario['email'],
        "nombre": usuario['nombre'],
        "es_anonimo": usuario['es_anonimo'],
        "consultas_restantes": max(0, consultas_restantes),
        "subscription_activa": usuario['subscription_activa'],
        "subscription_expira": usuario['subscription_expira'],
        "ultima_consulta": usuario['ultima_consulta']
    }

@app.post("/api/suscripcion")
def activar_suscripcion_endpoint(request: SuscripcionRequest):
    planes = {
        "mensual": 30,
        "trimestral": 90,
        "anual": 365
    }
    
    if request.plan not in planes:
        raise HTTPException(status_code=400, detail="Plan no válido")
    
    exito = activar_suscripcion(request.usuario_id, planes[request.plan])
    
    if exito:
        return {
            "success": True,
            "message": f"Suscripción {request.plan} activada",
            "dias": planes[request.plan]
        }
    else:
        raise HTTPException(status_code=500, detail="Error activando suscripción")

@app.get("/api/comercios")
def listar_comercios(provincia: Optional[str] = None, localidad: Optional[str] = None):
    comercios = cargar_comercios()
    
    todos = []
    for cadena in comercios.get('cadenas', {}).values():
        todos.extend(cadena.get('locales', []))
    
    if provincia:
        todos = [c for c in todos if provincia.lower() in c['provincia'].lower()]
    
    if localidad:
        todos = [c for c in todos if localidad.lower() in c['localidad'].lower()]
    
    return {"comercios": todos, "total": len(todos)}

@app.get("/api/comercios/cadenas")
def listar_cadenas():
    comercios = cargar_comercios()
    cadenas = {}
    
    for cadena_data in comercios.get('cadenas', {}).values():
        nombre = cadena_data['nombre_comercial']
        if nombre not in cadenas:
            cadenas[nombre] = 0
        cadenas[nombre] += len(cadena_data.get('locales', []))
    
    return {
        "cadenas": [{"nombre": k, "cantidad": v} for k, v in sorted(cadenas.items(), key=lambda x: x[1], reverse=True)],
        "total_cadenas": len(cadenas)
    }

@app.get("/api/comercios/provincias")
def listar_provincias():
    comercios = cargar_comercios()
    provincias = {}
    
    for cadena_data in comercios.get('cadenas', {}).values():
        for local in cadena_data.get('locales', []):
            nombre = local['provincia']
            if nombre not in provincias:
                provincias[nombre] = 0
            provincias[nombre] += 1
    
    return {
        "provincias": [{"nombre": k, "cantidad": v} for k, v in sorted(provincias.items(), key=lambda x: x[1], reverse=True)],
        "total_provincias": len(provincias)
    }

@app.get("/api/comercios/localidades")
def listar_localidades(provincia: str = Query(...)):
    comercios = cargar_comercios()
    localidades = {}
    
    for cadena_data in comercios.get('cadenas', {}).values():
        for local in cadena_data.get('locales', []):
            if provincia.lower() in local['provincia'].lower():
                nombre = local['localidad']
                if nombre not in localidades:
                    localidades[nombre] = 0
                localidades[nombre] += 1
    
    return {
        "provincia": provincia,
        "localidades": [{"nombre": k, "cantidad": v} for k, v in sorted(localidades.items(), key=lambda x: x[1], reverse=True)],
        "total": len(localidades)
    }

@app.get("/api/productos")
def listar_productos(categoria: Optional[str] = None):
    productos = cargar_productos()
    
    if categoria:
        productos['productos'] = [p for p in productos['productos'] if categoria.lower() in p['categoria'].lower()]
    
    return productos

@app.get("/api/productos/categorias")
def listar_categorias():
    productos = cargar_productos()
    categorias = {}
    
    for prod in productos.get('productos', []):
        nombre = prod['categoria']
        if nombre not in categorias:
            categorias[nombre] = 0
        categorias[nombre] += 1
    
    return {
        "categorias": [{"nombre": k, "cantidad": v} for k, v in sorted(categorias.items(), key=lambda x: x[1], reverse=True)],
        "total_categorias": len(categorias)
    }

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
