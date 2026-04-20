import sqlite3
import os
from datetime import datetime

DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'smartcheck.db')

def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    conn = get_db()
    cursor = conn.cursor()
    
    # Tabla de usuarios
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            password TEXT,
            nombre TEXT,
            telefono TEXT,
            es_anonimo BOOLEAN DEFAULT 1,
            consultas_gratis INTEGER DEFAULT 5,
            consultas_usadas INTEGER DEFAULT 0,
            subscription_activa BOOLEAN DEFAULT 0,
            subscription_expira TIMESTAMP,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ultima_consulta TIMESTAMP
        )
    ''')
    
    # Tabla de comercios
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS comercios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_comercial TEXT NOT NULL,
            cadena TEXT NOT NULL,
            provincia TEXT NOT NULL,
            localidad TEXT NOT NULL,
            direccion TEXT NOT NULL,
            telefono TEXT,
            latitud REAL,
            longitud REAL,
            activo BOOLEAN DEFAULT 1,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabla de productos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            descripcion TEXT,
            categoria TEXT NOT NULL,
            subcategoria TEXT,
            unidad_medida TEXT,
            marca_referencia TEXT,
            precio_referencia_min REAL,
            precio_referencia_max REAL,
            activo BOOLEAN DEFAULT 1,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabla de precios
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS precios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER NOT NULL,
            comercio_id INTEGER NOT NULL,
            precio REAL NOT NULL,
            precio_oferta REAL,
            en_oferta BOOLEAN DEFAULT 0,
            stock_disponible BOOLEAN DEFAULT 1,
            fecha_relevamiento DATE NOT NULL,
            fecha_vencimiento DATE,
            fuente TEXT,
            verificado_por_usuario BOOLEAN DEFAULT 0,
            FOREIGN KEY (producto_id) REFERENCES productos(id),
            FOREIGN KEY (comercio_id) REFERENCES comercios(id)
        )
    ''')
    
    # Tabla de consultas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS consultas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            productos TEXT,
            total_mas_barato REAL,
            comercio_mas_barato TEXT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        )
    ''')
    
    # Índices
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_comercios_cadena ON comercios(cadena)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_comercios_provincia ON comercios(provincia)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_comercios_localidad ON comercios(localidad)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_productos_categoria ON productos(categoria)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_precios_producto ON precios(producto_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_precios_comercio ON precios(comercio_id)')
    
    conn.commit()
    conn.close()
    
    return DATABASE_PATH

def verificar_limite_consultas(usuario_id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT consultas_usadas, consultas_gratis, subscription_activa, 
               subscription_expira, ultima_consulta
        FROM usuarios WHERE id = ?
    ''', (usuario_id,))
    
    usuario = cursor.fetchone()
    conn.close()
    
    if not usuario:
        return False, "Usuario no encontrado"
    
    if usuario['subscription_activa']:
        if usuario['subscription_expira']:
            if datetime.now() > datetime.fromisoformat(usuario['subscription_expira']):
                return False, "Suscripción expirada"
        return True, "OK"
    
    consultas_disponibles = usuario['consultas_gratis'] - usuario['consultas_usadas']
    
    if consultas_disponibles <= 0:
        return False, "Límite de consultas alcanzado. Suscríbete para continuar."
    
    return True, f"Consultas disponibles: {consultas_disponibles}"

def incrementar_consulta(usuario_id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE usuarios 
        SET consultas_usadas = consultas_usadas + 1,
            ultima_consulta = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (usuario_id,))
    
    conn.commit()
    conn.close()

def registrar_usuario(email, password, nombre, telefono, es_anonimo=True):
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO usuarios (email, password, nombre, telefono, es_anonimo)
            VALUES (?, ?, ?, ?, ?)
        ''', (email, password, nombre, telefono, es_anonimo))
        
        conn.commit()
        usuario_id = cursor.lastrowid
        conn.close()
        
        return True, usuario_id
    except sqlite3.IntegrityError:
        conn.close()
        return False, "Email ya registrado"

def activar_suscripcion(usuario_id, dias=30):
    from datetime import timedelta
    conn = get_db()
    cursor = conn.cursor()
    
    expiration = datetime.now() + timedelta(days=dias)
    
    cursor.execute('''
        UPDATE usuarios 
        SET subscription_activa = 1,
            subscription_expira = ?,
            consultas_usadas = 0
        WHERE id = ?
    ''', (expiration.isoformat(), usuario_id))
    
    conn.commit()
    conn.close()
    
    return True

if __name__ == '__main__':
    db_path = init_database()
    print(f"✅ Base de datos creada: {db_path}")
