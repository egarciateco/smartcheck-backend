import sqlite3
import time
import os
from typing import List, Dict, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "real_prices.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS stores
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, category TEXT, 
                  location TEXT, url TEXT, last_updated REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS prices
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, store_id INTEGER, product_name TEXT,
                  price REAL, currency TEXT, scraped_at REAL, source_url TEXT,
                  FOREIGN KEY(store_id) REFERENCES stores(id))''')
    conn.commit()
    conn.close()

def add_store(name: str, category: str, location: str, url: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO stores (name, category, location, url, last_updated) VALUES (?,?,?,?,?)",
              (name, category, location, url, 0))
    conn.commit()
    conn.close()

def save_prices(store_id: int, prices: List[Dict]):
    if not prices: return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = time.time()
    # Actualizar timestamp de la tienda
    c.execute("UPDATE stores SET last_updated = ? WHERE id = ?", (now, store_id))
    for p in prices:
        c.execute("INSERT INTO prices (store_id, product_name, price, currency, scraped_at, source_url) VALUES (?,?,?,?,?,?)",
                  (store_id, p["product"], p["price"], "ARS", now, p.get("url", "")))
    conn.commit()
    conn.close()

def get_real_prices(products: List[str], location: str, category: str) -> List[Dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Buscar precios reales actualizados en las últimas 24hs
    query = '''
        SELECT s.name as store_name, s.address, s.url as store_url, 
               p.product_name, p.price, p.scraped_at
        FROM prices p
        JOIN stores s ON p.store_id = s.id
        WHERE s.location = ? AND s.category = ? 
          AND p.product_name IN ({})
          AND p.scraped_at > ?
        ORDER BY s.name, p.product_name
    '''.format(','.join('?'*len(products)))
    
    params = [location, category] + products + [time.time() - 86400]
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    
    # Agrupar por tienda
    stores = {}
    for row in rows:
        name = row["store_name"]
        if name not in stores:
            stores[name] = {"name": name, "address": row["address"] or "Dirección no disponible", 
                            "total": 0, "items_found": 0, "delivery_time": "Verificar en sitio",
                            "metodos_pago": ["💳 Efectivo", "💳 Débito", "📱 Transferencia"],
                            "item_prices": []}
        stores[name]["total"] += row["price"]
        stores[name]["items_found"] += 1
        stores[name]["item_prices"].append({"item": row["product_name"], "price": row["price"]})
        
    return list(stores.values())