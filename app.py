# app.py - Servidor Flask principal
 
import os
import time
import uuid
from flask import Flask, request, jsonify, render_template, make_response, Response
from datetime import datetime

from ia_prompt import analizar_con_ia, obtener_contexto_magerit
from pilar_xml import generar_xml_pilar
from rag import GestorRAG
from tablas_txt import generar_descargable_riesgos, CalculadorRiesgosMagerit  # ← AÑADIR ESTA LÍNEA

app = Flask(__name__)
app.secret_key = os.urandom(24)

TEMP_DIR = "./temp_docs/"
os.makedirs(TEMP_DIR, exist_ok=True)

cache_xml = {}
cache_txt = {}  # ← NUEVO: cache para archivos TXT
CACHE_TIMEOUT = 300

# Inicializar RAG
gestor_rag = GestorRAG()
gestor_rag.cargar_libros()


def limpiar_cache_expirado():
    ahora = time.time()
    expirados = [eid for eid, (_, timestamp) in cache_xml.items() if ahora - timestamp > CACHE_TIMEOUT]
    for eid in expirados:
        del cache_xml[eid]
    
    # Limpiar también cache de TXT
    expirados_txt = [eid for eid, (_, timestamp) in cache_txt.items() if ahora - timestamp > CACHE_TIMEOUT]
    for eid in expirados_txt:
        del cache_txt[eid]


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/ask', methods=['POST'])
def ask():
    pregunta = ""
    archivos_subidos = []
    organizacion = request.form.get('organizacion', 'ORGANIZACIÓN')
    autor = request.form.get('autor', 'ANALISTA')

    if request.is_json:
        data = request.get_json()
        pregunta = data.get('pregunta', '').strip()
        organizacion = data.get('organizacion', organizacion)
        autor = data.get('autor', autor)
    elif request.form:
        pregunta = request.form.get('pregunta', '').strip()
        organizacion = request.form.get('organizacion', organizacion)
        autor = request.form.get('autor', autor)
        if 'documentos' in request.files:
            for f in request.files.getlist('documentos'):
                if f and f.filename:
                    path = os.path.join(TEMP_DIR, f.filename)
                    f.save(path)
                    archivos_subidos.append(path)
        elif 'documento' in request.files:
            f = request.files['documento']
            if f and f.filename:
                path = os.path.join(TEMP_DIR, f.filename)
                f.save(path)
                archivos_subidos.append(path)

    if not pregunta:
        pregunta = "Realiza un análisis de riesgos para una empresa"

    limpiar_cache_expirado()

    try:
        contexto_magerit = obtener_contexto_magerit(pregunta)

        if archivos_subidos:
            from analizador_archivo import analizar_con_ia_archivos
            respuesta_html = analizar_con_ia_archivos(pregunta, archivos_subidos)
        else:
            from ia_prompt import analizar_con_ia
            respuesta_html = analizar_con_ia(
                pregunta=pregunta,
                contexto_magerit=contexto_magerit
            )

        # ============================================================
        # GENERAR XML PARA PILAR (ya existente)
        # ============================================================
        xml_id = None
        if '<table' in respuesta_html.lower():
            xml_content = generar_xml_pilar(
                respuesta_html,
                organizacion=organizacion,
                autor=autor,
                descripcion=pregunta[:200]
            )
            xml_data = xml_content.encode('utf-8')
            xml_id = str(uuid.uuid4())
            cache_xml[xml_id] = (xml_data, time.time())

        # ============================================================
        # GENERAR TXT CON CÁLCULOS REALES (NUEVO)
        # ============================================================
        txt_id = None
        try:
            # Crear calculador y procesar el HTML
            calculador = CalculadorRiesgosMagerit()
            calculador.cargar_desde_html(respuesta_html)
            calculador.calcular_riesgos()
            contenido_txt = calculador.generar_txt_descargable()
            
            # Guardar en cache
            txt_id = str(uuid.uuid4())
            cache_txt[txt_id] = (contenido_txt, time.time())
        except Exception as e:
            print(f"Error generando TXT: {e}")
            import traceback
            traceback.print_exc()

        # ============================================================
        # CONSTRUIR RESPUESTA CON BOTONES DE DESCARGA
        # ============================================================
        botones_descarga = ""
        
        if xml_id:
            botones_descarga += f'''
            <div style="display:inline-block; margin:5px;">
                <a href="/download_xml/{xml_id}" target="_blank" style="background:#4CAF50;color:white;padding:10px 20px;text-decoration:none;border-radius:5px;">📥 XML (PILAR RM)</a>
            </div>
            '''
        
        if txt_id:
            botones_descarga += f'''
            <div style="display:inline-block; margin:5px;">
                <a href="/download_txt/{txt_id}" target="_blank" style="background:#2196F3;color:white;padding:10px 20px;text-decoration:none;border-radius:5px;">📄 TXT (Cálculos MAGERIT)</a>
            </div>
            '''

        if botones_descarga:
            respuesta_html += f'''
            <div style="margin-top:30px;padding:20px;background:linear-gradient(135deg,#667eea,#764ba2);text-align:center;border-radius:10px;">
                <h3 style="color:white;margin-top:0;">📥 DESCARGAR ANÁLISIS</h3>
                {botones_descarga}
                <p style="color:white;margin-top:15px;font-size:12px;">✅ XML para PILAR RM | TXT con cálculos según MAGERIT Libro III</p>
            </div>
            '''

    except Exception as e:
        print(f"Error en /ask: {e}")
        import traceback
        traceback.print_exc()
        respuesta_html = f"<div style='background:#f8d7da;padding:20px;'><h3>Error: {str(e)}</h3></div>"

    # Limpiar archivos temporales
    for archivo in archivos_subidos:
        try:
            if os.path.exists(archivo):
                os.remove(archivo)
        except:
            pass

    return jsonify({'respuesta': respuesta_html})


@app.route('/download_xml/<xml_id>')
def download_xml(xml_id):
    limpiar_cache_expirado()
    if xml_id in cache_xml:
        xml_data, _ = cache_xml[xml_id]
        response = make_response(xml_data)
        response.headers['Content-Type'] = 'application/xml'
        response.headers['Content-Disposition'] = f'attachment; filename=analisis_riesgos_pilar_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xml'
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return response
    else:
        return "<html><body><h2>XML no encontrado</h2><p>El archivo ha expirado o no existe.</p></body></html>", 404


# ============================================================
# NUEVA RUTA PARA DESCARGAR TXT
# ============================================================
@app.route('/download_txt/<txt_id>')
def download_txt(txt_id):
    limpiar_cache_expirado()
    if txt_id in cache_txt:
        contenido_txt, _ = cache_txt[txt_id]
        response = make_response(contenido_txt)
        response.headers['Content-Type'] = 'text/plain; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename=analisis_riesgos_magerit_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return response
    else:
        return "<html><body><h2>TXT no encontrado</h2><p>El archivo ha expirado o no existe.</p></body></html>", 404


@app.route('/estado')
def estado():
    libros = []
    if os.path.exists("./libros/"):
        libros = [f for f in os.listdir("./libros/") if f.lower().endswith('.pdf')]
    return jsonify({
        'libros': libros,
        'sistema': 'magerit3_pilar'
    })


@app.route('/limpiar', methods=['POST'])
def limpiar_temporales():
    try:
        for f in os.listdir(TEMP_DIR):
            try:
                os.remove(os.path.join(TEMP_DIR, f))
            except:
                pass
        cache_xml.clear()
        cache_txt.clear()
        return jsonify({'status': 'ok'})
    except:
        return jsonify({'status': 'error'}), 500


if __name__ == '__main__':
    print("\n" + "="*60)
    print("MAGERIT 3 - ANÁLISIS DE RIESGOS CON PILAR RM")
    print("="*60)
    print("📌 ESTRUCTURA DE ARCHIVOS:")
    print("   - rag.py (RAG con búsqueda global)")
    print("   - pilar_xml.py (generación XML PILAR)")
    print("   - tablas_txt.py (generación TXT con cálculos MAGERIT)")
    print("   - ia_prompt.py (prompt y llamada Mistral)")
    print("   - analizador_archivo.py (procesa XML, HTML, PDF, DOCX, TXT)")
    print("   - app.py (servidor Flask)")
    print("="*60)
    print("📥 Descargas: XML (PILAR RM) + TXT (cálculos MAGERIT)")
    print("📄 Soporte: XML, HTML, PDF, DOCX, TXT")
    print("="*60)
    print("🚀 Servidor: http://localhost:8089")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=8089, debug=True, use_reloader=False)