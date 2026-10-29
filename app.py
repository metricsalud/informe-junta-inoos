import os
import sys
import site
import time
import json
import traceback
import socket
import argparse
import webbrowser
import unicodedata
import re

# Asegurar que librerías en .venv estén disponibles
venv_site = os.path.join(os.path.dirname(__file__), '.venv', 'Lib', 'site-packages')
if os.path.exists(venv_site):
    site.addsitedir(venv_site)

import json
from flask import Flask, render_template, request, jsonify, send_file, Response
from data_engine import ClinicalDataEngine
from dashboard_engine import DashboardEngine, sanitize_for_json
from generador_informe_junta import GeneradorInformeJunta

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200 MB
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

DEFAULT_EXCEL = "BD pacientes Inoos SEPTIEMBRE 2026 .xlsx"
DEFAULT_TEMPLATE = "template_junta.pptx"
DEFAULT_OUTPUT = "Informe_Junta_Directiva_Generado.pptx"

MESES_NOMBRES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']

def detectar_mes_ano_archivo(nombre_archivo):
    """Detecta el mes y año analizado a partir del nombre del archivo Excel."""
    nombre_limpio = unicodedata.normalize('NFKD', str(nombre_archivo)).encode('ASCII', 'ignore').decode('ASCII').upper()
    mes_detectado = None
    for m in MESES_NOMBRES:
        m_ascii = unicodedata.normalize('NFKD', m).encode('ASCII', 'ignore').decode('ASCII').upper()
        if m_ascii in nombre_limpio:
            mes_detectado = m
            break
            
    match_ano = re.search(r'\b(202[0-9]|203[0-9])\b', nombre_limpio)
    ano_detectado = int(match_ano.group(1)) if match_ano else 2026
    
    return mes_detectado or "Septiembre", ano_detectado

# Estado de la base de datos activa
mes_init, ano_init = detectar_mes_ano_archivo(DEFAULT_EXCEL)
CURRENT_ACTIVE = {
    'filepath': os.path.abspath(DEFAULT_EXCEL) if os.path.exists(DEFAULT_EXCEL) else DEFAULT_EXCEL,
    'filename': DEFAULT_EXCEL,
    'mes': mes_init,
    'ano': ano_init
}

# Cache de motor para no recargar Excel en cada consulta si no cambia
ENGINE_CACHE = {}

def get_engine(excel_path=None, mes_corte="Septiembre", ano_corte=2026):
    if not excel_path:
        excel_path = CURRENT_ACTIVE['filepath']
    if not os.path.isabs(excel_path):
        p_uploads = os.path.join(app.config['UPLOAD_FOLDER'], excel_path)
        p_root = os.path.join(os.path.dirname(__file__), excel_path)
        if os.path.exists(p_uploads):
            excel_path = p_uploads
        elif os.path.exists(p_root):
            excel_path = p_root
            
    key = f"{excel_path}_{mes_corte}_{ano_corte}"
    if key not in ENGINE_CACHE:
        if os.path.exists(excel_path):
            ENGINE_CACHE[key] = ClinicalDataEngine(excel_path, mes_corte=mes_corte, ano_corte=ano_corte)
        else:
            return None
    return ENGINE_CACHE[key]

@app.route('/')
def index():
    return render_template('index.html', default_excel=CURRENT_ACTIVE['filename'])

@app.route('/api/files', methods=['GET'])
def list_files():
    """Lista los archivos de base de datos disponibles para alternar al instante."""
    files = []
    # Archivo base predeterminado
    if os.path.exists(DEFAULT_EXCEL):
        mes_d, ano_d = detectar_mes_ano_archivo(DEFAULT_EXCEL)
        files.append({
            'filename': DEFAULT_EXCEL,
            'filepath': os.path.abspath(DEFAULT_EXCEL),
            'mes': mes_d,
            'ano': ano_d,
            'is_default': True
        })
    # Archivos en uploads/
    uploads_dir = app.config['UPLOAD_FOLDER']
    if os.path.exists(uploads_dir):
        for f in sorted(os.listdir(uploads_dir), reverse=True):
            if f.endswith(('.xlsx', '.xlsm')) and not f.startswith('~$'):
                fpath = os.path.join(uploads_dir, f)
                mes_d, ano_d = detectar_mes_ano_archivo(f)
                files.append({
                    'filename': f,
                    'filepath': os.path.abspath(fpath),
                    'mes': mes_d,
                    'ano': ano_d,
                    'is_default': False
                })
    return jsonify({
        'status': 'success',
        'active': CURRENT_ACTIVE,
        'files': files
    })

@app.route('/api/set_active_file', methods=['POST'])
def set_active_file():
    """Permite seleccionar un archivo ya cargado para reflejarlo en pantalla."""
    data = request.json or {}
    filepath = data.get('filepath') or data.get('filename')
    if not filepath:
        return jsonify({"error": "Ruta no especificada"}), 400
        
    if not os.path.isabs(filepath):
        p1 = os.path.join(app.config['UPLOAD_FOLDER'], filepath)
        p2 = os.path.join(os.path.dirname(__file__), filepath)
        if os.path.exists(p1):
            filepath = p1
        elif os.path.exists(p2):
            filepath = p2
            
    if not os.path.exists(filepath):
        return jsonify({"error": f"Archivo no existe: {filepath}"}), 404
        
    filename = os.path.basename(filepath)
    mes_det, ano_det = detectar_mes_ano_archivo(filename)
    CURRENT_ACTIVE['filepath'] = filepath
    CURRENT_ACTIVE['filename'] = filename
    CURRENT_ACTIVE['mes'] = mes_det
    CURRENT_ACTIVE['ano'] = ano_det
    
    try:
        engine = get_engine(filepath, mes_det, ano_det)
        return jsonify({
            "status": "success",
            "active": CURRENT_ACTIVE,
            "total_registros": len(engine.df) if engine else 0
        })
    except Exception as e:
        return jsonify({"error": f"Error al indexar archivo: {str(e)}"}), 500

@app.route('/api/kpis', methods=['GET'])
def get_kpis():
    excel_file = request.args.get('excel', CURRENT_ACTIVE['filepath'])
    if not os.path.isabs(excel_file):
        p1 = os.path.join(app.config['UPLOAD_FOLDER'], excel_file)
        p2 = os.path.join(os.path.dirname(__file__), excel_file)
        if os.path.exists(p1):
            excel_file = p1
        elif os.path.exists(p2):
            excel_file = p2
        else:
            excel_file = os.path.join(os.path.dirname(__file__), excel_file)
        
    mes = request.args.get('mes', CURRENT_ACTIVE['mes'])
    ano = int(request.args.get('ano', CURRENT_ACTIVE['ano']))
    
    engine = get_engine(excel_file, mes, ano)
    if not engine:
        return jsonify({"error": f"Archivo Excel no encontrado: {excel_file}"}), 404
        
    df = engine.df
    total_registros = len(df)
    
    # Distribución por EPS
    eps_counts = df['EPS_CANONICA'].value_counts().to_dict()
    
    # Priorizados vs No Priorizados
    prio_counts = {
        "Priorizados": int(df['ES_PRIORIZADO'].sum()),
        "No Priorizados": int((~df['ES_PRIORIZADO']).sum())
    }
    
    # Top 5 tumores generales
    top_tumores = df['AGRUPADOR'].value_counts().head(5).to_dict()
    
    # Denominadores
    poblaciones = engine.poblaciones
    
    return jsonify({
        "status": "success",
        "active_filename": os.path.basename(excel_file),
        "active_filepath": excel_file,
        "mes": mes,
        "ano": ano,
        "corte_display": f"Corte: {mes} {ano}",
        "total_registros": total_registros,
        "duplicados_preservados": True,
        "eps_distribucion": eps_counts,
        "prioridad_distribucion": prio_counts,
        "top_tumores": top_tumores,
        "poblaciones": poblaciones
    })

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No se envió ningún archivo"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Nombre de archivo vacío"}), 400
        
    if not file.filename.endswith(('.xlsx', '.xlsm')):
        return jsonify({"error": "El archivo debe ser un Excel (.xlsx o .xlsm)"}), 400
        
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(save_path)
    
    # Invalidar cache anterior si existía
    keys_to_del = [k for k in ENGINE_CACHE if save_path in k]
    for k in keys_to_del:
        del ENGINE_CACHE[k]
        
    mes_det, ano_det = detectar_mes_ano_archivo(file.filename)
    CURRENT_ACTIVE['filepath'] = save_path
    CURRENT_ACTIVE['filename'] = file.filename
    CURRENT_ACTIVE['mes'] = mes_det
    CURRENT_ACTIVE['ano'] = ano_det
        
    try:
        engine = get_engine(save_path, mes_det, ano_det)
        return jsonify({
            "status": "success",
            "message": "Archivo cargado e indexado correctamente",
            "filename": file.filename,
            "filepath": save_path,
            "detected_mes": mes_det,
            "detected_ano": ano_det,
            "corte_display": f"Corte: {mes_det} {ano_det}",
            "total_registros": len(engine.df)
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Error al procesar el Excel: {str(e)}"}), 500

@app.route('/api/generate', methods=['POST'])
def generate_report():
    data = request.json or {}
    mes = data.get('mes', CURRENT_ACTIVE['mes'])
    ano = int(data.get('ano', CURRENT_ACTIVE['ano']))
    excel_path = data.get('excel_path', CURRENT_ACTIVE['filepath'])
    
    if not os.path.isabs(excel_path):
        p1 = os.path.join(app.config['UPLOAD_FOLDER'], excel_path)
        p2 = os.path.join(os.path.dirname(__file__), excel_path)
        if os.path.exists(p1):
            excel_path = p1
        elif os.path.exists(p2):
            excel_path = p2
        
    if not os.path.exists(excel_path):
        return jsonify({"error": f"Base de datos no encontrada: {excel_path}"}), 404
        
    template_path = os.path.join(os.path.dirname(__file__), DEFAULT_TEMPLATE)
    if not os.path.exists(template_path):
        return jsonify({"error": f"Plantilla maestra no encontrada: {template_path}"}), 404
        
    out_name = f"Informe_Junta_Directiva_{mes}_{ano}.pptx"
    output_path = os.path.join(os.path.dirname(__file__), out_name)
    
    start_time = time.time()
    try:
        generador = GeneradorInformeJunta(
            excel_path=excel_path,
            template_path=template_path,
            output_path=output_path,
            mes_corte=mes,
            ano_corte=ano
        )
        generador.generar()
        duration = round(time.time() - start_time, 2)
        size_mb = round(os.path.getsize(output_path) / (1024 * 1024), 2)
        
        return jsonify({
            "status": "success",
            "message": "Informe de Junta Directiva generado con éxito",
            "output_filename": out_name,
            "duration_seconds": duration,
            "file_size_mb": size_mb,
            "slides_count": len(generador.prs.slides)
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Fallo en la generación: {str(e)}"}), 500

@app.route('/api/download/<filename>')
def download_file(filename):
    file_path = os.path.join(os.path.dirname(__file__), filename)
    if not os.path.exists(file_path):
        file_path = os.path.join(os.path.dirname(__file__), DEFAULT_OUTPUT)
    if not os.path.exists(file_path):
        return "Archivo no encontrado", 404
        
    return send_file(file_path, as_attachment=True, download_name=filename)

@app.route('/api/test', methods=['GET'])
def run_tests():
    from test_verificacion import VerificadorConcordancia
    try:
        verificador = VerificadorConcordancia(
            excel_path=CURRENT_ACTIVE['filepath'],
            pptx_ref_path="INFORME JUNTA SEPTIEMBRE 2026 V3.pptx",
            pptx_gen_path=DEFAULT_OUTPUT
        )
        res = verificador.ejecutar_todas()
        return jsonify({
            "status": "success",
            "total_pruebas": res["total_pruebas"],
            "exitosas": res["exitosas"],
            "discrepancias": res["discrepancias"],
            "porcentaje_concordancia": res["porcentaje_concordancia"]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================================
# RUTAS DEL TABLERO DE MANDO (DASHBOARD)
# ==========================================

DASHBOARD_ENGINE_CACHE = {}

def get_dashboard_engine(excel_path=None):
    if not excel_path:
        excel_path = CURRENT_ACTIVE['filepath']
    if not os.path.isabs(excel_path):
        p1 = os.path.join(app.config['UPLOAD_FOLDER'], excel_path)
        p2 = os.path.join(os.path.dirname(__file__), excel_path)
        if os.path.exists(p1): excel_path = p1
        elif os.path.exists(p2): excel_path = p2
        else: excel_path = os.path.join(os.path.dirname(__file__), excel_path)
        
    engine = get_engine(excel_path)
    if not engine:
        return None
    mtime = os.path.getmtime(excel_path) if os.path.exists(excel_path) else 0
    cache_key = f"{excel_path}_{mtime}"
    if cache_key not in DASHBOARD_ENGINE_CACHE:
        DASHBOARD_ENGINE_CACHE[cache_key] = DashboardEngine(engine)
    return DASHBOARD_ENGINE_CACHE[cache_key]

@app.route('/dashboard')
def dashboard_view():
    return render_template('dashboard.html', default_excel=CURRENT_ACTIVE['filename'])

@app.route('/api/dashboard/filters', methods=['GET'])
def get_dashboard_filters():
    excel_path = request.args.get('excel', CURRENT_ACTIVE['filepath'])
    dash = get_dashboard_engine(excel_path)
    if not dash:
        return jsonify({"error": "Motor de datos no disponible para este archivo"}), 404
    opts = dash.get_filter_options()
    opts['active_filename'] = os.path.basename(excel_path)
    clean_payload = sanitize_for_json({'status': 'success', 'options': opts})
    return Response(json.dumps(clean_payload, ensure_ascii=False, allow_nan=False), mimetype='application/json')

@app.route('/api/dashboard/data', methods=['POST'])
def get_dashboard_data():
    body = request.json or {}
    excel_path = body.get('excel') or CURRENT_ACTIVE['filepath']
    dash = get_dashboard_engine(excel_path)
    if not dash:
        return jsonify({"error": "Motor de datos no disponible para este archivo"}), 404
    filters = body.get('filters', {})
    data = dash.calculate_dashboard_metrics(filters)
    data['active_filename'] = os.path.basename(excel_path)
    
    # Sanitización estricta para garantizar cumplimiento RFC-8259 sin tokens NaN
    clean_data = sanitize_for_json(data)
    json_bytes = json.dumps(clean_data, ensure_ascii=False, allow_nan=False)
    return Response(json_bytes, mimetype='application/json')

@app.route('/api/dashboard/export_csv', methods=['POST'])
def export_dashboard_csv():
    body = request.json or {}
    excel_path = body.get('excel') or CURRENT_ACTIVE['filepath']
    dash = get_dashboard_engine(excel_path)
    if not dash:
        return jsonify({"error": "Motor de datos no disponible para este archivo"}), 404
    filters = body.get('filters', {})
    df_filtered = dash.filter_dataframe(filters)
    
    import io
    output = io.StringIO()
    cols_to_export = [c for c in ['PACIENTE_ID', 'EPS_CANONICA', 'AGRUPADOR', 'ES_PRIORIZADO', 'EDAD', 'SEXO', 'DEPARTAMENTO', 'OBJETIVO_TTO', 'FECHA_INGRESO', 'FECHA_DX'] if c in df_filtered.columns]
    df_filtered[cols_to_export].to_csv(output, index=False, sep=';', encoding='utf-8-sig')
    
    mem = io.BytesIO()
    mem.write(output.getvalue().encode('utf-8-sig'))
    mem.seek(0)
    
    filename = f"Cohorte_Filtrada_{CURRENT_ACTIVE['mes']}_{CURRENT_ACTIVE['ano']}.csv"
    return send_file(mem, as_attachment=True, download_name=filename, mimetype='text/csv')


def find_available_port(start_port=5050, max_tries=50):
    """Busca automáticamente el primer puerto TCP libre para evitar colisiones."""
    for p in range(start_port, start_port + max_tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('0.0.0.0', p))
                return p
            except OSError:
                continue
    return start_port

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Servidor Web INOOS - Informe Junta Directiva")
    parser.add_argument("--port", "-p", type=int, default=int(os.environ.get('PORT', 5050)), help="Puerto para el servidor web (por defecto 5050)")
    parser.add_argument("--host", default="0.0.0.0", help="Host de enlace")
    parser.add_argument("--open", "-o", action="store_true", help="Abrir navegador automáticamente al iniciar")
    args, _ = parser.parse_known_args()

    # Comprobar si el puerto pedido está ocupado
    port = args.port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('0.0.0.0', port))
        except OSError:
            print(f"[AVISO] El puerto {port} está ocupado por otra aplicación.")
            port = find_available_port(start_port=port + 1)
            print(f"[AUTO-ASIGNACIÓN] Usando puerto disponible: {port}")

    url = f"http://localhost:{port}"
    print(f"\n" + "="*60)
    print(f" [INOOS] Servidor Web INOOS Iniciado Exitosamente")
    print(f" Accede desde tu navegador en:")
    print(f" --> {url}")
    print(f"="*60 + "\n")

    # Pre-calentar motor clínico en memoria para respuestas instantáneas (< 0.05s)
    try:
        print("[*] Pre-calentando base de datos e índices analíticos...")
        t_pre = time.time()
        get_dashboard_engine(CURRENT_ACTIVE['filepath'])
        print(f"[OK] Motor clínico listo en memoria ({time.time()-t_pre:.3f}s). El Tablero responderá de forma instantánea.\n")
    except Exception as e:
        print(f"[Aviso] Pre-calentamiento diferido: {e}\n")

    if args.open:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    app.run(host=args.host, port=port, debug=False)
