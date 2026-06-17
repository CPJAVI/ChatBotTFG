# pilar_xml.py - Funciones para generar XML compatible con PILAR RM
# pilar_xml.py - Genera XML compatible con PILAR RM
# pilar_xml.py - Genera XML compatible con PILAR RM (estructura proyecto fuull.xml)
# pilar_xml.py - Genera XML compatible con PILAR RM
# pilar_xml.py - Genera XML compatible con PILAR RM
# Procesa las 4 tablas HTML generadas por ia_prompt.py
# pilar_xml.py - Genera XML compatible con PILAR RM
# Procesa las 4 tablas HTML generadas por ia_prompt.py

import re
from datetime import datetime
from bs4 import BeautifulSoup
from typing import Dict, List, Any, Tuple

PLANTILLA_XML_PILAR = '''<?xml version="1.0" encoding="UTF-8"?>
<model code="{codigo_modelo}">
    <name>{nombre_modelo}</name>
    <tool>
        <name>PILAR RM</name>
        <version>2025.1.4 - 31.10.2025</version>
    </tool>
    <date>{fecha}</date>
    <data key="org" name="Organización" text="{organizacion}"/>
    <data key="author" name="Autor" text="{autor}"/>
    <data key="version" name="Versión" text="{version}"/>
    <data key="desc" name="Descripción" text="{descripcion}"/>
    <data key="version pilar" name="version pilar" text="5.4.7 - 12.11.2015"/>
    
    <domain c="base">
        <name>Base</name>
    </domain>
    
    <layer c="essential"><name>Información y servicios esenciales</name></layer>
    <layer c="S.3rd"><name>contratado a terceros</name></layer>
    <layer c="D"><name>Datos / Información</name></layer>
    <layer c="S"><name>Servicios</name></layer>
    <layer c="SW"><name>Aplicaciones (software)</name></layer>
    <layer c="HW"><name>Equipamiento informático (hardware)</name></layer>
    <layer c="COM"><name>Redes de comunicaciones</name></layer>
    <layer c="AUX"><name>Equipamiento auxiliar</name></layer>
    <layer c="L"><name>Instalaciones</name></layer>
    <layer c="P"><name>Personal</name></layer>
    <layer c="K"><name>Claves criptográficas</name></layer>
    <layer c="Media"><name>Soportes de información</name></layer>
    
    <stereotype c="std:asset">
        <value dim="val_econ" acr="Valor Económico" min="0" max="5" />
        <value dim="es.d" acr="Disponibilidad" min="0" max="5" />
        <value dim="es.i" acr="Integridad" min="0" max="5" />
        <value dim="es.c" acr="Confidencialidad" min="0" max="5" />
        <value dim="es.a" acr="Autenticidad" min="0" max="5" />
        <value dim="es.t" acr="Trazabilidad" min="0" max="5" />
    </stereotype>
    
{activos_xml}
{dependencias_xml}
{valores_xml}
{amenazas_xml}
{salvaguardas_xml}
</model>'''

# Mapeo de dimensión a acronym (segun proyecto fuull.xml)
DIM_A_ACRONYM = {
    'es.d': '[D]',
    'es.i': '[I]',
    'es.c': '[C]',
    'es.a': '[A]',
    'es.t': '[T]',
    'val_econ': ''  # val_econ no lleva acronym
}

def extraer_valor_economico(texto: str) -> int:
    """Extrae valor económico de texto como '500000' o '500.000' -> 500000"""
    if not texto or texto == '-':
        return 0
    limpio = re.sub(r'[^\d]', '', texto)
    try:
        return int(limpio) if limpio else 0
    except:
        return 0

def escala_valor_economico(valor: int) -> int:
    """Escala valor económico a 1-5 para PILAR"""
    if valor <= 0:
        return 1
    elif valor <= 10000:
        return 1
    elif valor <= 50000:
        return 2
    elif valor <= 100000:
        return 3
    elif valor <= 200000:
        return 4
    else:
        return 5

def nivel_ens_a_numero(texto: str) -> int:
    """Convierte 'Muy Alto' -> 5, 'Alto' -> 4, 'Medio' -> 3, 'Bajo' -> 2, 'Muy Bajo' -> 1"""
    if not texto:
        return 2
    mapa = {
        'muy alto': 5,
        'alto': 4,
        'medio': 3,
        'bajo': 2,
        'muy bajo': 1
    }
    texto_limpio = texto.lower().strip()
    for clave, valor in mapa.items():
        if clave in texto_limpio:
            return valor
    # Si es un número directamente
    try:
        return int(texto_limpio)
    except:
        return 2

def mapear_tipo_a_capa(tipo: str) -> str:
    """Mapea [D] -> D, [SW] -> SW, [HW] -> HW, [COM] -> COM, [P] -> P, etc."""
    if not tipo:
        return 'essential'
    tipo_limpio = tipo.strip('[]')
    if tipo_limpio in ['D', 'K', 'S', 'SW', 'HW', 'COM', 'AUX', 'L', 'P', 'Media', 'essential']:
        return tipo_limpio
    return 'essential'






def extraer_dependencias_grado(texto_depende: str, texto_grado: str) -> List[Tuple[str, int]]:
    """Extrae lista de (id_dependencia, grado) del texto"""
    if not texto_depende or texto_depende == '-' or texto_depende == '':
        return []
    
    # Buscar IDs completos en formato act.tipo.n (ej: act.k.0, act.hw.1, act.sw.0)
    ids = re.findall(r'act\.[a-z]+\.[0-9]+', texto_depende)
    
    # Si no encuentra ese formato, buscar números sueltos (por si acaso)
    if not ids:
        ids = re.findall(r'\b\d+\b', texto_depende)
        ids = [f"act.unknown.{i}" for i in ids]
    
    if not ids:
        return []
    
    grado = 100
    if texto_grado and texto_grado != '-' and texto_grado != '':
        # Quitar estilos HTML
        grado_texto = re.sub(r'<[^>]+>', '', str(texto_grado))
        match = re.search(r'(\d+(?:[.,]\d+)?)', grado_texto)
        if match:
            valor_str = match.group(1).replace(',', '.')
            try:
                valor = float(valor_str)
                if valor <= 1:
                    grado = int(round(valor * 100))
                else:
                    grado = int(valor)
                grado = max(1, min(100, grado))
            except ValueError:
                pass
    
    return [(id_dep, grado) for id_dep in ids]






 
def generar_xml_pilar(contenido_html: str, 
                      organizacion: str = "", 
                      autor: str = "",
                      version: str = "1.0",
                      descripcion: str = "") -> str:
    
    soup = BeautifulSoup(contenido_html, 'html.parser')
    tablas = soup.find_all('table')
    
    activos: Dict[str, Dict] = {}
    dependencias: List[Tuple[str, str, int]] = []
    amenazas: List[Dict] = []
    salvaguardas: List[Dict] = []
    
    # ============================================================
    # TABLA 1: ACTIVOS
    # ============================================================
    if len(tablas) >= 1:
        filas = tablas[0].find_all('tr')
        for fila in filas[1:]:
            celdas = fila.find_all(['td', 'th'])
            if len(celdas) < 6:
                continue
            
            texto_celdas = [celda.get_text().strip() for celda in celdas]
            
            activo_id = texto_celdas[0]
            if not activo_id or activo_id == 'Id' or activo_id == 'ID':
                continue
            
            nombre = texto_celdas[1] if len(texto_celdas) > 1 else ""
            tipo = texto_celdas[2] if len(texto_celdas) > 2 else "essential"
            valor_texto = texto_celdas[3] if len(texto_celdas) > 3 else "0"
            
            depende_de = texto_celdas[4] if len(texto_celdas) > 4 else ""
            grado_texto = texto_celdas[5] if len(texto_celdas) > 5 else ""
            
            # Dimensiones ENS
            confidencialidad = texto_celdas[6] if len(texto_celdas) > 6 else "2"
            integridad = texto_celdas[7] if len(texto_celdas) > 7 else "2"
            disponibilidad = texto_celdas[8] if len(texto_celdas) > 8 else "2"
            autenticidad = texto_celdas[9] if len(texto_celdas) > 9 else "2"
            trazabilidad = texto_celdas[10] if len(texto_celdas) > 10 else "2"
            
            capa = mapear_tipo_a_capa(tipo)
            valor_economico = extraer_valor_economico(valor_texto)
            
            activos[activo_id] = {
                'id': activo_id,
                'nombre': nombre,
                'capa': capa,
                'valor_economico': valor_economico,
                'dimensiones': {
                    'es.c': nivel_ens_a_numero(confidencialidad),
                    'es.i': nivel_ens_a_numero(integridad),
                    'es.d': nivel_ens_a_numero(disponibilidad),
                    'es.a': nivel_ens_a_numero(autenticidad),
                    'es.t': nivel_ens_a_numero(trazabilidad),
                    'val_econ': escala_valor_economico(valor_economico)
                }
            }
            
            # Dependencias
            for dep_id, grado in extraer_dependencias_grado(depende_de, grado_texto):
                if dep_id != activo_id:
                    dependencias.append((activo_id, dep_id, grado))
    
    # ============================================================
    # TABLA 2: AMENAZAS
    # ============================================================
    if len(tablas) >= 2:
        filas = tablas[1].find_all('tr')
        for fila in filas[1:]:
            celdas = fila.find_all(['td', 'th'])
            if len(celdas) < 4:
                continue
            
            texto_celdas = [celda.get_text().strip() for celda in celdas]
            
            if texto_celdas[0] == 'Código' or texto_celdas[0] == 'Codigo':
                continue
            
            codigo = re.sub(r'[\[\]]', '', texto_celdas[0])
            if not codigo:
                continue
                
            nombre = texto_celdas[1] if len(texto_celdas) > 1 else ""
            frecuencia = texto_celdas[2] if len(texto_celdas) > 2 else "0"
            degradacion = texto_celdas[3] if len(texto_celdas) > 3 else "0"
            
            capa = "essential"
            if len(texto_celdas) > 4:
                tipos_afecta = texto_celdas[4]
                if '[D]' in tipos_afecta:
                    capa = "D"
                elif '[SW]' in tipos_afecta:
                    capa = "SW"
                elif '[HW]' in tipos_afecta:
                    capa = "HW"
                elif '[COM]' in tipos_afecta:
                    capa = "COM"
                elif '[P]' in tipos_afecta:
                    capa = "P"
            
            amenazas.append({
                'codigo': codigo,
                'nombre': nombre,
                'capa': capa,
                'frecuencia': frecuencia,
                'degradacion': degradacion
            })
    
    # ============================================================
    # TABLA 3: SALVAGUARDAS
    # ============================================================
    if len(tablas) >= 3:
        filas = tablas[2].find_all('tr')
        for fila in filas[1:]:
            celdas = fila.find_all(['td', 'th'])
            if len(celdas) < 2:
                continue
            
            texto_celdas = [celda.get_text().strip() for celda in celdas]
            
            if texto_celdas[0] == 'Código' or texto_celdas[0] == 'Codigo':
                continue
            
            codigo = re.sub(r'[\[\]]', '', texto_celdas[0])
            if not codigo:
                continue
                
            nombre = texto_celdas[1] if len(texto_celdas) > 1 else ""
            eff_freq = texto_celdas[2] if len(texto_celdas) > 2 else ""
            eff_degr = texto_celdas[3] if len(texto_celdas) > 3 else ""
            
            amenazas_mitiga = []
            if len(texto_celdas) > 4:
                amenazas_mitiga = re.findall(r'([A-Z]\.[0-9]+)', texto_celdas[4])
            
            salvaguardas.append({
                'codigo': codigo,
                'nombre': nombre,
                'eff_freq': eff_freq,
                'eff_degr': eff_degr,
                'mitiga': amenazas_mitiga
            })
    
    # ============================================================
    # GENERAR XML
    # ============================================================
    
    # Activos XML
    activos_lines = []
    for a in activos.values():
        activos_lines.append(f'    <asset c="{a["id"]}" domain="base" layer="{a["capa"]}">')
        activos_lines.append(f'        {a["nombre"]}')
        activos_lines.append(f'        <type c="te.{a["capa"].lower()}"/>')
        activos_lines.append('    </asset>')
    activos_xml = '\n'.join(activos_lines) if activos_lines else '    <!-- No hay activos -->'
    
    # Dependencias XML
    dependencias_lines = []
    seen = set()
    for hijo, padre, grado in dependencias:
        key = f"{hijo}_{padre}"
        if key not in seen:
            seen.add(key)
            dependencias_lines.append(f'    <depend above="{padre}" below="{hijo}" degree="{grado}%"/>')
    dependencias_xml = '\n'.join(dependencias_lines) if dependencias_lines else '    <!-- No hay dependencias -->'
    
    # Amenazas XML
    amenazas_lines = []
    for am in amenazas:
        amenazas_lines.append(f'    <threat c="{am["codigo"]}" layer="{am["capa"]}">')
        amenazas_lines.append(f'        <name>{am["nombre"]}</name>')
        if am["frecuencia"] and am["frecuencia"] not in ['0', '0.0', '']:
            amenazas_lines.append(f'        <freq vl="{am["frecuencia"]}"/>')
        if am["degradacion"] and am["degradacion"] not in ['0', '0.0', '']:
            amenazas_lines.append(f'        <degr vl="{am["degradacion"]}"/>')
        amenazas_lines.append('    </threat>')
    amenazas_xml = '\n'.join(amenazas_lines) if amenazas_lines else '    <!-- No hay amenazas -->'
    
    # Salvaguardas XML
    salvaguardas_lines = []
    for sg in salvaguardas:
        salvaguardas_lines.append(f'    <safeguard c="{sg["codigo"]}">')
        salvaguardas_lines.append(f'        <name>{sg["nombre"]}</name>')
        if sg["eff_freq"]:
            salvaguardas_lines.append(f'        <eff-freq vl="{sg["eff_freq"]}"/>')
        if sg["eff_degr"]:
            salvaguardas_lines.append(f'        <eff-degr vl="{sg["eff_degr"]}"/>')
        if sg["mitiga"]:
            salvaguardas_lines.append(f'        <mitigates>{", ".join(sg["mitiga"])}</mitigates>')
        salvaguardas_lines.append('    </safeguard>')
    salvaguardas_xml = '\n'.join(salvaguardas_lines) if salvaguardas_lines else '    <!-- No hay salvaguardas -->'
    
    # Valores XML (CON ACRONYM como en proyecto fuull.xml)
    valores_lines = []
    for a in activos.values():
        dims = a['dimensiones']
        # val_econ no tiene acronym
        valores_lines.append(f'    <value asset="{a["id"]}" dim="val_econ" vl="{dims["val_econ"]}"/>')
        valores_lines.append(f'    <value asset="{a["id"]}" dim="es.d" acronym="[D]" vl="{dims["es.d"]}"/>')
        valores_lines.append(f'    <value asset="{a["id"]}" dim="es.i" acronym="[I]" vl="{dims["es.i"]}"/>')
        valores_lines.append(f'    <value asset="{a["id"]}" dim="es.c" acronym="[C]" vl="{dims["es.c"]}"/>')
        valores_lines.append(f'    <value asset="{a["id"]}" dim="es.a" acronym="[A]" vl="{dims["es.a"]}"/>')
        valores_lines.append(f'    <value asset="{a["id"]}" dim="es.t" acronym="[T]" vl="{dims["es.t"]}"/>')
    valores_xml = '\n'.join(valores_lines) if valores_lines else '    <!-- No hay valores -->'
    
    return PLANTILLA_XML_PILAR.format(
        codigo_modelo="ANALISIS",
        nombre_modelo="ANALISIS_RIESGOS",
        fecha=datetime.now().strftime("%a %b %d %H:%M:%S %Y"),
        organizacion=organizacion or "ORGANIZACION",
        autor=autor or "AUTOR",
        version=version,
        descripcion=descripcion or "Analisis de riesgos",
        activos_xml=activos_xml,
        dependencias_xml=dependencias_xml,
        amenazas_xml=amenazas_xml,
        salvaguardas_xml=salvaguardas_xml,
        valores_xml=valores_xml
    )