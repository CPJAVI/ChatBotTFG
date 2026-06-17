# api_keys.py
# Configuración de APIs para el análisis de riesgos

# ============================================
# PROVEEDORES DISPONIBLES
# ==========================================
PROVEEDORES = {
    "mistral": {
        "nombre": "Mistral AI",
        "url": "https://api.mistral.ai/v1/chat/completions",
        "modelo": "mistral-small-latest"
    },
    "gemini": {
        "nombre": "Google Gemini",
        "url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
        "modelo": "gemini-1.5-flash"
    },
    "groq": {
        "nombre": "Groq",
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "modelo": "llama3-70b-8192"  # o "mixtral-8x7b-32768" / "gemma2-9b-it"
    }
}

# ============================================
# CLAVES API (completa con tus claves)
# ==========================================
MISTRAL_API_KEY = "TmHUYmLWgJ5Goj773GOi36DLHnITqoIH"
GEMINI_API_KEY = "AIzaSyDgeDoh3zNSLKagnJ9M5FB0dIkd73nIvjM"
GROQ_API_KEY = "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"

# ============================================
# PROVEEDOR ACTIVO (cambia aquí para elegir)
# ==========================================
# Opciones: "mistral", "gemini", "groq"
PROVEEDOR_ACTIVO = "mistral"  # <--- CAMBIA ESTO PARA USAR OTRA API

# ============================================
# FUNCIONES DE UTILIDAD
# ==========================================
def get_proveedor():
    """Devuelve la configuración del proveedor activo"""
    return PROVEEDORES.get(PROVEEDOR_ACTIVO, PROVEEDORES["mistral"])

def get_api_key():
    """Devuelve la clave API del proveedor activo"""
    claves = {
        "mistral": MISTRAL_API_KEY,
        "gemini": GEMINI_API_KEY,
        "groq": GROQ_API_KEY
    }
    return claves.get(PROVEEDOR_ACTIVO, "")

def get_headers():
    """Devuelve los headers necesarios para cada API"""
    if PROVEEDOR_ACTIVO == "mistral":
        return {"Authorization": f"Bearer {MISTRAL_API_KEY}", "Content-Type": "application/json"}
    elif PROVEEDOR_ACTIVO == "groq":
        return {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    elif PROVEEDOR_ACTIVO == "gemini":
        return {"Content-Type": "application/json"}
    return {}

def get_url():
    """Devuelve la URL completa de la API (con API key si es Gemini)"""
    if PROVEEDOR_ACTIVO == "gemini":
        return f"{PROVEEDORES['gemini']['url']}?key={GEMINI_API_KEY}"
    return PROVEEDORES[PROVEEDOR_ACTIVO]["url"]

def get_modelo():
    """Devuelve el nombre del modelo a usar"""
    return PROVEEDORES[PROVEEDOR_ACTIVO]["modelo"]

def listar_proveedores():
    """Muestra los proveedores disponibles"""
    print("\n📡 PROVEEDORES DISPONIBLES:")
    for key, value in PROVEEDORES.items():
        print(f"   - {key}: {value['nombre']} (modelo: {value['modelo']})")
    print(f"\n✅ ACTIVO: {PROVEEDOR_ACTIVO} - {PROVEEDORES[PROVEEDOR_ACTIVO]['nombre']}")