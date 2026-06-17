
import os
import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict

LIBROS_DIR = "./libros/"
 
class GestorRAG:
    def __init__(self):
        self.textos = []           # Todos los fragmentos
        self.vectorizer = None
        self.tfidf_matrix = None
        
        self.libro_i = []
        self.libro_ii = []
        self.libro_iii = []
        self.ens_textos = []
        self.guia_ens_textos = [] 

        self.indices_amenazas = []
        self.indices_salvaguardas = []
    
    
    def obtener_valoracion_ens(self, nombre_activo: str, descripcion: str = "") -> Dict[str, int]:
        """
        Consulta el RAG (Guía ENS y ENS) para obtener valoración de las 5 dimensiones.
        Retorna valores numéricos del 1 (Muy Bajo) al 5 (Muy Alto).
        Si no encuentra, devuelve 2 (Bajo por defecto).
        """
        consulta = f"{nombre_activo} {descripcion} valoración confidencialidad integridad disponibilidad autenticidad trazabilidad"
        
        # Buscar en Guía ENS y ENS
        resultados = self.buscar_ens(consulta)
        if not resultados:
            resultados = self.buscar_guia_ens(consulta)
    
        
        # Valores por defecto: 2 = Bajo
        valoracion = {
            'confidencialidad': 2,
            'integridad': 2,
            'disponibilidad': 2,
            'autenticidad': 2,
            'trazabilidad': 2
        }
        
        # Mapeo de textos a números (1-5) - INCLUYE MÚLTIPLES SINÓNIMOS
        mapa_niveles = {
            # Nivel 1: Muy Bajo / Despreciable / Inexistente / Nulo
            1: ['muy bajo', 'muy bajo', 'despreciable', 'inexistente', 'nulo', 'insignificante', 'nada', '0'],
            
            # Nivel 2: Bajo / Limitado / Pequeño
            2: ['bajo', 'limitado', 'pequeño', 'menor', 'poco', 'leve', 'mínimo'],
            
            # Nivel 3: Medio / Normal / Moderado / Aceptable
            3: ['medio', 'moderado', 'normal', 'aceptable', 'estándar', 'regular', 'suficiente'],
            
            # Nivel 4: Alto / Grande / Significativo
            4: ['alto', 'grande', 'significativo', 'importante', 'elevado', 'considerable', 'grave'],
            
            # Nivel 5: Muy Alto / Crítico / Extremo / Inaceptable / Catastrófico
            5: ['muy alto', 'crítico', 'extremo', 'inaceptable', 'catastrófico', 'máximo', 'total', 'absoluto', 'devastador']
        }
        
        # Extraer valoraciones de los fragmentos encontrados
        for r in resultados[:5]:
            texto = r['texto'].lower()
            
            # Confidencialidad
            if 'confidencialidad' in texto:
                for nivel, palabras in mapa_niveles.items():
                    for palabra in palabras:
                        if palabra in texto:
                            valoracion['confidencialidad'] = nivel
                            break
                    if valoracion['confidencialidad'] != 2:
                        break
            
            # Integridad
            if 'integridad' in texto:
                for nivel, palabras in mapa_niveles.items():
                    for palabra in palabras:
                        if palabra in texto:
                            valoracion['integridad'] = nivel
                            break
                    if valoracion['integridad'] != 2:
                        break
            
            # Disponibilidad
            if 'disponibilidad' in texto:
                for nivel, palabras in mapa_niveles.items():
                    for palabra in palabras:
                        if palabra in texto:
                            valoracion['disponibilidad'] = nivel
                            break
                    if valoracion['disponibilidad'] != 2:
                        break
            
            # Autenticidad
            if 'autenticidad' in texto:
                for nivel, palabras in mapa_niveles.items():
                    for palabra in palabras:
                        if palabra in texto:
                            valoracion['autenticidad'] = nivel
                            break
                    if valoracion['autenticidad'] != 2:
                        break
            
            # Trazabilidad
            if 'trazabilidad' in texto:
                for nivel, palabras in mapa_niveles.items():
                    for palabra in palabras:
                        if palabra in texto:
                            valoracion['trazabilidad'] = nivel
                            break
                    if valoracion['trazabilidad'] != 2:
                        break
        
        return valoracion
     

    
    def buscar_guia_ens(self, consulta: str) -> List[Dict]:
        """Busca específicamente en la Guía CCN-STIC 800"""
        return self.buscar(consulta, libro_filtro="GUIA_ENS")
    
    def buscar_ens(self, consulta: str) -> List[Dict]:
        """Busca en los documentos del ENS"""
        return self.buscar(consulta, libro_filtro="ENS")
        
    def cargar_libros(self):
        """Carga todos los PDFs y extrae fragmentos por página"""
        if not os.path.exists(LIBROS_DIR):
            os.makedirs(LIBROS_DIR, exist_ok=True)
            return False
        
        archivos = [f for f in os.listdir(LIBROS_DIR) if f.lower().endswith('.pdf')]
        if not archivos:
            print("⚠️ No hay PDFs en la carpeta ./libros/")
            return False
        
        print(f"\n📚 Cargando {len(archivos)} PDFs...")
        
        self.textos = []
        self.indices_amenazas = []
        self.indices_salvaguardas = []
        self.libro_i = []
        self.libro_ii = []
        self.libro_iii = []
        self.ens_textos = []
        self.guia_ens_textos = []  # NUEVO: resetear lista
        
        for archivo in archivos:
            ruta = os.path.join(LIBROS_DIR, archivo)
            
            nombre = archivo.lower()
            
            # NUEVA DETECCIÓN: Separar ENS de Guía CCN-STIC 800
            if 'ens' in nombre and 'stic' not in nombre and '800' not in nombre:
                libro_tipo = "ENS"
                print(f"   📑 {archivo} -> ENS")
            elif 'stic' in nombre or '800' in nombre or 'guia' in nombre:
                libro_tipo = "GUIA_ENS"
                print(f"   📖 {archivo} -> GUÍA CCN-STIC 800")
            elif '2' in nombre or 'ii' in nombre:
                libro_tipo = "LIBRO_II"
                print(f"   📘 {archivo} -> LIBRO II")
            elif '3' in nombre or 'iii' in nombre:
                libro_tipo = "LIBRO_III"
                print(f"   📙 {archivo} -> LIBRO III")
            else:
                libro_tipo = "LIBRO_I"
                print(f"   📗 {archivo} -> LIBRO I")
            
            paginas_ok = 0
            
            import pdfplumber
            with pdfplumber.open(ruta) as pdf:
                for num_pag, pagina in enumerate(pdf.pages):
                    texto_raw = pagina.extract_text()
                    if texto_raw and len(texto_raw) > 100:
                        pagina_actual = num_pag + 1
                        
                        if libro_tipo == "LIBRO_II":
                            
                            # ========== AMENAZAS: páginas 23-49 ==========
                            if 23 <= pagina_actual <= 49:
                                lineas = texto_raw.split('\n')
                                i = 0
                                while i < len(lineas):
                                    linea = lineas[i].strip()
                                    
                                    match_codigo = re.search(r'^\[([NEIA])\.(\d+)\]', linea)
                                    if match_codigo:
                                        codigo = f"[{match_codigo.group(1)}.{match_codigo.group(2)}]"
                                        
                                        # Saltar líneas de índice (ej: "5.4.1. [A.3]")
                                        if re.match(r'^\d+\.\d+\.\d+\.\s*\[', linea):
                                            i += 1
                                            continue
                                        
                                        nombre_amenaza = re.sub(r'^\[[NEIA]\.\d+\]\s*', '', linea)
                                        nombre_amenaza = re.sub(r'^\d+\.\d+\.\d+\.\s*', '', nombre_amenaza)
                                        nombre_amenaza = nombre_amenaza.strip()
                                        
                                        # Saltar si todavía tiene formato de índice
                                        if re.match(r'^\d+\.\d+\.\d+\.', nombre_amenaza):
                                            i += 1
                                            continue
                                        
                                        if len(nombre_amenaza) < 5:
                                            i += 1
                                            continue
                                        
                                        tipos_activos = set()
                                        dimensiones = set()
                                        descripcion = ""
                                        
                                        j = i + 1
                                        while j < len(lineas) and j < i + 35:
                                            linea_sig = lineas[j].strip()
                                            
                                            if 'Tipos de activos:' in linea_sig:
                                                k = j + 1
                                                while k < len(lineas) and k < j + 12:
                                                    tipo_linea = lineas[k].strip()
                                                    if tipo_linea.startswith('•'):
                                                        match_tipo = re.search(r'\[([A-Za-z]+)\]', tipo_linea)
                                                        if match_tipo:
                                                            tipo = match_tipo.group(1)
                                                            tipo = re.sub(r'\..*$', '', tipo)
                                                            if tipo in ['D', 'K', 'S', 'SW', 'HW', 'COM', 'Media', 'AUX', 'L', 'P']:
                                                                tipos_activos.add(tipo)
                                                    elif 'Dimensiones:' in tipo_linea or 'Descripción:' in tipo_linea:
                                                        break
                                                    k += 1
                                            
                                            if 'Dimensiones:' in linea_sig:
                                                k = j + 1
                                                while k < len(lineas) and k < j + 10:
                                                    dim_linea = lineas[k].strip()
                                                    match_dim = re.search(r'\[([DIC])\]', dim_linea)
                                                    if match_dim:
                                                        dimensiones.add(match_dim.group(1))
                                                    elif 'Descripción:' in dim_linea or 'Origen:' in dim_linea:
                                                        break
                                                    k += 1
                                            
                                            if 'Descripción:' in linea_sig:
                                                k = j + 1
                                                while k < len(lineas) and k < j + 15:
                                                    desc_linea = lineas[k].strip()
                                                    if desc_linea and not desc_linea.startswith('•') and not 'Origen:' in desc_linea and not 'Ver:' in desc_linea and len(desc_linea) > 10:
                                                        descripcion += " " + desc_linea
                                                    elif 'Origen:' in desc_linea or 'Ver:' in desc_linea:
                                                        break
                                                    k += 1
                                                descripcion = descripcion.strip()[:400]
                                            
                                            if 'Origen:' in linea_sig:
                                                break
                                            
                                            j += 1
                                        
                                        codigo_key = f"{codigo}_{pagina_actual}"
                                        if not hasattr(self, '_codigos_procesados'):
                                            self._codigos_procesados = set()
                                        
                                        if codigo_key not in self._codigos_procesados:
                                            self._codigos_procesados.add(codigo_key)
                                            
                                            print(f"   🔥 {codigo} - {nombre_amenaza} - {tipos_activos} - {dimensiones}")
                                            
                                            item = {
                                                'texto': f"{codigo} {nombre_amenaza}\nDescripción: {descripcion}",
                                                'fuente': archivo,
                                                'pagina': pagina_actual,
                                                'libro': libro_tipo,
                                                'codigo': codigo,
                                                'nombre': nombre_amenaza,
                                                'tipos_activos': sorted(list(tipos_activos)),
                                                'dimensiones': sorted(list(dimensiones)),
                                                'descripcion': descripcion
                                            }
                                            idx_global = len(self.textos)
                                            self.textos.append(item)
                                            self.libro_ii.append(item)
                                            self.indices_amenazas.append(idx_global)
                                    
                                    i += 1
                            
                            # ========== SALVAGUARDAS: páginas 51-55 ==========
                            elif 51 <= pagina_actual <= 55:
                                lineas = texto_raw.split('\n')
                                for i, linea in enumerate(lineas):
                                    linea = linea.strip()
                                    if not linea or re.match(r'^\d+$', linea):
                                        continue
                                    
                                    match_salv = re.search(r'^([A-Z]{1,3}\.[A-Za-z0-9.]+)\s+(.+)$', linea)
                                    if match_salv:
                                        codigo = match_salv.group(1)
                                        nombre_salvaguarda = match_salv.group(2).strip()
                                        nombre_salvaguarda = re.sub(r'\s+', ' ', nombre_salvaguarda)
                                        
                                        if nombre_salvaguarda and len(nombre_salvaguarda) > 3 and len(codigo) < 20:
                                            print(f"   🛡️ {codigo} - {nombre_salvaguarda}")
                                            
                                            item = {
                                                'texto': f"{codigo} {nombre_salvaguarda}",
                                                'fuente': archivo,
                                                'pagina': pagina_actual,
                                                'libro': libro_tipo,
                                                'codigo': codigo,
                                                'nombre': nombre_salvaguarda
                                            }
                                            idx_global = len(self.textos)
                                            self.textos.append(item)
                                            self.libro_ii.append(item)
                                            self.indices_salvaguardas.append(idx_global)
                            
                            else:
                                item = {
                                    'texto': texto_raw[:5000],
                                    'fuente': archivo,
                                    'pagina': pagina_actual,
                                    'libro': libro_tipo
                                }
                                idx_global = len(self.textos)
                                self.textos.append(item)
                                self.libro_ii.append(item)
                        
                        else:
                            item = {
                                'texto': texto_raw[:5000],
                                'fuente': archivo,
                                'pagina': pagina_actual,
                                'libro': libro_tipo
                            }
                            idx_global = len(self.textos)
                            self.textos.append(item)
                            
                            if libro_tipo == "LIBRO_I":
                                self.libro_i.append(item)
                            elif libro_tipo == "LIBRO_III":
                                self.libro_iii.append(item)
                            elif libro_tipo == "ENS":
                                self.ens_textos.append(item)
                            elif libro_tipo == "GUIA_ENS":  # NUEVO: guardar en su lista
                                self.guia_ens_textos.append(item)
                        
                        paginas_ok += 1
            
            print(f"      ✅ {paginas_ok} páginas")
        
        if hasattr(self, '_codigos_procesados'):
            delattr(self, '_codigos_procesados')
        
        print(f"\n📊 TOTAL: {len(self.textos)} fragmentos")
        print(f"   📗 Libro I: {len(self.libro_i)}")
        print(f"   📘 Libro II: {len(self.libro_ii)}")
        print(f"      🔥 Amenazas (p23-49): {len(self.indices_amenazas)}")
        print(f"      🛡️ Salvaguardas (p51-55): {len(self.indices_salvaguardas)}")
        print(f"   📙 Libro III: {len(self.libro_iii)}")
        print(f"   📑 ENS: {len(self.ens_textos)}")
        print(f"   📖 GUÍA CCN-STIC 800: {len(self.guia_ens_textos)}")  # NUEVO: mostrar cuántos fragmentos se cargaron
        
        if self.textos:
            self._crear_indice()
            return True
        return False
    
        
 
    def _crear_indice(self):
        """Crea índice TF-IDF SIN límite de features (usa todo el vocabulario)"""
        textos_limpios = [t['texto'] for t in self.textos]
        # SIN max_features - que coja TODO el vocabulario
        self.vectorizer = TfidfVectorizer()
        self.tfidf_matrix = self.vectorizer.fit_transform(textos_limpios)
        print(f"📊 Índice TF-IDF creado con {len(textos_limpios)} documentos")
        print(f"   📚 Vocabulario: {len(self.vectorizer.get_feature_names_out())} términos")
    
    def buscar(self, consulta: str, libro_filtro: str = None) -> List[Dict]:
        """
        Búsqueda GLOBAL en todos los libros.
        Retorna TODOS los resultados con similitud > 0, ordenados por relevancia.
        SIN top_k limitante.
        """
        if not self.textos or self.vectorizer is None:
            return []
        
        consulta_vec = self.vectorizer.transform([consulta.lower()])
        similitudes = cosine_similarity(consulta_vec, self.tfidf_matrix).flatten()
        
        # Obtener todos los índices
        indices = list(range(len(self.textos)))
        
        if libro_filtro:
            indices = [i for i in indices if self.textos[i]['libro'] == libro_filtro]
        
        # Crear pares y ordenar por similitud (mayor a menor)
        pares = [(i, similitudes[i]) for i in indices if similitudes[i] > 0]
        pares.sort(key=lambda x: x[1], reverse=True)
        
        resultados = []
        for idx, sim in pares:
            item = self.textos[idx]
            resultados.append({
                'texto': item['texto'],
                'fuente': item['fuente'],
                'pagina': item['pagina'],
                'libro': item['libro'],
                'similitud': sim
            })
        
        return resultados
    
    def buscar_activos(self, dominio: str = "") -> List[Dict]:
        """
        Busca activos en TODO el corpus (Libros I, II, III, ENS)
        Útil cuando el usuario no especifica activos.
        """
        consulta = f"{dominio} activo servicio sistema aplicación hardware software datos información"
        return self.buscar(consulta, libro_filtro=None)
    
    def buscar_amenazas(self, contexto: str) -> List[Dict]:
        """
        Busca amenazas SOLO en páginas 23-49 del Libro II.
        Retorna TODOS los resultados con TODOS los campos.
        """
        if not self.indices_amenazas or self.vectorizer is None:
            return []
        
        consulta_vec = self.vectorizer.transform([contexto.lower()])
        similitudes = cosine_similarity(consulta_vec, self.tfidf_matrix).flatten()
        
        pares = [(idx, similitudes[idx]) for idx in self.indices_amenazas if similitudes[idx] > 0]
        pares.sort(key=lambda x: x[1], reverse=True)
        
        resultados = []
        for idx, sim in pares:
            item = self.textos[idx]  # ← Esto tiene TODOS los campos
            resultados.append({
                'texto': item['texto'],
                'fuente': item['fuente'],
                'pagina': item['pagina'],
                'codigo': item.get('codigo', ''),
                'nombre': item.get('nombre', ''),           # ← AÑADIR
                'tipos_activos': item.get('tipos_activos', []),  # ← AÑADIR
                'dimensiones': item.get('dimensiones', []),      # ← AÑADIR
                'descripcion': item.get('descripcion', ''),
                'similitud': sim
            })
        
        return resultados
    
    def buscar_salvaguardas(self, contexto: str) -> List[Dict]:
        """
        Busca salvaguardas SOLO en páginas 51-57 del Libro II.
        Retorna TODOS los resultados relevantes.
        """
        if not self.indices_salvaguardas or self.vectorizer is None:
            return []
        
        consulta_vec = self.vectorizer.transform([contexto.lower()])
        similitudes = cosine_similarity(consulta_vec, self.tfidf_matrix).flatten()
        
        pares = [(idx, similitudes[idx]) for idx in self.indices_salvaguardas if similitudes[idx] > 0]
        pares.sort(key=lambda x: x[1], reverse=True)
        
        resultados = []
        for idx, sim in pares:
            item = self.textos[idx]
            codigo = self._extraer_codigo_salvaguarda(item['texto'])
            resultados.append({
                'texto': item['texto'],
                'fuente': item['fuente'],
                'pagina': item['pagina'],
                'codigo': codigo,
                'nombre': item.get('nombre', ''),
                'similitud': sim
            })
        
        return resultados
    
    def buscar_ens(self, consulta: str) -> List[Dict]:
        """Busca en los documentos del ENS"""
        return self.buscar(consulta, libro_filtro="ENS")
    
    def existe_codigo_amenaza(self, codigo: str) -> bool:
        """Verifica si un código de amenaza existe en el catálogo"""
        if not self.indices_amenazas:
            return False
        for idx in self.indices_amenazas:
            texto = self.textos[idx]['texto']
            if codigo in texto:
                return True
        return False
    
    def existe_codigo_salvaguarda(self, codigo: str) -> bool:
        """Verifica si un código de salvaguarda existe en el catálogo"""
        if not self.indices_salvaguardas:
            return False
        for idx in self.indices_salvaguardas:
            texto = self.textos[idx]['texto']
            if codigo in texto:
                return True
        return False
    
    def _extraer_codigo_amenaza(self, texto: str) -> str:
        """Extrae código de amenaza tipo [N.XXX] o [N.XXX-XXX]"""
        match = re.search(r'\[([A-Z]\.\d+[-\d]*)\]', texto)
        return match.group(1) if match else ""
    
    def _extraer_codigo_salvaguarda(self, texto: str) -> str:
        """Extrae código de salvaguarda"""
        match = re.search(r'([A-Z]{1,3}\.[A-Z]{1,4})', texto)
        if match:
            return match.group(1)
        match = re.search(r'(\d+\.\d+)\.', texto)
        return match.group(1) if match else ""
 