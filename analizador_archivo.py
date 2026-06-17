import os
import re
import requests
import pandas as pd
import pdfplumber
from docx import Document
from bs4 import BeautifulSoup
from typing import List

import api_keys
from rag import GestorRAG

# ------------------------------------------------------------
# RAG
# ------------------------------------------------------------
gestor_rag = GestorRAG()
if len(gestor_rag.textos) == 0:
    gestor_rag.cargar_libros()

# ------------------------------------------------------------
# EXTRACCIÓN DE TEXTO DE ARCHIVOS (igual que antes)
# ------------------------------------------------------------
def extraer_texto_archivo(ruta: str) -> str:
    ext = os.path.splitext(ruta)[1].lower()
    texto = ""
    try:
        if ext in ['.xlsx', '.xls']:
            dfs = pd.read_excel(ruta, sheet_name=None)
            for hoja, df in dfs.items():
                texto += f"\n--- Hoja: {hoja} ---\n{df.to_csv(index=False)}\n"
        elif ext == '.csv':
            df = pd.read_csv(ruta)
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
        elif ext in ['.html', '.htm']:
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

def extraer_contenido_archivos(archivos: List[str]) -> str:
    contenido = ""
    for ruta in archivos:
        texto = extraer_texto_archivo(ruta)
        if texto:
            contenido += f"\n\n========= {os.path.basename(ruta)} =========\n{texto}\n"
    if not contenido:
        contenido = "No se han proporcionado archivos."
    return contenido

# ------------------------------------------------------------
# CATÁLOGOS DEL RAG (SIN MODIFICACIONES)
# ------------------------------------------------------------
def obtener_catalogo_amenazas(limit: int = 100) -> str:
    catalogo = ""
    for idx in gestor_rag.indices_amenazas[:limit]:
        item = gestor_rag.textos[idx]
        cod = item.get("codigo", "")
        nom = item.get("nombre", "")
        tipos_activos= item.get('tipos_activos', []),
        dimensiones = item.get('dimensiones', []),        
        if cod and nom:
            catalogo += f"- {cod}: {nom}\n"
    if not catalogo:
        resultados = gestor_rag.buscar_amenazas("")
        for r in resultados[:limit]:
            catalogo += f"- {r.get('codigo', '')}: {r.get('nombre', '')} : {r.get('tipos_activos', [])} : {r.get('dimensiones', [])}\n"
    return catalogo

def obtener_catalogo_salvaguardas(limit: int = 100) -> str:
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

# ------------------------------------------------------------
# CONSTRUCCIÓN DEL PROMPT SIN VALORES ORIENTATIVOS
# ------------------------------------------------------------
def construir_prompt(pregunta: str, contenido_archivos: str) -> str:
    catalogo_amenazas = obtener_catalogo_amenazas(100)
    catalogo_salvaguardas = obtener_catalogo_salvaguardas(100)

    return f"""Eres un experto en análisis de riesgos con MAGERIT 3.

========================================
CATÁLOGO OFICIAL DE AMENAZAS (ÚNICOS CÓDIGOS PERMITIDOS):
========================================
{catalogo_amenazas}

========================================
CATÁLOGO OFICIAL DE SALVAGUARDAS (ÚNICOS CÓDIGOS PERMITIDOS):
========================================
{catalogo_salvaguardas}

========================================
INSTRUCCIONES ESTRICTAS:
========================================
1. **No inventes ningún dato.** Usa exclusivamente la información del contenido de los archivos. 
2. **Si falta un dato** (frecuencia, degradación, valor de activo, efectividad, etc.), escribe un valor realista aleatorio. 
3. **Para amenazas y salvaguardas** usa ÚNICAMENTE los códigos y nombres de los catálogos anteriores. Si el nombre de una amenaza o salvaguardas no aparece exactamente en esos catálogos, pero el usuario lo menciona en los archivos, busca el código más parecido en el catálogo y utilízalo (los nombres pueden venir tanto en mayúscula como en minúscula en los datos, y pueden también contener faltas de ortografía, tenlo en cuenta), ya sea de amenaza o salvaguardas, según su contexto. Si no encuentras ninguno, IGNORAR. 
4. **Para los activos**, las dimensiones (Confidencialidad, Integridad, Disponibilidad, Autenticidad, Trazabilidad) deben extraerse del contenido del archivo. Si no aparecen, investiga en el ENS. No olvides colorear celdas rojo para ALTO, amarillo para MEDIO y verde para BAJO.
5. **No rellenes automáticamente ninguna celda** con valores ficticios. Si no hay información, que quede vacío.
6. SOLO si el fichero introducido contiene <name>PILAR RM</name> exactamente así, cuando vayas a poner el valor en valor si es 1 pon 10000, si el valor es 2 pon 50000, si el valor es 3 pon 100000, si el valor es 4 pon 200000 y si el valor es 5 pon 500000 el valor de cada activo. Si es cualquier otro activo y su valor está especificado con un numero exacto o lo dice el usuario por escrito, pon ese otro valor.
7. PROHIBIDO EXPRESAMENTE PONER SALVAGUARDAS O AMENAZAS DUPLICADOS EN CÓDIGO O NOMBRE
========================================
FORMATO OBLIGATORIO DE RESPUESTA:
========================================
TABLA 1: ACTIVOS
| Id | Activo | Tipo | Valor (€) | Depende de (Id) | Grado | Confidencialidad | Integridad | Disponibilidad | Autenticidad | Trazabilidad | Categoría |
NOTA: EL VALOR DE CATEGORÍA ES EL MAYOR DE LAS 5 DIMENSIONES, POR VALOR PUEDE VENIR ESPECIFICADO COMO VALOR, VALOR ECONÓMICO, €, VALOR (€), DE MUCHAS FORMAS ESPECÍFICAS.

TABLA 2: AMENAZAS
| Código | Amenaza | Frecuencia (0-1) | Degradación (0-1) | Tipos de activos que afecta | Activos específicos (Id) | Dimensiones afectadas |
NOTA: UNA AMENAZA QUE AFECTA A UNO O VARIOS TIPOS DE ACTIVOS SOLO PUEDE AFECTAR A ACTIVOS QUE PERTENEZCAN A ALGUNO DE ESOS TIPOS. SI UNA AMENAZA NO AFECTA NINGÚN ACTIVO, ELIMINAR
 
TABLA 3: SALVAGUARDAS
| Código | Salvaguarda | Efectividad Frecuencia | Efectividad Degradación | Amenazas que mitiga (Código) |
NOTA: UN SALVAGUARDAS SOLO PUEDE MITIGAR AMENAZAS QUE AFECTEN A ACTIVOS CUYO TIPO APAREZCA (COMO SECUENCIA DE PALABRAS) EN EL CÓDIGO DEL SALVAGUARDAS. SI UN SALVAGUARDAS NO MITIGA NINGUNA AMENAZA, IGNORAR 
TABLA 4: RIESGOS POR ACTIVO
| Id | Activo | Riesgo Directo (€/año) | Riesgo por Dependencias (€/año) | Riesgo Potencial TOTAL (€/año) | Riesgo Residual (€/año) | Consecuencias operativas | Consecuencias legales |

CONCLUSIONES Y PLAN DE TRATAMIENTO
(un párrafo de máximo 200 palabras)

========================================
CONTENIDO DE LOS ARCHIVOS:
========================================
{contenido_archivos}

========================================
PREGUNTA DEL USUARIO:
========================================
{pregunta}

========================================
RESPONDE ÚNICAMENTE CON LAS TABLAS HTML Y EL APARTADO DE CONCLUSIONES. NO AÑADAS NINGÚN TEXTO ADICIONAL.
========================================
"""

# ------------------------------------------------------------
# LLAMADA A LA IA
# ------------------------------------------------------------
def llamar_ia(prompt: str) -> str:
    try:
        if api_keys.PROVEEDOR_ACTIVO == "mistral":
            resp = requests.post(
                api_keys.get_url(),
                headers=api_keys.get_headers(),
                json={
                    "model": api_keys.get_modelo(),
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.0,
                    "max_tokens": 6000
                },
                timeout=120
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            else:
                return f"<div style='background:#f8d7da;padding:20px;'><h3>Error Mistral: {resp.status_code}</h3></div>"
        elif api_keys.PROVEEDOR_ACTIVO == "gemini":
            resp = requests.post(
                api_keys.get_url(),
                headers=api_keys.get_headers(),
                json={
                    "contents": [{
                        "parts": [{"text": prompt}]
                    }],
                    "generationConfig": {
                        "temperature": 0.0,
                        "maxOutputTokens": 6000
                    }
                },
                timeout=120
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
            else:
                return f"<div style='background:#f8d7da;padding:20px;'><h3>Error Gemini: {resp.status_code}</h3></div>"
        elif api_keys.PROVEEDOR_ACTIVO == "groq":
            resp = requests.post(
                api_keys.get_url(),
                headers=api_keys.get_headers(),
                json={
                    "model": api_keys.get_modelo(),
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.0,
                    "max_tokens": 6000
                },
                timeout=120
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            else:
                return f"<div style='background:#f8d7da;padding:20px;'><h3>Error Groq: {resp.status_code}</h3></div>"
        else:
            return f"<div style='background:#f8d7da;padding:20px;'><h3>PROVEEDOR_ACTIVO '{api_keys.PROVEEDOR_ACTIVO}' no válido</h3></div>"
    except Exception as e:
        return f"<div style='background:#f8d7da;padding:20px;'><h3>Error: {str(e)}</h3></div>"

# ------------------------------------------------------------
# FUNCIÓN PRINCIPAL
# ------------------------------------------------------------
def analizar_con_ia_archivos(pregunta: str, archivos: List[str], contexto_magerit: str = "") -> str:
    contenido = extraer_contenido_archivos(archivos)
    prompt = construir_prompt(pregunta, contenido)
    from ia_prompt import analizar_con_ia
    return analizar_con_ia(prompt)

 