 # tablas_txt.py
# tablas_txt.py
import re
import os
from datetime import datetime
from typing import Dict, List, Tuple
from bs4 import BeautifulSoup

class CalculadorRiesgosMagerit:
    """
    Clase independiente para calcular riesgos según MAGERIT Libro III.
    """
    
    # Escala de eficacias estándar de MAGERIT (Libro III)
    EFICACIAS = {
        "L5": 0.98,
        "L4": 0.88,
        "L3": 0.70,
        "L2": 0.50,
        "L1": 0.25,
        "L0": 0.0
    }
    
    def __init__(self):
        self.activos = []
        self.amenazas = []
        self.salvaguardas = []
        self.resultados = {}
    
    def cargar_desde_html(self, contenido_html: str):
        """Carga los datos desde el HTML generado por la IA"""
        soup = BeautifulSoup(contenido_html, 'html.parser')
        tablas = soup.find_all('table')
        
        if len(tablas) >= 1:
            self._extraer_activos(tablas[0])
        if len(tablas) >= 2:
            self._extraer_amenazas(tablas[1])
        if len(tablas) >= 3:
            self._extraer_salvaguardas(tablas[2])
        
        # Limpieza post-carga: eliminar dependencias duplicadas
        for activo in self.activos:
            if len(activo['depende_de']) > 1:
                vistos = set()
                dependencias_limpias = []
                for dep_id, grado in activo['depende_de']:
                    if dep_id not in vistos:
                        vistos.add(dep_id)
                        dependencias_limpias.append((dep_id, grado))
                activo['depende_de'] = dependencias_limpias
    
    def _extraer_activos(self, tabla):
        """Extrae activos de la Tabla 1"""
        filas = tabla.find_all('tr')
        for fila in filas[1:]:
            celdas = fila.find_all(['td', 'th'])
            if len(celdas) < 6:
                continue
            
            activo = {
                'id': celdas[0].get_text().strip(),
                'nombre': celdas[1].get_text().strip(),
                'tipo': celdas[2].get_text().strip(),
                'valor': self._extraer_numero(celdas[3].get_text()),
                'depende_de': [],
                'grado': 1.0
            }
            
            # Dependencias (columna 4) y grado (columna 5)
            depende_text = celdas[4].get_text().strip() if len(celdas) > 4 else ""
            grado_text = celdas[5].get_text().strip() if len(celdas) > 5 else ""
            
            if depende_text and depende_text not in ['-', '']:
                ids_dep = [d.strip() for d in depende_text.split(',')]
                grado = self._extraer_numero(grado_text) if grado_text else 1.0
                
                # Eliminar duplicados en la misma línea
                vistos = set()
                for dep_id in ids_dep:
                    if dep_id and dep_id not in vistos:
                        vistos.add(dep_id)
                        activo['depende_de'].append((dep_id, grado))
            
            self.activos.append(activo)
    
    def _extraer_amenazas(self, tabla):
        """Extrae amenazas de la Tabla 2 SIN DUPLICADOS"""
        filas = tabla.find_all('tr')
        codigos_vistos = set()
        
        for fila in filas[1:]:
            celdas = fila.find_all(['td', 'th'])
            if len(celdas) < 4:
                continue
            
            codigo_raw = celdas[0].get_text().strip()
            codigo = re.sub(r'[\[\]]', '', codigo_raw)
            
            if codigo in codigos_vistos or not codigo:
                continue
            codigos_vistos.add(codigo)
            
            amenaza = {
                'codigo': codigo,
                'nombre': celdas[1].get_text().strip(),
                'frecuencia': self._extraer_numero(celdas[2].get_text()),
                'degradacion': self._extraer_numero(celdas[3].get_text()),
                'afecta': []
            }
            
            # Activos específicos que afecta (columna 5)
            if len(celdas) > 5:
                afecta_text = celdas[5].get_text().strip()
                if afecta_text and afecta_text != '-':
                    for a in afecta_text.split(','):
                        a_clean = a.strip()
                        if a_clean:
                            amenaza['afecta'].append(a_clean)
            
            self.amenazas.append(amenaza)
    
    def _extraer_salvaguardas(self, tabla):
        """Extrae salvaguardas de la Tabla 3 SIN DUPLICADOS"""
        filas = tabla.find_all('tr')
        codigos_vistos = set()
        
        for fila in filas[1:]:
            celdas = fila.find_all(['td', 'th'])
            if len(celdas) < 2:
                continue
            
            codigo_raw = celdas[0].get_text().strip()
            codigo = re.sub(r'[\[\]]', '', codigo_raw)
            
            if codigo in codigos_vistos or not codigo:
                continue
            codigos_vistos.add(codigo)
            
            ef_freq_raw = celdas[2].get_text().strip() if len(celdas) > 2 else ""
            ef_degr_raw = celdas[3].get_text().strip() if len(celdas) > 3 else ""
            
            salvaguarda = {
                'codigo': codigo,
                'nombre': celdas[1].get_text().strip(),
                'efectividad_frecuencia': ef_freq_raw,
                'efectividad_degradacion': ef_degr_raw,
                'amenazas_que_mitiga': []
            }
            
            # Amenazas que mitiga (columna 4)
            if len(celdas) > 4:
                mitiga_text = celdas[4].get_text().strip()
                if mitiga_text and mitiga_text != '-':
                    amenazas_mitiga = re.findall(r'[A-Z]\.[0-9]+', mitiga_text)
                    salvaguarda['amenazas_que_mitiga'] = amenazas_mitiga
            
            self.salvaguardas.append(salvaguarda)
    
    def _extraer_numero(self, texto: str) -> float:
        """Extrae un número de un texto"""
        if not texto or texto in ['-', '?', '']:
            return 0.0
        texto = str(texto).strip()
        
        # Porcentaje
        if '%' in texto:
            try:
                return float(texto.replace('%', '').replace(',', '.')) / 100.0
            except:
                pass
        
        # Eliminar € y espacios
        texto = re.sub(r'[€\s]', '', texto)
        texto = texto.replace(',', '.')
        
        try:
            return float(texto)
        except:
            nums = re.findall(r'\d+(?:\.\d+)?', texto)
            return float(nums[0]) if nums else 0.0
    
    def _convertir_efectividad(self, valor: str) -> float:
        """
        Convierte efectividad a tanto por uno.
        PRIORIDAD: Si contiene Lx (ej: L5, L4), usa ese valor.
        Si no, intenta porcentaje (ej: 98%, 88%).
        Si no, intenta decimal (ej: 0.98).
        """
        if not valor:
            return 0.0
        
        texto = str(valor).strip().upper()
        
        # 1. PRIORIDAD: Buscar código Lx (L5, L4, L3, L2, L1, L0)
        match_lx = re.search(r'L[0-5]', texto)
        if match_lx:
            lx = match_lx.group(0)
            return self.EFICACIAS.get(lx, 0.0)
        
        # 2. FALLBACK: Porcentaje (ej: "98%")
        if '%' in texto:
            try:
                return float(texto.replace('%', '')) / 100.0
            except:
                pass
        
        # 3. FALLBACK: Decimal (ej: "0.98")
        try:
            v = float(texto)
            return v if v <= 1 else v / 100.0
        except:
            return 0.0
    
    def _obtener_salvaguardas_para_amenaza(self, codigo_amenaza: str) -> List[Tuple[float, float]]:
        """Devuelve lista de (ef_f, ef_d) para una amenaza"""
        resultados = []
        for sal in self.salvaguardas:
            if codigo_amenaza in sal.get('amenazas_que_mitiga', []):
                ef_f = self._convertir_efectividad(sal.get('efectividad_frecuencia', ''))
                ef_d = self._convertir_efectividad(sal.get('efectividad_degradacion', ''))
                resultados.append((ef_f, ef_d))
        return resultados
    
    def calcular_riesgos(self):
        """Calcula todos los riesgos según MAGERIT Libro III"""
        
        # Mapa de activos
        activos_map = {a['id']: a for a in self.activos}
        
        # Mapa de amenazas por activo
        amenazas_por_activo = {}
        for am in self.amenazas:
            for id_afectado in am.get('afecta', []):
                id_limpio = id_afectado.strip()
                if id_limpio in activos_map:
                    amenazas_por_activo.setdefault(id_limpio, []).append(am)
        
        # Mapa de dependencias (destino -> lista de (origen, grado)) SIN DUPLICADOS
        dependencias_map = {}
        for a in self.activos:
            vistos = set()
            for dep_id, grado in a.get('depende_de', []):
                if dep_id not in vistos:
                    vistos.add(dep_id)
                    dependencias_map.setdefault(a['id'], []).append((dep_id, grado))
        
        # Calcular para cada activo
        for activo in self.activos:
            act_id = activo['id']
            valor = activo['valor']
            
            # ========== RIESGO DIRECTO ==========
            riesgo_directo = 0.0
            desglose_directo = []
            riesgo_residual_directo = 0.0
            desglose_residual_directo = []
            
            for am in amenazas_por_activo.get(act_id, []):
                freq = am['frecuencia']
                deg = am['degradacion']
                producto = valor * freq * deg
                riesgo_directo += producto
                desglose_directo.append(f"{valor:.0f} × {freq} × {deg} = {producto:.2f}")
                
                # Riesgo Residual con salvaguardas
                salvaguardas_aplicables = self._obtener_salvaguardas_para_amenaza(am['codigo'])
                
                if salvaguardas_aplicables:
                    factor_f = 1.0
                    factor_d = 1.0
                    factores_f_list = []
                    factores_d_list = []
                    
                    for (ef_f, ef_d) in salvaguardas_aplicables:
                        factor_f *= (1 - ef_f)
                        factor_d *= (1 - ef_d)
                        factores_f_list.append(f"(1-{ef_f:.2f})")
                        factores_d_list.append(f"(1-{ef_d:.2f})")
                    
                    freq_res = freq * factor_f
                    deg_res = deg * factor_d
                    producto_res = valor * freq_res * deg_res
                    riesgo_residual_directo += producto_res
                    
                    factores_f_str = " × ".join(factores_f_list)
                    factores_d_str = " × ".join(factores_d_list)
                    desglose_residual_directo.append(f"{valor:.0f} × ({freq} × {factores_f_str}) × ({deg} × {factores_d_str}) = {producto_res:.2f}")
                else:
                    riesgo_residual_directo += producto
                    desglose_residual_directo.append(f"{valor:.0f} × {freq} × {deg} = {producto:.2f} (sin salvaguardas)")
            
            # ========== RIESGO POR DEPENDENCIAS ==========
            riesgo_dependencias = 0.0
            desglose_dependencias = []
            riesgo_residual_dep = 0.0
            desglose_residual_dep = []
            
            # Usar set para evitar duplicar combinaciones (activo_origen + codigo_amenaza)
            procesadas = set()
            
            for (id_origen, grado) in dependencias_map.get(act_id, []):
                for am in amenazas_por_activo.get(id_origen, []):
                    clave = f"{id_origen}_{am['codigo']}"
                    if clave in procesadas:
                        continue
                    procesadas.add(clave)
                    
                    freq = am['frecuencia']
                    deg = am['degradacion']
                    
                    # VALOR DEL ACTIVO SUPERIOR × frecuencia_inferior × degradación_inferior × grado
                    producto = valor * freq * deg * grado
                    riesgo_dependencias += producto
                    desglose_dependencias.append(f"{valor:.0f} × {freq} × {deg} × {grado} = {producto:.2f}")
                    
                    # Riesgo Residual por dependencias
                    salvaguardas_aplicables = self._obtener_salvaguardas_para_amenaza(am['codigo'])
                    
                    if salvaguardas_aplicables:
                        factor_f = 1.0
                        factor_d = 1.0
                        factores_f_list = []
                        factores_d_list = []
                        
                        for (ef_f, ef_d) in salvaguardas_aplicables:
                            factor_f *= (1 - ef_f)
                            factor_d *= (1 - ef_d)
                            factores_f_list.append(f"(1-{ef_f:.2f})")
                            factores_d_list.append(f"(1-{ef_d:.2f})")
                        
                        freq_res = freq * factor_f
                        deg_res = deg * factor_d
                        producto_res = valor * freq_res * deg_res * grado
                        riesgo_residual_dep += producto_res
                        
                        factores_f_str = " × ".join(factores_f_list)
                        factores_d_str = " × ".join(factores_d_list)
                        desglose_residual_dep.append(f"{valor:.0f} × ({freq} × {factores_f_str}) × ({deg} × {factores_d_str}) × {grado} = {producto_res:.2f}")
                    else:
                        riesgo_residual_dep += producto
                        desglose_residual_dep.append(f"{valor:.0f} × {freq} × {deg} × {grado} = {producto:.2f} (sin salvaguardas)")
            
            riesgo_potencial = riesgo_directo + riesgo_dependencias
            riesgo_residual_total = riesgo_residual_directo + riesgo_residual_dep
            
            self.resultados[act_id] = {
                'nombre': activo['nombre'],
                'directo': round(riesgo_directo, 2),
                'desglose_directo': " + ".join(desglose_directo),
                'dependencias': round(riesgo_dependencias, 2),
                'desglose_dependencias': " + ".join(desglose_dependencias) if desglose_dependencias else "0",
                'potencial': round(riesgo_potencial, 2),
                'residual': round(riesgo_residual_total, 2),
                'desglose_residual': " + ".join(desglose_residual_directo + desglose_residual_dep) if (desglose_residual_directo or desglose_residual_dep) else "0"
            }
        
        return self.resultados
    
    def generar_txt_descargable(self) -> str:
        """Genera el contenido del archivo .txt"""
        if not self.resultados:
            self.calcular_riesgos()
        
        lineas = []
        lineas.append("=" * 100)
        lineas.append("ANÁLISIS DE RIESGOS SEGÚN MAGERIT LIBRO III")
        lineas.append(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lineas.append("=" * 100)
        lineas.append("")
        
        # Tabla resumen
        lineas.append("┌────────────┬──────────────────────────────┬────────────────┬────────────────┬────────────────┬────────────────┐")
        lineas.append("│ ID         │ Activo                       │ R. Directo (€) │ R. Depend. (€) │ R. Potencial   │ R. Residual    │")
        lineas.append("├────────────┼──────────────────────────────┼────────────────┼────────────────┼────────────────┼────────────────┤")
        
        for act_id, vals in self.resultados.items():
            nombre = vals['nombre'][:28] + ".." if len(vals['nombre']) > 28 else vals['nombre']
            lineas.append(f"│ {act_id:<10} │ {nombre:<28} │ {vals['directo']:14.2f} │ {vals['dependencias']:14.2f} │ {vals['potencial']:14.2f} │ {vals['residual']:14.2f} │")
        
        lineas.append("└────────────┴──────────────────────────────┴────────────────┴────────────────┴────────────────┴────────────────┘")
        lineas.append("")
        lineas.append("")
        
        # Desgloses detallados
        lineas.append("=" * 100)
        lineas.append("DESGLOSES DETALLADOS")
        lineas.append("=" * 100)
        
        for act_id, vals in self.resultados.items():
            lineas.append("")
            lineas.append(f"▶ ACTIVO: {act_id} - {vals['nombre']}")
            lineas.append("-" * 80)
            lineas.append(f"  Riesgo Directo: {vals['directo']} €")
            lineas.append(f"    Cálculo: {vals['desglose_directo']}")
            lineas.append("")
            lineas.append(f"  Riesgo por Dependencias: {vals['dependencias']} €")
            lineas.append(f"    Cálculo: {vals['desglose_dependencias']}")
            lineas.append("")
            lineas.append(f"  Riesgo Potencial TOTAL: {vals['potencial']} €")
            lineas.append(f"    Fórmula: Directo + Dependencias = {vals['directo']} + {vals['dependencias']}")
            lineas.append("")
            lineas.append(f"  Riesgo Residual: {vals['residual']} €")
            lineas.append(f"    Cálculo: {vals['desglose_residual']}")
            lineas.append("")
        
        # Nota metodológica
        lineas.append("")
        lineas.append("=" * 100)
        lineas.append("NOTA METODOLÓGICA (MAGERIT Libro III)")
        lineas.append("=" * 100)
        lineas.append("")
        lineas.append("1. Riesgo Directo = Valor_Activo × Frecuencia_Amenaza × Degradación_Amenaza")
        lineas.append("2. Riesgo por Dependencias = Valor_Activo_Superior × Frecuencia_Inferior × Degradación_Inferior × Grado")
        lineas.append("3. Riesgo Potencial = Riesgo Directo + Riesgo por Dependencias")
        lineas.append("4. Riesgo Residual = Valor × (Frecuencia × ∏(1-ef_f)) × (Degradación × ∏(1-ef_d))")
        lineas.append("")
        lineas.append("Escala de eficacias (Lx): L5=0.98, L4=0.88, L3=0.70, L2=0.50, L1=0.25, L0=0.00")
        
        return "\n".join(lineas)
    
    def guardar_txt(self, ruta_archivo: str = None) -> str:
        """Guarda el análisis en un archivo .txt"""
        if ruta_archivo is None:
            ruta_archivo = f"analisis_riesgos_magerit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(ruta_archivo, 'w', encoding='utf-8') as f:
            f.write(self.generar_txt_descargable())
        return ruta_archivo


def generar_descargable_riesgos(contenido_html: str, return_content: bool = False) -> str:
    """Función de conveniencia para generar el descargable"""
    calculador = CalculadorRiesgosMagerit()
    calculador.cargar_desde_html(contenido_html)
    calculador.calcular_riesgos()
    
    if return_content:
        return calculador.generar_txt_descargable()
    else:
        return calculador.guardar_txt()