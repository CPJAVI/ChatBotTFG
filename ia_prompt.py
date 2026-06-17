# ia_prompt.py - Prompt de IA y comunicación con Mistral
# CON FÓRMULAS CORRECTAS DE MAGERIT
# ia_prompt.py - Versión mejorada con extracción universal de datos
# Conserva toda la funcionalidad original y añade detección inteligente de activos/amenazas/salvaguardas

import os
import re
import json
import requests
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from io import StringIO
import pdfplumber
from docx import Document
from bs4 import BeautifulSoup

import api_keys
from rag import GestorRAG

# ============================================================
# Inicialización del RAG (sin cambios)
# ============================================================
gestor_rag = GestorRAG()
if len(gestor_rag.textos) == 0:
    gestor_rag.cargar_libros()

 
 


def obtener_contexto_magerit(pregunta: str) -> str:
    """Obtiene contexto del RAG para fórmulas"""
    contexto = ""
    general = gestor_rag.buscar(pregunta, libro_filtro="LIBRO_III")
    if general:
        contexto += "\n=== CONTEXTO GENERAL LIBRO III ===\n"
        for g in general[:5]:
            contexto += f"\n--- {g['fuente']} (pág. {g['pagina']}) ---\n{g['texto'][:500]}\n"
    return contexto if contexto else "No se encontraron fragmentos en los libros de MAGERIT."
def safe_str(value: Any, default: str = "?") -> str:
    """Convierte cualquier valor a string de forma segura"""
    if value is None:
        return default
    if isinstance(value, (list, tuple, dict)):
        return default
    try:
        return str(value)
    except:
        return default

 
def obtener_catalogo_amenazas(limit: int = 100) -> str:
    """Obtiene catálogo de amenazas del RAG (formato texto)"""
    catalogo = ""
    for idx in gestor_rag.indices_amenazas[:limit]:
        item = gestor_rag.textos[idx]
        cod = item.get("codigo", "")
        nom = item.get("nombre", "")
        tipos = item.get("tipos_activos", [])
        dimensiones = item.get("dimensiones", [])
        
        if cod and nom:
            catalogo += f"- {cod}: {nom}\n"
            if tipos:
                catalogo += f"  Tipos de activos: {', '.join(tipos)}\n"
            if dimensiones:
                catalogo += f"  Dimensiones: {', '.join(dimensiones)}\n"
    if not catalogo:
        resultados = gestor_rag.buscar_amenazas("")
        for r in resultados[:limit]:
            cod = r.get('codigo', '')
            nom = r.get('nombre', '')
            tipos = r.get('tipos_activos', [])
            dimensiones = r.get('dimensiones', [])
            if cod and nom:
                catalogo += f"- {cod}: {nom}\n"
                if tipos:
                    catalogo += f"  Tipos de activos: {', '.join(tipos)}\n"
                if dimensiones:
                    catalogo += f"  Dimensiones: {', '.join(dimensiones)}\n"
    return catalogo
def obtener_catalogo_salvaguardas(limit: int = 100) -> str:
    """Obtiene catálogo de salvaguardas del RAG (formato texto)"""
    catalogo = ""
    for idx in gestor_rag.indices_salvaguardas[:limit]:
        item = gestor_rag.textos[idx]
        cod = item.get("codigo", "")
        nom = item.get("nombre", "")
        if cod and nom:
            catalogo += f"- {cod}: {nom}\n"
    if not catalogo:
        resultados = gestor_rag.buscar_salvaguardas("")
        for r in resultados[:limit]:
            catalogo += f"- {r.get('codigo', '')}: {r.get('nombre', '')}\n"
    return catalogo

def obtener_amenazas_del_rag(pregunta: str) -> List[Dict]:
    """Obtiene amenazas del catálogo RAG (estructurado)"""
    resultados = gestor_rag.buscar_amenazas(pregunta)
    amenazas = []
    for r in resultados:
        amenazas.append({
            'codigo': r.get('codigo', ''),
            'nombre': r.get('nombre', ''),
            'tipos_activos': r.get('tipos_activos', []),
            'dimensiones': r.get('dimensiones', []),
            'descripcion': r.get('descripcion', '')
        })
    return amenazas

def obtener_salvaguardas_del_rag(pregunta: str) -> List[Dict]:
    """Obtiene salvaguardas del catálogo RAG (estructurado)"""
    resultados = gestor_rag.buscar_salvaguardas(pregunta)
    salvaguardas = []
    for r in resultados:
        salvaguardas.append({
            'codigo': r.get('codigo', ''),
            'nombre': r.get('nombre', ''),
            'texto_completo': r.get('texto', '')
        })
    return salvaguardas

TIPOS_ACTIVOS_MAGERIT = {
    "[D]": "Datos / Información",
    "[K]": "Claves criptográficas",
    "[S]": "Servicios",
    "[SW]": "Software - Aplicaciones informáticas",
    "[HW]": "Equipamiento informático (hardware)",
    "[COM]": "Redes de comunicaciones",
    "[Media]": "Soportes de información",
    "[AUX]": "Equipamiento auxiliar",
    "[L]": "Instalaciones",
    "[P]": "Personal"
}
def clasificar_activo_por_tipo(nombre_activo: str) -> str:
    """Clasifica un activo según su nombre en los tipos Magerit"""
    if not nombre_activo:
        return "[HW]"
    
    # Normalizar: minúsculas, eliminar acentos, eliminar caracteres especiales
    nombre_lower = nombre_activo.lower()
    
    # Eliminar acentos (áéíóúü -> aeiou)
    import unicodedata
    nombre_lower = ''.join(
        c for c in unicodedata.normalize('NFD', nombre_lower)
        if unicodedata.category(c) != 'Mn'
    )
    
    # Eliminar caracteres no alfabéticos (excepto espacios)
    import re
    nombre_lower = re.sub(r'[^a-z\s]', '', nombre_lower)
    
    # ============================================================
    # 1. CLAVES CRIPTOGRÁFICAS [K] - PRIORIDAD MÁXIMA
    # ============================================================
    if any(p in nombre_lower for p in [
        'clave', 'certificado', 'cifrado', 'criptografico', 'token', 'contraseña', 'contrasena',
        'codigo de acceso', 'codigodeacceso', 'password', 'pin', 'otp', 'seudonimo', 'alias',
        'clave privada', 'claveprivada', 'clave publica', 'clavepublica', 'certificado digital',
        'certificadodigital', 'firma electronica', 'firmaelectronica', 'token de acceso',
        'tokendeacceso', 'token de autenticacion', 'tokendeautenticacion'
    ]):
        return "[K]"
    
    # ============================================================
    # 2. SOFTWARE / APLICACIONES [SW]
    # ============================================================
    elif any(p in nombre_lower for p in [
        'aplicacion', 'app', 'software', 'sistema operativo', 'sistemaoperativo', 'windows',
        'linux', 'macos', 'android', 'ios', 'firmware', 'middleware', 'web service', 'webservice',
        'gestor bd', 'gestorbd', 'mysql', 'postgresql', 'oracle', 'sql server', 'sqlserver',
        'servidor correo', 'servidorcorreo', 'exchange', 'outlook', 'navegador', 'chrome',
        'firefox', 'edge', 'safari', 'ofimatica', 'office', 'word', 'excel', 'powerpoint',
        'erp', 'crm', 'antivirus', 'edr', 'virtualizacion', 'vmware', 'docker', 'contenedor', 'api'
    ]):
        return "[SW]"
    
    # ============================================================
    # 3. HARDWARE [HW]
    # ============================================================
    elif any(p in nombre_lower for p in [
        'servidor', 'ordenador', 'pc', 'portatil', 'portatil', 'hardware', 'equipo', 'router',
        'switch', 'disco', 'cpu', 'central', 'workstation', 'estacion trabajo', 'estaciontrabajo',
        'cliente ligero', 'clienteligero', 'thin client', 'thinclient', 'impresora', 'scanner',
        'fotocopiadora', 'fax', 'monitor', 'pantalla', 'teclado', 'raton', 'periferico',
        'almacenamiento', 'nas', 'rack', 'blade', 'mainframe', 'miniordenador', 'tablet', 'movil',
        'movil', 'telefono', 'smartphone', 'laptop', 'desktop', 'memoria ram', 'memoriaram',
        'placa base', 'placabase'
    ]):
        return "[HW]"
    
    # ============================================================
    # 4. DATOS / INFORMACIÓN [D]
    # ============================================================
    elif any(p in nombre_lower for p in [
        'base de datos', 'basesdedatos', 'bases de datos', 'datos', 'informacion', 'archivo',
        'fichero', 'registro', 'log', 'documento', 'expediente', 'historial', 'informe', 'reporte',
        'estadistica', 'indicador', 'correo', 'email', 'mensaje', 'contenido', 'publicacion',
        'pagina web', 'paginaw eb', 'imagen', 'video', 'audio', 'multimedia', 'backup',
        'copia de seguridad', 'copiadeseguridad', 'configuracion', 'parametro', 'licencia',
        'contrato', 'factura', 'pedido', 'nomina', 'datos personales', 'datospersonales',
        'datos sensibles', 'datossensibles'
    ]):
        return "[D]"
    
    # ============================================================
    # 5. REDES DE COMUNICACIONES [COM]
    # ============================================================
    elif any(p in nombre_lower for p in [
        'red', 'comunicacion', 'wifi', 'internet', 'fibra', 'lan', 'wan', 'wireless', 'vlan',
        'vpn', 'hub', 'bridge', 'access point', 'accesspoint', 'gateway', 'firewall', 'proxy',
        'dns', 'dhcp', 'enlace', 'circuito', 'banda ancha', 'bandaancha', 'adsl', 'fibra optica',
        'fibraoptica', 'cable red', 'cablered', 'ethernet', 'mpls'
    ]):
        return "[COM]"
    
    # ============================================================
    # 6. SOPORTES DE INFORMACIÓN [Media]
    # ============================================================
    elif any(p in nombre_lower for p in [
        'soporte', 'disco duro', 'discoduro', 'usb', 'pendrive', 'cd', 'dvd', 'cinta magnetica',
        'cintamagnetica', 'blu-ray', 'bluray', 'disquete', 'tarjeta memoria', 'tarjetamemoria',
        'ssd', 'disco externo', 'discoexterno', 'san'
    ]):
        return "[Media]"
    
    # ============================================================
    # 7. EQUIPAMIENTO AUXILIAR [AUX]
    # ============================================================
    elif any(p in nombre_lower for p in [
        'climatizacion', 'aire acondicionado', 'aireacondicionado', 'calefaccion', 'ventilacion',
        'electricidad', 'sae', 'ups', 'sai', 'generador', 'bateria', 'extintor', 'detector humos',
        'detectorhumos', 'alarma incendios', 'alarmaincendios', 'iluminacion', 'ascensor',
        'montacargas', 'camara', 'puerta blindada', 'puertablindada', 'grupo electrogeno',
        'grupoelectrogeno', 'fuente alimentacion', 'fuentealimentacion', 'regulador tension',
        'reguladortension', 'pdu'
    ]):
        return "[AUX]"
    
    # ============================================================
    # 8. INSTALACIONES [L]
    # ============================================================
    elif any(p in nombre_lower for p in [
        'sala', 'edificio', 'oficina central', 'oficinacentral', 'sede central', 'sedecentral',
        'oficina', 'instalacion', 'local', 'sede', 'planta', 'almacen', 'campus', 'aula',
        'laboratorio', 'despacho', 'vestuario', 'cafeteria', 'biblioteca', 'centro de datos',
        'centroredatos', 'cpd', 'data center', 'datacenter', 'nave', 'taller', 'garaje',
        'aparcamiento', 'parking', 'recepcion', 'hall'
    ]):
        return "[L]"
    
    # ============================================================
    # 9. PERSONAL [P]
    # ============================================================
    elif any(p in nombre_lower for p in [
        'personal', 'usuario', 'operador', 'administrador', 'empleado', 'persona', 'supervisor',
        'director', 'gerente', 'analista', 'tecnico', 'ingeniero', 'becario', 'contratista',
        'visitante', 'vigilante', 'limpiador', 'responsable', 'coordinador', 'jefe',
        'subdirector', 'rector', 'profesor', 'alumno', 'estudiante', 'pas', 'pdi'
    ]):
        return "[P]"
    
    # ============================================================
    # 10. POR DEFECTO: HARDWARE
    # ============================================================
    return "[HW]"
    
def obtener_valoracion_ens(nombre_activo: str, descripcion: str = "") -> Dict[str, int]:
    """Consulta el RAG para obtener valoración de dimensiones (1..5) o devuelve 2 por defecto"""
    consulta = f"{nombre_activo} {descripcion} confidencialidad integridad disponibilidad autenticidad trazabilidad"
    resultados = gestor_rag.buscar_ens(consulta)
    if not resultados:
        resultados = gestor_rag.buscar_guia_ens(consulta)
    
    valoracion = {'confidencialidad': '?', 'integridad': '?', 'disponibilidad': '?', 'autenticidad': '?', 'trazabilidad': '?'}
    if not resultados:
        return valoracion
    
    mapa_niveles = {
        BAJO: ['bajo', 'limitado', 'pequeño', 'menor', 'poco', 'leve', 'mínimo','muy bajo', 'despreciable', 'inexistente', 'nulo', 'insignificante', 'nada', '0'],
        MEDIO: ['medio', 'moderado', 'normal', 'aceptable', 'estándar', 'regular', 'suficiente'],
        ALTO: ['alto', 'grande', 'significativo', 'importante', 'elevado', 'considerable', 'grave','muy alto', 'crítico', 'extremo', 'inaceptable', 'catastrófico', 'máximo', 'total', 'absoluto', 'devastador']
    }
    for r in resultados[:10]:
        texto = r.get('texto', '').lower()
        for dim in valoracion.keys():
            if dim in texto:
                for nivel, palabras in mapa_niveles.items():
                    if any(palabra in texto for palabra in palabras):
                        valoracion[dim] = nivel
                        break
    return valoracion

# ============================================================
# NUEVA FUNCIÓN: EXTRACCIÓN UNIVERSAL DE DATOS DE ARCHIVOS
# ============================================================
def extraer_texto_archivo_original(ruta: str) -> str:
    """Función original que extrae texto plano de cualquier archivo (se mantiene)"""
    ext = os.path.splitext(ruta)[1].lower()
    texto = ""
    try:
        if ext in ['.xlsx', '.xls']:
            dfs = pd.read_excel(ruta, sheet_name=None)
            for hoja, df in dfs.items():
                texto += f"\n--- Hoja: {hoja} ---\n{df.to_csv(index=False)}\n"
        elif ext == '.csv':
            df = pd.read_csv(ruta, encoding='utf-8', skipinitialspace=True)
            texto += df.to_csv(index=False)
        elif ext == '.pdf':
            with pdfplumber.open(ruta) as pdf:
                for pagina in pdf.pages:
                    t = pagina.extract_text()
                    if t:
                        texto += t + "\n"
        elif ext == '.docx':
            doc = Document(ruta)
            texto += "\n".join(p.text for p in doc.paragraphs)
        elif ext in ['.txt', '.md', '.log']:
            with open(ruta, 'r', encoding='utf-8', errors='ignore') as f:
                texto += f.read()
        elif ext in ['.html', '.htm', '.xml']:
            with open(ruta, 'r', encoding='utf-8', errors='ignore') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
                for script in soup(["script", "style"]):
                    script.decompose()
                texto += soup.get_text(separator='\n', strip=True)
        else:
            with open(ruta, 'r', encoding='utf-8', errors='ignore') as f:
                texto += f.read()
    except Exception as e:
        print(f"[extraer_texto] Error en {ruta}: {e}")
    return texto

def extraer_datos_de_archivo(ruta: str) -> Dict[str, List]:
    """
    Extrae activos, amenazas, salvaguardas y dependencias de CUALQUIER archivo
    sin asumir una estructura fija. Busca patrones y tablas.
    """
    resultado = {
        'activos': [],
        'amenazas': [],
        'salvaguardas': [],
        'dependencias': []
    }
    
    # 1. Obtener texto plano
    texto = extraer_texto_archivo_original(ruta)
    if not texto:
        return resultado
    
    # 2. Intentar leer como DataFrame si es Excel/CSV (para detección de columnas)
    dfs = []
    ext = os.path.splitext(ruta)[1].lower()
    if ext in ['.xlsx', '.xls']:
        try:
            xls = pd.ExcelFile(ruta)
            for sheet in xls.sheet_names:
                df = pd.read_excel(ruta, sheet_name=sheet, header=None)
                dfs.append(df)
        except:
            pass
    elif ext == '.csv':
        try:
            df = pd.read_csv(ruta, encoding='utf-8', header=None, skipinitialspace=True)
            dfs.append(df)
        except:
            pass
    
    # 3. Buscar tablas markdown (con pipes |) en el texto
    lineas = texto.split('\n')
    tablas_markdown = []
    i = 0
    while i < len(lineas):
        if '|' in lineas[i] and not lineas[i].strip().startswith('---'):
            # Inicio de posible tabla
            filas_tabla = []
            while i < len(lineas) and '|' in lineas[i]:
                fila = lineas[i].strip()
                if fila and not re.match(r'^[\s\-:|]+$', fila):  # no es línea de separación
                    celdas = [c.strip() for c in fila.split('|') if c.strip()]
                    if celdas:
                        filas_tabla.append(celdas)
                i += 1
            if len(filas_tabla) >= 2:
                # Asumimos primera fila como cabecera
                cabecera = filas_tabla[0]
                datos = []
                for fila in filas_tabla[1:]:
                    if len(fila) == len(cabecera):
                        datos.append({cabecera[j]: fila[j] for j in range(len(cabecera))})
                if datos:
                    tablas_markdown.append(datos)
            continue
        i += 1
    
    # 4. Función auxiliar para normalizar texto (minúsculas, sin acentos)
    def normalize(s: str) -> str:
        import unicodedata
        s = s.lower()
        s = unicodedata.normalize('NFKD', s).encode('ASCII', 'ignore').decode('utf-8')
        return s
    
    # 5. Detectar activos en tablas markdown o dataframes
    activos_encontrados = []
    # Buscar en tablas markdown
    for tabla in tablas_markdown:
        # Identificar columnas que parecen activos
        col_nombre = None
        col_valor = None
        col_depende = None
        col_grado = None
        col_tipo = None
        for col in tabla[0].keys():
            norm = normalize(col)
            if 'activo' in norm or 'nombre' in norm or 'recurso' in norm or 'activo' in norm:
                col_nombre = col
            if 'valor' in norm or 'euro' in norm or '€' in norm or 'econ' in norm:
                col_valor = col
            if 'depend' in norm:
                col_depende = col
            if 'grado' in norm:
                col_grado = col
            if 'tipo' in norm or 'clase' in norm:
                col_tipo = col
        if col_nombre:
            for row in tabla:
                nombre = row.get(col_nombre, '').strip()
                if not nombre:
                    continue
                valor = None
                if col_valor and row.get(col_valor):
                    val_str = str(row[col_valor]).replace('€', '').replace(',', '').strip()
                    nums = re.findall(r'\d+(?:\.\d+)?', val_str)
                    if nums:
                        valor = float(nums[0])
                depende = []
                if col_depende and row.get(col_depende):
                    dep_str = str(row[col_depende])
                    # Buscar IDs como ACT1, act2, "Software", etc.
                    ids = re.findall(r'[A-Za-z0-9_]+\.?[A-Za-z0-9_]*', dep_str)
                    depende = [d for d in ids if d and len(d) > 1]
                grado = 1.0
                if col_grado and row.get(col_grado):
                    grado_str = str(row[col_grado]).replace(',', '.').strip()
                    try:
                        grado = float(grado_str)
                    except:
                        if '%' in grado_str:
                            grado = float(grado_str.replace('%', '')) / 100.0
                tipo = row.get(col_tipo, '') if col_tipo else ''
                activos_encontrados.append({
                    'nombre': nombre,
                    'valor': valor,
                    'depende_de': depende,
                    'grado': grado,
                    'tipo': tipo
                })
    
    # También buscar activos en dataframes de Excel/CSV (estructura más libre)
    for df in dfs:
        # Convertir a texto y buscar filas que parezcan contener un activo
        for idx, row in df.iterrows():
            row_text = ' '.join([str(c) for c in row.values if pd.notna(c)])
            # Si la fila contiene palabras clave de activo y un número que puede ser valor
            if any(k in normalize(row_text) for k in ['activo', 'base de datos', 'servidor', 'software', 'ordenador', 'red', 'sede', 'director']):
                # Intentar extraer nombre (primera celda no vacía)
                nombre = None
                for cell in row.values:
                    if pd.notna(cell) and isinstance(cell, str) and len(cell) > 2:
                        nombre = cell
                        break
                if nombre and not any(a['nombre'] == nombre for a in activos_encontrados):
                    valor = None
                    # buscar número que parezca valor económico
                    nums = re.findall(r'\b\d{4,}\b', row_text)
                    if nums:
                        valor = float(nums[0])
                    activos_encontrados.append({
                        'nombre': nombre,
                        'valor': valor,
                        'depende_de': [],
                        'grado': 1.0,
                        'tipo': ''
                    })
    
    # 6. Detectar amenazas en tablas markdown
    amenazas_encontradas = []
    for tabla in tablas_markdown:
        col_codigo = None
        col_nombre = None
        col_frec = None
        col_degr = None
        col_afecta = None
        for col in tabla[0].keys():
            norm = normalize(col)
            if 'codigo' in norm or 'código' in norm:
                col_codigo = col
            if 'amenaza' in norm or 'nombre' in norm:
                col_nombre = col
            if 'frecuencia' in norm:
                col_frec = col
            if 'degrad' in norm:
                col_degr = col
            if 'afecta' in norm or 'activos que afecta' in norm:
                col_afecta = col
        if col_nombre or col_codigo:
            for row in tabla:
                nombre = row.get(col_nombre, '').strip() if col_nombre else ''
                codigo = row.get(col_codigo, '').strip() if col_codigo else ''
                if not nombre and not codigo:
                    continue
                # Extraer frecuencia (puede venir con %)
                freq_str = row.get(col_frec, '') if col_frec else ''
                frecuencia = None
                if freq_str:
                    freq_str = str(freq_str).replace(',', '.').strip()
                    if '%' in freq_str:
                        frecuencia = float(freq_str.replace('%', '')) / 100.0
                    else:
                        try:
                            frecuencia = float(freq_str)
                        except:
                            pass
                degradacion = None
                deg_str = row.get(col_degr, '') if col_degr else ''
                if deg_str:
                    deg_str = str(deg_str).replace(',', '.').strip()
                    if '%' in deg_str:
                        degradacion = float(deg_str.replace('%', '')) / 100.0
                    else:
                        try:
                            degradacion = float(deg_str)
                        except:
                            pass
                afecta = []
                if col_afecta and row.get(col_afecta):
                    afecta = [a.strip() for a in str(row[col_afecta]).split(',')]
                amenazas_encontradas.append({
                    'codigo': codigo,
                    'nombre': nombre,
                    'frecuencia': frecuencia,
                    'degradacion': degradacion,
                    'afecta': afecta
                })
    
    # 7. Detectar salvaguardas en tablas markdown
    salvaguardas_encontradas = []
    for tabla in tablas_markdown:
        col_codigo = None
        col_nombre = None
        col_ef_frec = None
        col_ef_degr = None
        for col in tabla[0].keys():
            norm = normalize(col)
            if 'codigo' in norm:
                col_codigo = col
            if 'salvaguarda' in norm or 'nombre' in norm:
                col_nombre = col
            if 'efectividad frecuencia' in norm or 'efectividad_frec' in norm:
                col_ef_frec = col
            if 'efectividad degradacion' in norm or 'efectividad_degr' in norm:
                col_ef_degr = col
        if col_nombre or col_codigo:
            for row in tabla:
                nombre = row.get(col_nombre, '').strip() if col_nombre else ''
                codigo = row.get(col_codigo, '').strip() if col_codigo else ''
                if not nombre and not codigo:
                    continue
                ef_frec = row.get(col_ef_frec, '').strip() if col_ef_frec else ''
                ef_degr = row.get(col_ef_degr, '').strip() if col_ef_degr else ''
                salvaguardas_encontradas.append({
                    'codigo': codigo,
                    'nombre': nombre,
                    'efectividad_frecuencia': ef_frec,
                    'efectividad_degradacion': ef_degr
                })
    
    # 8. Detectar dependencias (explícitas en tablas o en texto)
    dependencias_encontradas = []
    # De los activos, si tienen depende_de, generar dependencias
    for a in activos_encontrados:
        for dep in a.get('depende_de', []):
            dependencias_encontradas.append({
                'activo_origen': a['nombre'],
                'activo_destino': dep,
                'grado': a.get('grado', 1.0)
            })
    # También buscar en el texto patrones como "X depende de Y con grado Z"
    patron_dependencia = re.compile(r'(\w+(?:\s+\w+)?)\s+depende\s+de\s+(\w+(?:\s+\w+)?)(?:\s+con\s+grado\s+([\d.,]+))?', re.IGNORECASE)
    for match in patron_dependencia.finditer(texto):
        origen = match.group(1).strip()
        destino = match.group(2).strip()
        grado = match.group(3).strip().replace(',', '.') if match.group(3) else '1.0'
        try:
            grado = float(grado)
        except:
            grado = 1.0
        dependencias_encontradas.append({
            'activo_origen': origen,
            'activo_destino': destino,
            'grado': grado
        })
    
    # 9. Asignar tipos a los activos si no tienen
    for a in activos_encontrados:
        if not a['tipo']:
            a['tipo'] = clasificar_activo_por_tipo(a['nombre'])
        # Asegurar que grado es float
        if 'grado' not in a:
            a['grado'] = 1.0
        elif isinstance(a['grado'], str):
            try:
                a['grado'] = float(a['grado'].replace(',', '.'))
            except:
                a['grado'] = 1.0
    
    resultado['activos'] = activos_encontrados
    resultado['amenazas'] = amenazas_encontradas
    resultado['salvaguardas'] = salvaguardas_encontradas
    resultado['dependencias'] = dependencias_encontradas
    
    return resultado

def extraer_contenido_archivos(archivos: List[str]) -> str:
    """Concatena texto plano de todos los archivos (original, se mantiene)"""
    contenido = ""
    for ruta in archivos:
        texto = extraer_texto_archivo_original(ruta)
        if texto:
            contenido += f"\n\n========= {os.path.basename(ruta)} =========\n{texto}\n"
    if not contenido:
        contenido = "No se han proporcionado archivos."
    return contenido
def extraer_de_pregunta(pregunta: str) -> Dict[str, List]:
    """Extrae información estructurada de la pregunta del usuario"""
    info = {'activos': [], 'amenazas': []}
    
    # ============================================================
    # PATRONES MEJORADOS PARA ACTIVOS
    # ============================================================
    
    # Patrón 1: "X tiene un valor de Y" (más específico)
    patron_valor_especifico = re.compile(
        r'([A-Za-záéíóúñÑ\s]+?)\s+(?:tiene un valor de|vale|valor de)\s+(\d+(?:\.\d+)?)\s*(?:€|euros)?',
        re.IGNORECASE
    )
    
    # Patrón 2: "los tres primeros activos tienen un valor de X"
    patron_grupo = re.compile(
        r'(?:los|las)\s+(\d+)\s+(?:primeros|primeras|siguientes)\s+(\w+)\s+(?:tienen un valor de|valen)\s+(\d+(?:\.\d+)?)',
        re.IGNORECASE
    )
    
    # Buscar patrones de grupo primero (ej: "los tres primeros activos tienen un valor de 777")
    for match in patron_grupo.finditer(pregunta):
        cantidad = int(match.group(1))
        tipo = match.group(2)  # "activos", "servidores", etc.
        valor = float(match.group(3))
        # Esto es una pista, no podemos crear activos sin nombres
        # Se usará después para asignar valores a activos existentes
    
    # Buscar patrones específicos
    for match in patron_valor_especifico.finditer(pregunta):
        nombre = match.group(1).strip()
        valor = float(match.group(2))
        # Validar que el nombre sea razonable (no frases como "tienen un")
        if len(nombre) > 3 and nombre.lower() not in ['tienen un', 'tiene un', 'los tres', 'las dos']:
            info['activos'].append({'nombre': nombre, 'valor': valor})
    
    # ============================================================
    # PATRONES PARA AMENAZAS
    # ============================================================
    
    # Patrón: "X degrada Y en un Z% y tiene frecuencia W"
    patron_amenaza = re.compile(
        r'([A-Za-záéíóúñÑ\s]+?)\s+(?:degrad[a-z]+|afecta)\s+(?:a\s+)?([A-Za-záéíóúñÑ\s,]+?)\s+(?:en un|en)\s+(\d+(?:\.\d+)?)%?\s*(?:y tiene (?:una )?frecuencia (?:de )?(\d+(?:\.\d+)?)%?)?',
        re.IGNORECASE
    )
    
    for match in patron_amenaza.finditer(pregunta):
        nombre_amenaza = match.group(1).strip()
        activos_afectados = [a.strip() for a in match.group(2).split(',')]
        degradacion = float(match.group(3)) / 100.0 if '%' in match.group(3) else float(match.group(3)) / 100.0
        frecuencia = float(match.group(4)) / 100.0 if match.group(4) and '%' in match.group(4) else (float(match.group(4)) / 100.0 if match.group(4) else None)
        
        if frecuencia is None:
            # Buscar frecuencia en otra parte de la frase
            freq_match = re.search(r'frecuencia\s+(?:de\s+)?(\d+(?:\.\d+)?)%?', pregunta, re.IGNORECASE)
            if freq_match:
                frecuencia = float(freq_match.group(1)) / 100.0 if '%' in freq_match.group(1) else float(freq_match.group(1))
        
        info['amenazas'].append({
            'nombre': nombre_amenaza,
            'frecuencia': frecuencia if frecuencia else 0.5,
            'degradacion': degradacion,
            'afecta': activos_afectados
        })
    
    # Patrón alternativo para amenazas simples
    patron_amenaza_simple = re.compile(
        r'(?:la amenaza de|las amenazas de)\s+([A-Za-záéíóúñÑ\s]+?)\s+(?:degradan|degrada)\s+(?:en un|en)\s+(\d+(?:\.\d+)?)%',
        re.IGNORECASE
    )
    
    for match in patron_amenaza_simple.finditer(pregunta):
        nombre_amenaza = match.group(1).strip()
        degradacion = float(match.group(2)) / 100.0
        
        # Buscar frecuencia asociada
        freq_match = re.search(r'frecuencia\s+(?:de\s+)?(\d+(?:\.\d+)?)%?', pregunta, re.IGNORECASE)
        frecuencia = float(freq_match.group(1)) / 100.0 if freq_match else 0.5
        
        # Buscar activos afectados
        activos_match = re.search(r'degrada\s+(?:a\s+)?([A-Za-záéíóúñÑ\s,]+?)(?:\s+en un|\s+y tiene)', pregunta, re.IGNORECASE)
        activos_afectados = [a.strip() for a in activos_match.group(1).split(',')] if activos_match else []
        
        info['amenazas'].append({
            'nombre': nombre_amenaza,
            'frecuencia': frecuencia,
            'degradacion': degradacion,
            'afecta': activos_afectados
        })
    
    return info

# ============================================================
# FUNCIÓN PRINCIPAL analizar_con_ia  
# ============================================================
def analizar_con_ia(pregunta: str,
                    archivos: List[str] = None,
                    contexto_magerit: str = "") -> str:
    """
    Analiza los riesgos usando MAGERIT. Recibe la pregunta del usuario y una lista de rutas de archivos.
    Devuelve HTML con las tablas y conclusiones.
    """
    # 1. Extraer datos de los archivos (estructurados)
    activos = []
    amenazas = []
    salvaguardas = []
    dependencias = []
    
    if archivos:
        for ruta in archivos:
            datos = extraer_datos_de_archivo(ruta)
            activos.extend(datos.get('activos', []))
            amenazas.extend(datos.get('amenazas', []))
            salvaguardas.extend(datos.get('salvaguardas', []))
            dependencias.extend(datos.get('dependencias', []))
    
    # 2. Extraer información de la pregunta
    info_pregunta = extraer_de_pregunta(pregunta)
    # Fusionar: los datos de la pregunta tienen prioridad (sobrescriben)
    for a_preg in info_pregunta['activos']:
        # Buscar si ya existe un activo con el mismo nombre
        encontrado = False
        for a in activos:
            if a['nombre'].lower() == a_preg['nombre'].lower():
                a['valor'] = a_preg['valor']
                encontrado = True
                break
        if not encontrado:
            activos.append({'nombre': a_preg['nombre'], 'valor': a_preg['valor'], 'depende_de': [], 'grado': 1.0, 'tipo': ''})
    
    for am_preg in info_pregunta['amenazas']:
        encontrado = False
        for am in amenazas:
            if am['nombre'].lower() == am_preg['nombre'].lower():
                if am_preg.get('frecuencia') is not None:
                    am['frecuencia'] = am_preg['frecuencia']
                if am_preg.get('degradacion') is not None:
                    am['degradacion'] = am_preg['degradacion']
                encontrado = True
                break
        if not encontrado:
            amenazas.append({
                'codigo': '',
                'nombre': am_preg['nombre'],
                'frecuencia': am_preg.get('frecuencia'),
                'degradacion': am_preg.get('degradacion'),
                'afecta': []
            })
    
    # 3. Si no hay activos, usar los del RAG o generar algunos típicos (pero se avisa a la IA)
    if not activos:
        # No inventamos aquí, lo dejará la IA pero con instrucción de usar datos reales.
        # Para no dejar vacío, añadimos un marcador
        activos = []  # se mantiene vacío, la IA verá que no hay datos y deberá pedirlos o generarlos realistas.
    
    # 4. Enriquecer activos con tipo y valoración ENS (si no tienen)

    for a in activos:
   
        a['tipo'] = clasificar_activo_por_tipo(a.get('nombre', ''))
        
        if 'valoracion_ens' not in a:
            try:
                a['valoracion_ens'] = obtener_valoracion_ens(a.get('nombre', ''), '')
            except:
                a['valoracion_ens'] = { 'confidencialidad': '?', 'integridad': '?', 'disponibilidad': '?', 'autenticidad': '?', 'trazabilidad': '?'}

 
    # 5. Construir textos para el prompt
    activos_txt = ""
    for i, a in enumerate(activos):
        nombre = safe_str(a.get('nombre', '?'))
        tipo = safe_str(a.get('tipo', '[HW]'))
        valor = safe_str(a.get('valor', '?'))
        depende = ', '.join(a.get('depende_de', []))
        grado = safe_str(a.get('grado', 1.0))
        ens = a.get('valoracion_ens', {})
        activos_txt += f"{nombre} [{tipo}] - Valor: {valor} € - Depende de: {depende} (grado {grado}) - ENS: C={ens.get('confidencialidad',2)} I={ens.get('integridad',2)} D={ens.get('disponibilidad',2)} A={ens.get('autenticidad',2)} T={ens.get('trazabilidad',2)}\n"
    
    amenazas_txt = ""
    for am in amenazas:
        cod = safe_str(am.get('codigo', ''))
        nom = safe_str(am.get('nombre', ''))
        freq = safe_str(am.get('frecuencia', '?'))
        deg = safe_str(am.get('degradacion', '?'))
        afecta = ', '.join(am.get('afecta', []))
        amenazas_txt += f"| {cod} | {nom} | {freq} | {deg} | {afecta} |\n"
    
    salvaguardas_txt = ""
    for s in salvaguardas:
        cod = safe_str(s.get('codigo', ''))
        nom = safe_str(s.get('nombre', ''))
        ef_freq = safe_str(s.get('efectividad_frecuencia', ''))
        ef_deg = safe_str(s.get('efectividad_degradacion', ''))
        salvaguardas_txt += f"| {cod} | {nom} | {ef_freq} | {ef_deg} |\n"
    
    dependencias_txt = ""
    for d in dependencias:
        origen = safe_str(d.get('activo_origen', '?'))
        destino = safe_str(d.get('activo_destino', '?'))
        grado = safe_str(d.get('grado', 1.0))
        dependencias_txt += f"- {origen} depende de {destino} con grado {grado}\n"
    
    # Si no hay dependencias pero sí activos con dependencias declaradas, ya se han incluido.
    
    # 6. Obtener catálogos del RAG (para que la IA solo use códigos válidos)
    catalogo_amenazas_rag = obtener_catalogo_amenazas(100)
    catalogo_salvaguardas_rag = obtener_catalogo_salvaguardas(100)
    

    # 7. Construir prompt final (similar al original pero con datos reales)
    prompt = f"""Eres un experto en análisis de riesgos con MAGERIT 3.

========================================
CATÁLOGO OFICIAL DE AMENAZAS (ÚNICOS CÓDIGOS PERMITIDOS):
========================================
{catalogo_amenazas_rag}

========================================
CATÁLOGO OFICIAL DE SALVAGUARDAS (ÚNICOS CÓDIGOS PERMITIDOS):
========================================
{catalogo_salvaguardas_rag}

========================================
DATOS EXTRAÍDOS DE LOS ARCHIVOS Y DE LA PREGUNTA:
========================================

**ACTIVOS:**
{activos_txt if activos_txt else "No se han encontrado activos en los archivos ni en la pregunta."}

**AMENAZAS:**
{amenazas_txt if amenazas_txt else "No se han encontrado amenazas."}

**SALVAGUARDAS:**
{salvaguardas_txt if salvaguardas_txt else "No se han encontrado salvaguardas."}

**DEPENDENCIAS:**
{dependencias_txt if dependencias_txt else "No se han encontrado dependencias explícitas."}

**TEXTO COMPLETO DE LOS ARCHIVOS (para contexto adicional):**
{extraer_contenido_archivos(archivos) if archivos else "No hay archivos."}

**PREGUNTA DEL USUARIO:**
{pregunta}

========================================
INSTRUCCIONES ESTRICTAS:
========================================
 
1. **ACTIVOS**: Utiliza EXACTAMENTE los activos que aparecen en los datos extraídos (sección "ACTIVOS" más arriba). VALORACION ENS SE MUESTRAN ALTO, MEDIO, BAJO SEGÚN SE CORRESPONDA PARA CADA DIMENSIÓN, NUNCA LOS NÚMEROS
EN GRADO SI UN ACTIVO NO TIENE DEPENDENCIAS DEJA LA COLUMNA VACÍA, SI ESE ACTIVO TIENE DEPENDENCIAS PON UN DECIMAL ENTRE 0 Y 1. GRADO NUNCA DEBE SER UNA PALABRA, DEBE SER UN VALOR NUMÉRICO . SI NO LA COLUMNA DEPENDE DE ESTÁ VACÍA GRADO VACÍO, SI LA COLUMNA DEPENDE DE NO ESTÁ VACÍA, GRADO TENDRÁ VALOR DECIMAL ENTRE 0 Y 1, SEGÚN EL QUE VENGA ESPECIFICADO Y SI NO VIENE NADA ESPECIFICADO PERO HAY DEPENDENCIAS SE LO INGENIA LA IA PARA PONER EL VALOR
   - Si el usuario ha especificado un número concreto (ej. "hay X activos"), respeta ese número. Si X=w+y+z siendo z los activos que vienen en archivos, w los que dice en el prompt el usuario contextualmente, z debe ingeniárselo la IA para saber cuales son. Lo mismo aplica para cuando usuario dice amenazas o salvaguardas pero dice un numero concreto y no todas aparecen en archivos o fueron especificadas en el prompt. 
   - Si los datos contienen menos activos de los que el usuario dice, completa con activos típicos realistas pero sin inventar IDs. 
   - En caso contrario (sin indicación), usa los activos que se hayan encontrado en los archivos. NO añadas activos extra si no es necesario.
   - PROHIBIDO ACTIVOS DUPLICADOS
   - Lee bien el texto de documentos, para detectar dependencias, por ejemplo siendo dos activos X e Y, si se especifica ya sea por texto o en alguna archivo X depende de Y, o por ejemplo también tiene como dependencia, es dependiente de, entre otras formas textuales de decirlo, es que X depende de Y. Si aparecen como columnas, en la fila del activo X, sus dependencias estarán en columnas con nombres tales como 'Dependencias', 'Depende de', 'Es dependiente de', entre otros...

   - Si en el texto extraído aparece "above X below Y", significa que Y depende de X, SIENDO X E Y DOS ACTIVOS
   
Para clasificar los tipos de activos ten en cuenta estas palabras claves:
IMPORTANTE A TENER EN CUENTA: Tanto en los archivos como en las palabras escritas del usuario, pueden estar en mayúsculas, minúsculas o con faltas de ortografía. Presta atención a eso. 
1. CLAVES CRIPTOGRÁFICAS [K]:
        'clave', 'certificado', 'cifrado', 'criptografico', 'token', 'contraseña', 'contrasena',
        'codigo de acceso', 'codigodeacceso', 'password', 'pin', 'otp', 'seudonimo', 'alias',
        'clave privada', 'claveprivada', 'clave publica', 'clavepublica', 'certificado digital',
        'certificadodigital', 'firma electronica', 'firmaelectronica', 'token de acceso',
        'tokendeacceso', 'token de autenticacion', 'tokendeautenticacion'
2. SOFTWARE / APLICACIONES [SW]:
        'aplicacion', 'app', 'software', 'sistema operativo', 'sistemaoperativo', 'windows',
        'linux', 'macos', 'android', 'ios', 'firmware', 'middleware', 'web service', 'webservice',
        'gestor bd', 'gestorbd', 'mysql', 'postgresql', 'oracle', 'sql server', 'sqlserver',
        'servidor correo', 'servidorcorreo', 'exchange', 'outlook', 'navegador', 'chrome',
        'firefox', 'edge', 'safari', 'ofimatica', 'office', 'word', 'excel', 'powerpoint',
        'erp', 'crm', 'antivirus', 'edr', 'virtualizacion', 'vmware', 'docker', 'contenedor', 'api'
3. HARDWARE [HW]:
        'servidor', 'ordenador', 'pc', 'portatil', 'portatil', 'hardware', 'equipo', 'router',
        'switch', 'disco', 'cpu', 'central', 'workstation', 'estacion trabajo', 'estaciontrabajo',
        'cliente ligero', 'clienteligero', 'thin client', 'thinclient', 'impresora', 'scanner',
        'fotocopiadora', 'fax', 'monitor', 'pantalla', 'teclado', 'raton', 'periferico',
        'almacenamiento', 'nas', 'rack', 'blade', 'mainframe', 'miniordenador', 'tablet', 'movil',
        'movil', 'telefono', 'smartphone', 'laptop', 'desktop', 'memoria ram', 'memoriaram',
        'placa base', 'placabase'
4. DATOS / INFORMACIÓN [D]:
        'base de datos', 'basesdedatos', 'bases de datos', 'datos', 'informacion', 'archivo',
        'fichero', 'registro', 'log', 'documento', 'expediente', 'historial', 'informe', 'reporte',
        'estadistica', 'indicador', 'correo', 'email', 'mensaje', 'contenido', 'publicacion',
        'pagina web', 'paginaw eb', 'imagen', 'video', 'audio', 'multimedia', 'backup',
        'copia de seguridad', 'copiadeseguridad', 'configuracion', 'parametro', 'licencia',
        'contrato', 'factura', 'pedido', 'nomina', 'datos personales', 'datospersonales',
        'datos sensibles', 'datossensibles'
5. REDES DE COMUNICACIONES [COM]:
        'red', 'comunicacion', 'wifi', 'internet', 'fibra', 'lan', 'wan', 'wireless', 'vlan',
        'vpn', 'hub', 'bridge', 'access point', 'accesspoint', 'gateway', 'firewall', 'proxy',
        'dns', 'dhcp', 'enlace', 'circuito', 'banda ancha', 'bandaancha', 'adsl', 'fibra optica',
        'fibraoptica', 'cable red', 'cablered', 'ethernet', 'mpls'
6. SOPORTES DE INFORMACIÓN [Media]:
        'soporte', 'disco duro', 'discoduro', 'usb', 'pendrive', 'cd', 'dvd', 'cinta magnetica',
        'cintamagnetica', 'blu-ray', 'bluray', 'disquete', 'tarjeta memoria', 'tarjetamemoria',
        'ssd', 'disco externo', 'discoexterno', 'san'
7. EQUIPAMIENTO AUXILIAR [AUX]:
        'climatizacion', 'aire acondicionado', 'aireacondicionado', 'calefaccion', 'ventilacion',
        'electricidad', 'sae', 'ups', 'sai', 'generador', 'bateria', 'extintor', 'detector humos',
        'detectorhumos', 'alarma incendios', 'alarmaincendios', 'iluminacion', 'ascensor',
        'montacargas', 'camara', 'puerta blindada', 'puertablindada', 'grupo electrogeno',
        'grupoelectrogeno', 'fuente alimentacion', 'fuentealimentacion', 'regulador tension',
        'reguladortension', 'pdu'
8. INSTALACIONES [L]:
        'sala', 'edificio', 'oficina central', 'oficinacentral', 'sede central', 'sedecentral',
        'oficina', 'instalacion', 'local', 'sede', 'planta', 'almacen', 'campus', 'aula',
        'laboratorio', 'despacho', 'vestuario', 'cafeteria', 'biblioteca', 'centro de datos',
        'centroredatos', 'cpd', 'data center', 'datacenter', 'nave', 'taller', 'garaje',
        'aparcamiento', 'parking', 'recepcion', 'hall'
9. PERSONAL [P]
        'personal', 'usuario', 'operador', 'administrador', 'empleado', 'persona', 'supervisor',
        'director', 'gerente', 'analista', 'tecnico', 'ingeniero', 'becario', 'contratista',
        'visitante', 'vigilante', 'limpiador', 'responsable', 'coordinador', 'jefe',
        'subdirector', 'rector', 'profesor', 'alumno', 'estudiante', 'pas', 'pdi'


2. **DIMENSIONES (Confidencialidad, Integridad, Disponibilidad, Autenticidad, Trazabilidad)**:  
    
   - Debes leer esos números y para cada activo, en la tabla HTML, escribir el texto correspondiente y colorear la celda según:  
        * **BAJO** → color VERDE (`style="background-color:#d4edda;"`)  
        * **MEDIO**   → color AMARILLO (`style="background-color:#fff3cd;"`)  
        * **ALTO**   → color ROJO (`style="background-color:#f8d7da;"`)  
   - Si algún valor no está presente o es "?", usa "BAJO" por defecto.

3. **ID de activos**: Usa el formato `act.tipo_activo.n` donde `tipo_activo` es una abreviatura (hw, sw, d, com, l, p, media, aux) y `n` es un número correlativo empezando por 0 para cada tipo. Ejemplo: `act.hw.0`, `act.d.1`.  
   - Si ya hay IDs en los datos   convertirlos al nuevo formato manteniendo la correspondencia.
   - En la celda donde se especifica el tipo de activo pon la abreviatura no el nombre del tipo (EN MAYÚSCULAS).

4. **AMENAZAS**: Asigna a cada amenaza el código más parecido del catálogo oficial (sección superior). Si no hay coincidencia, IGNORAR
   - Frecuencia y degradación deben ser números entre 0 y 1. Si vienen en porcentaje (X%), conviértelos a decimal (0.X).  
   - La columna "Activos específicos (Id)" debe contener los IDs de los activos a los que afecta (según los datos o según lógica de tipos).
   - PROHIBIDO AMENAZAS DUPLICADAS
5. **SALVAGUARDAS**: Solo incluye en la tabla aquellas que mitigan al menos una amenaza. Para cada salvaguarda, asigna un código del catálogo oficial (si no tiene, usa el nombre como código).    
   - En la columna "Amenazas que mitiga (Código)" pon los códigos de las amenazas correspondientes (según los datos o según coherencia de tipos de activos).
   - En efectividad sobre frecuencia y efectividad sobre degradación de salvaguardas representalo como Lx (valor), siendo L0 para valores entre 0 y 9.9%, L1 para valores entre 10 y 49.9%, L2 para valores entre 50% y 79.9%, L3 para valores entre 80 y 89.9%, L4 para valores entre 90 y 94.9% y L5 para valores mayores a 95%. DEBE APARECER TANTO Lx COMO (valor) LAS DOS COSAS VISIBLES EN LA PANTALLA
   - PROHIBIDO SALVAGUARDAS DUPLICADOS


7. **FORMATO DE RESPUESTA**: Debes generar **exactamente 4 tablas HTML** (con las columnas indicadas) y el apartado de conclusiones. No añadas texto introductorio ni explicaciones adicionales.  
   - Las tablas deben ser válidas, con etiquetas `<table>`, ` <thead>`, ` <tbody>`, ` <tr>`, ` <td>`.  
   - Aplica los colores de las dimensiones en las celdas correspondientes usando el atributo `style`.  
   - Para las celdas de categoría, calcula el máximo de las cinco dimensiones y aplica el mismo color.

8. **CONCLUSIONES**: Escribe un párrafo de máximo 200 palabras con las principales conclusiones y un plan de tratamiento basado en los riesgos identificados.

========================================
FORMATO OBLIGATORIO DE RESPUESTA:
========================================
TABLA 1: ACTIVOS Y DEPENDENCIAS
| Id | Activo | Tipo | Valor (€) | Depende de (Id) | Grado | Confidencialidad | Integridad | Disponibilidad | Autenticidad | Trazabilidad | Categoría |
(Usa colores: verde para BAJO, amarillo para MEDIO, rojo para ALTO)

TABLA 2: AMENAZAS
| Código | Amenaza | Frecuencia (0-1) | Degradación (0-1) | Tipos de activos que afecta | Activos específicos (Id) | Dimensiones afectadas |

TABLA 3: SALVAGUARDAS
| Código | Salvaguarda | Efectividad Frecuencia | Efectividad Degradación | Amenazas que mitiga (Código) |

 
TABLA 4: CONSECUENCIAS DE NO MITIGAR RIESGOS PARA CADA ACTIVO  

**Para CADA activo**, debes seguir estos pasos. 

**Columnas de la tabla:**

| Id | Activo | Consecuencias operativas | Consecuencias legales |

### 5. Consecuencias operativas y legales: escribe consecuencias operativas y legales que conllevan no mitigar los riesgos para cada activo, máximo 200 caracteres.
  
<br>CONCLUSIONES Y PLAN DE TRATAMIENTO</br>
(Máximo 200 palabras, basado en las tablas y en el contexto de MAGERIT)

========================================
RESPONDE ÚNICAMENTE CON LAS 4 TABLAS HTML Y EL APARTADO DE CONCLUSIONES.
========================================
"""
    
 # 8. Llamar a la IA según el proveedor configurado
    try:
        if api_keys.PROVEEDOR_ACTIVO == "mistral":
            resp = requests.post(
                api_keys.get_url(),
                headers=api_keys.get_headers(),
                json={
                    "model": api_keys.get_modelo(),
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                    "max_tokens": 6000
                },
                timeout=120
            )
            if resp.status_code == 200:
                respuesta_ia = resp.json()["choices"][0]["message"]["content"]
            else:
                return f"<div style='background:#f8d7da;padding:20px;'><h3>Error Mistral: {resp.status_code}</h3></div>"
        elif api_keys.PROVEEDOR_ACTIVO == "gemini":
            resp = requests.post(
                api_keys.get_url(),
                headers=api_keys.get_headers(),
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.0, "maxOutputTokens": 6000}
                },
                timeout=120
            )
            if resp.status_code == 200:
                data = resp.json()
                respuesta_ia = data["candidates"][0]["content"]["parts"][0]["text"]
            else:
                return f"<div style='background:#f8d7da;padding:20px;'><h3>Error Gemini: {resp.status_code}</h3></div>"
        elif api_keys.PROVEEDOR_ACTIVO == "groq":
            resp = requests.post(
                api_keys.get_url(),
                headers=api_keys.get_headers(),
                json={
                    "model": api_keys.get_modelo(),
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                    "max_tokens": 6000
                },
                timeout=120
            )
            if resp.status_code == 200:
                respuesta_ia = resp.json()["choices"][0]["message"]["content"]
            else:
                return f"<div style='background:#f8d7da;padding:20px;'><h3>Error Groq: {resp.status_code}</h3></div>"
        else:
            return f"<div style='background:#f8d7da;padding:20px;'><h3>PROVEEDOR_ACTIVO '{api_keys.PROVEEDOR_ACTIVO}' no válido</h3></div>"
        

        
        # Devolver el HTML de la IA + el botón de descarga
        return f"""
        {respuesta_ia}
        """
        
    except Exception as e:
        return f"<div style='background:#f8d7da;padding:20px;'><h3>Error: {str(e)}</h3></div>"