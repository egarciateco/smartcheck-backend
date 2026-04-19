"""
🧪 SmartCheck API - Test Suite
Ejecutá: python test_api.py
"""

import httpx
import sys

BASE_URL = "https://smartcheck-api.onrender.com"

def test_health():
    """Test endpoint de health"""
    response = httpx.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    assert "status" in response.json()
    print("✅ /health - OK")

def test_provincias():
    """Test endpoint de provincias"""
    response = httpx.get(f"{BASE_URL}/api/v1/locations/provincias")
    assert response.status_code == 200
    assert "provincias" in response.json()
    print("✅ /api/v1/locations/provincias - OK")

def test_localidades():
    """Test endpoint de localidades"""
    response = httpx.get(
        f"{BASE_URL}/api/v1/locations/localidades",
        params={"provincia": "Buenos Aires"}
    )
    assert response.status_code == 200
    assert "localidades" in response.json()
    print("✅ /api/v1/locations/localidades - OK")

def test_categorias():
    """Test endpoint de categorías"""
    response = httpx.get(f"{BASE_URL}/api/v1/categorias")
    assert response.status_code == 200
    assert "categorias" in response.json()
    print("✅ /api/v1/categorias - OK")

def test_compare():
    """Test endpoint de comparación de precios"""
    response = httpx.get(
        f"{BASE_URL}/api/v1/compare",
        params={
            "products": "leche",
            "provincia": "Buenos Aires",
            "localidad": "La Plata",
            "categoria": "Supermercados"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "all_stores" in data
    assert "cheapest" in data
    print("✅ /api/v1/compare - OK")
    print(f"   🏪 Comercio más barato: {data['cheapest']['name']} (${data['cheapest']['total']})")

def run_all_tests():
    """Ejecutar todos los tests"""
    print("🧪 Iniciando tests de SmartCheck API...\n")
    
    try:
        test_health()
        test_provincias()
        test_localidades()
        test_categorias()
        test_compare()
        
        print("\n🎉 Todos los tests pasaron exitosamente!")
        return 0
    except AssertionError as e:
        print(f"\n❌ Test fallido: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(run_all_tests())
