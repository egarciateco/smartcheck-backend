import json
import os
from typing import List, Dict

def normalizar_cadena(nombre: str) -> str:
    nombre_upper = nombre.upper()
    
    cadenas = {
        'CARREFOUR': 'Carrefour',
        'COTO': 'Coto',
        'JUMBO': 'Jumbo',
        'VEA': 'Vea',
        'DISCO': 'Disco',
        'DIA': 'Día',
        'CHANGOMAS': 'Changomas',
        'LA ANONIMA': 'La Anónima',
        'WALMART': 'Walmart',
        'MAKRO': 'Makro',
        'SUPERMERCADOS CORDIEZ': 'Cordiez',
        'EL TUNEL': 'El Túnel',
        'MICROPACK': 'Micropack',
        'MICRO GO': 'Micro Go',
        'BLOW MAX': 'Blow Max',
        'SUPER A': 'Super A',
        'KILBEL': 'Kilbel',
        'CALCHAQUI': 'Calchaquí',
        'DELFIN': 'Delfín',
        'CAPO': 'Capo',
        'SAN RAMON': 'San Ramón',
        'ARCOIRIS': 'Arcoíris',
        'LA ROTONDA': 'La Rotonda',
        'SUPER NATALY': 'Nataly',
        'SAN JOSE': 'San José',
        'AMERICA': 'América',
        'CABRAL': 'Cabral',
        'ALVEAR': 'Alvear',
        'TOP': 'Top',
        'SUPERMAMI': 'Supermami',
        'TADICOR': 'Tadicor',
        'SUPERCOOP': 'Supercoop',
        'COOPERATIVA OBRERA': 'Cooperativa Obrera',
        'LA GALLEGA': 'La Gallega',
        'LA REINA': 'La Reina',
        'CALIFORNIA': 'California',
        'DAMESCO': 'Damesco',
        'EL MILAGRO': 'El Milagro',
        'OSCAR DAVID': 'Oscar David',
        'MARIANO MAX': 'Mariano Max',
        'MULTIPACK': 'Multipack',
        'TODO': 'Todo',
        'YAGUAR': 'Yaguar',
        'SUPERMERCADOS TODO': 'Todo',
        'APA SUPERMERCADOS': 'APA',
        'CUCHERMERCADOS': 'Cuchermércados',
        'DOBRO SUPERMERCADOS': 'Dobro',
        'CASA BERCHIA': 'Casa Berchia',
    }
    
    for clave, valor in cadenas.items():
        if clave in nombre_upper:
            return valor
    
    return 'Independiente'

def cargar_desde_txt(archivo_txt: str) -> List[Dict]:
    comercios = []
    id_counter = 1
    
    try:
        with open(archivo_txt, 'r', encoding='utf-8') as f:
            lineas = f.readlines()
            
        for i, linea in enumerate(lineas):
            if i == 0:
                continue
            
            linea = linea.strip()
            if not linea:
                continue
            
            partes = linea.split('\t')
            
            if len(partes) < 4:
                partes = linea.split()
            
            if len(partes) >= 4:
                provincia = partes[0].strip() if len(partes) > 0 else ''
                localidad = partes[1].strip() if len(partes) > 1 else ''
                domicilio = ' '.join(partes[2:-1]).strip() if len(partes) > 2 else ''
                nombre = partes[-1].strip() if len(partes) > 0 else ''
                
                if provincia and localidad and nombre:
                    cadena = normalizar_cadena(nombre)
                    
                    comercio = {
                        "id": f"{cadena.lower().replace(' ', '_')}_{id_counter:04d}",
                        "nombre": nombre,
                        "cadena": cadena,
                        "direccion": domicilio,
                        "localidad": localidad,
                        "provincia": provincia,
                        "codigo_postal": "",
                        "telefono": "",
                        "email": "",
                        "horario": "",
                        "latitud": None,
                        "longitud": None,
                        "activo": True
                    }
                    
                    comercios.append(comercio)
                    id_counter += 1
                    
    except FileNotFoundError:
        print(f"❌ Archivo no encontrado: {archivo_txt}")
    except Exception as e:
        print(f"❌ Error procesando {archivo_txt}: {e}")
    
    return comercios

def organizar_por_cadena(comercios: List[Dict]) -> Dict:
    resultado = {
        "metadata": {
            "fecha_actualizacion": "2026-04-19",
            "total_cadenas": 0,
            "total_locales": len(comercios),
            "fuente": "FAECYS + Bases comerciales Argentina"
        },
        "cadenas": {}
    }
    
    cadenas_dict = {}
    
    for comercio in comercios:
        cadena = comercio["cadena"]
        
        if cadena not in cadenas_dict:
            cadenas_dict[cadena] = {
                "nombre_comercial": cadena,
                "tipo": "Supermercado",
                "sitio_web": "",
                "logo_url": "",
                "locales": []
            }
        
        cadenas_dict[cadena]["locales"].append(comercio)
    
    resultado["cadenas"] = cadenas_dict
    resultado["metadata"]["total_cadenas"] = len(cadenas_dict)
    
    return resultado

def main():
    print("🔄 Iniciando carga de comercios...")
    
    archivos = [
        'datos_raw/lista1.txt',
        'datos_raw/lista2.txt'
    ]
    
    todos_los_comercios = []
    
    for archivo in archivos:
        ruta_completa = os.path.join(os.path.dirname(__file__), '..', archivo)
        if os.path.exists(ruta_completa):
            print(f"📄 Cargando {archivo}...")
            comercios = cargar_desde_txt(ruta_completa)
            todos_los_comercios.extend(comercios)
            print(f"   ✅ {len(comercios)} comercios cargados")
        else:
            print(f"   ⚠️  Archivo {archivo} no encontrado")
    
    resultado = organizar_por_cadena(todos_los_comercios)
    
    ruta_salida = os.path.join(os.path.dirname(__file__), 'comercios.json')
    with open(ruta_salida, 'w', encoding='utf-8') as f:
        json.dump(resultado, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Total: {resultado['metadata']['total_locales']} comercios")
    print(f"✅ Cadenas: {resultado['metadata']['total_cadenas']}")
    print(f"✅ Archivo guardado: {ruta_salida}")

if __name__ == '__main__':
    main()
