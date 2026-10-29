import os
import time
import pickle
import hashlib
from datetime import datetime
import unicodedata
import pandas as pd
import numpy as np

EDAD_BINS = [0, 18, 36, 56, 71, 150]
EDAD_LABELS = ['< 18', '18 - 35', '36 - 55', '56 - 70', '> 70']

def normalizar_texto(texto):
    if pd.isna(texto):
        return ""
    texto = str(texto).strip()
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').upper()

def sanitize_for_json(obj):
    """
    Convierte de forma recursiva cualquier valor NaN, Infinito, NaT o no estándar
    a None (que serializa como null en JSON estándar RFC 8259), garantizando que
    el navegador NUNCA reciba tokens inválidos como ': NaN' o ': Infinity'.
    """
    if obj is None:
        return None
    if isinstance(obj, (float, np.floating)):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return float(round(float(obj), 4))
    if isinstance(obj, (int, np.integer)):
        return int(obj)
    if isinstance(obj, (bool, np.bool_)):
        return bool(obj)
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {str(k): sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set, np.ndarray, pd.Series)):
        return [sanitize_for_json(x) for x in obj]
    if pd.isna(obj):
        return None
    return obj

class DashboardEngine:
    def __init__(self, clinical_engine):
        self.engine = clinical_engine

        # 1. Intentar carga desde caché binario derivado de DashboardEngine (< 0.02s)
        cache_path = None
        if hasattr(clinical_engine, '_get_cache_path'):
            base_cp = clinical_engine._get_cache_path()
            if base_cp:
                cache_path = base_cp.replace("engine_", "dash_")
                
        if cache_path and os.path.exists(cache_path):
            try:
                t0 = time.time()
                with open(cache_path, 'rb') as f:
                    self.df = pickle.load(f)
                # Garantizar compatibilidad hacia adelante si el caché previo no tenía TIPO_REGISTRO
                if 'TIPO_REGISTRO' not in self.df.columns:
                    raw = clinical_engine.df_raw
                    if 'INCENCIA_O_PREVALENCIA' in raw.columns:
                        def clean_tipo(val):
                            v = str(val).upper().strip()
                            if 'INCIDENCIA' in v: return 'Incidencia (Casos Nuevos)'
                            return 'Prevalencia (Casos Existentes)'
                        self.df['TIPO_REGISTRO'] = raw['INCENCIA_O_PREVALENCIA'].apply(clean_tipo)
                    else:
                        self.df['TIPO_REGISTRO'] = 'Prevalencia (Casos Existentes)'
                    with open(cache_path, 'wb') as f_out:
                        pickle.dump(self.df, f_out, protocol=pickle.HIGHEST_PROTOCOL)
                print(f"[CACHE HIT] Motor analítico del Dashboard cargado en {time.time()-t0:.3f}s ({len(self.df)} pacientes).")
                return
            except Exception as e:
                print(f"[CACHE MISS] Recalculando columnas analíticas: {e}")

        raw = clinical_engine.df_raw.copy()
        norm = clinical_engine.df.copy()

        # Construir dataset analítico integrado a partir de las columnas reales de la base
        df = norm.copy()

        # 1. Régimen de Afiliación
        if 'REGIMEN' in raw.columns:
            def clean_regimen(val):
                v = str(val).upper()
                if 'SUBSIDIADO' in v or v.startswith('S'): return 'Subsidiado'
                if 'CONTRIBUTIVO' in v or v.startswith('C'): return 'Contributivo'
                if 'ESPECIAL' in v or v.startswith('E'): return 'Especial (FOMAG)'
                if 'PARTICULAR' in v or v.startswith('P'): return 'Particular'
                return 'Otro'
            df['REGIMEN'] = raw['REGIMEN'].apply(clean_regimen)
        else:
            df['REGIMEN'] = 'Sin dato'

        # 2. Clasificación del Estadio Clínico
        if 'CLASIFICACION_DEL_ESTADIO' in raw.columns:
            def clean_estadio(val):
                v = str(val).upper().strip()
                if 'TEMPRANO' in v: return 'Temprano (Estadios I-II)'
                if 'TARDIO' in v: return 'Tardío (Estadio III)'
                if 'METASTASICO' in v: return 'Metastásico (Estadio IV)'
                return 'No Estadificado / Otro'
            df['ESTADIO_CLINICO'] = raw['CLASIFICACION_DEL_ESTADIO'].apply(clean_estadio)
        else:
            df['ESTADIO_CLINICO'] = 'No Estadificado / Otro'

        # 3. Tipo de Registro: Prevalencia vs Incidencia
        if 'INCENCIA_O_PREVALENCIA' in raw.columns:
            def clean_tipo(val):
                v = str(val).upper().strip()
                if 'INCIDENCIA' in v: return 'Incidencia (Casos Nuevos)'
                return 'Prevalencia (Casos Existentes)'
            df['TIPO_REGISTRO'] = raw['INCENCIA_O_PREVALENCIA'].apply(clean_tipo)
        else:
            df['TIPO_REGISTRO'] = 'Prevalencia'

        # 4. Intención Inicial de Tratamiento (Columna 40)
        col_40 = [c for c in raw.columns if '40OBJETIVO' in c or '40' in c]
        if col_40:
            def clean_tto_40(val):
                v = str(val).upper().strip()
                if 'CURACION' in v or 'CURATIV' in v: return 'Tratamiento Curativo'
                if 'PALIACION' in v or 'PALIATIV' in v: return 'Tratamiento Paliativo'
                if 'EXPECTANTE' in v or 'OBSERVACION' in v: return 'Manejo Expectante / Seguimiento'
                return 'Sin registrar / Desconocido'
            df['INTENCION_INICIAL'] = raw[col_40[0]].apply(clean_tto_40)
        else:
            df['INTENCION_INICIAL'] = 'Sin registrar'

        # 5. Cálculo Dinámico de Tiempos de Oportunidad (a nivel de cada paciente)
        # Fecha Confirmación Diagnóstica
        col_dx = [c for c in raw.columns if '18FECHACONFIRMACION' in c or 'CONFIRMACION' in c]
        f_dx = pd.to_datetime(raw[col_dx[0]] if col_dx else None, errors='coerce')
        df['FECHA_DX'] = f_dx

        # Fecha Primera Consulta Médica Efectiva tras Dx
        col_c = [c for c in raw.columns if '26FECHAPRIMERCONSULTA' in c or 'PRIMERCONSULTA' in c]
        if col_c:
            f_c = pd.to_datetime(raw[col_c[0]], errors='coerce')
            dias_dx_c = (f_c - f_dx).dt.days
            # Descartar anomalías de registro (negativos o > 365 días)
            df['DIAS_DX_A_CONSULTA'] = dias_dx_c.where((dias_dx_c >= 0) & (dias_dx_c <= 365))
        else:
            df['DIAS_DX_A_CONSULTA'] = np.nan

        # Tiempo de Procesamiento de Patología (Toma de muestra a Reporte de malignidad)
        col_recol = [c for c in raw.columns if '23FECHARECOLECCION' in c or 'RECOLECCION' in c]
        col_repo = [c for c in raw.columns if '24FECHAREPORTE' in c or 'REPORTEMALIGNIDAD' in c]
        if col_recol and col_repo:
            f_recol = pd.to_datetime(raw[col_recol[0]], errors='coerce')
            f_repo = pd.to_datetime(raw[col_repo[0]], errors='coerce')
            dias_pat = (f_repo - f_recol).dt.days
            df['DIAS_PATOLOGIA'] = dias_pat.where((dias_pat >= 0) & (dias_pat <= 180))
        else:
            df['DIAS_PATOLOGIA'] = np.nan

        # 6. Biomarcador HER2 (Cáncer de Mama)
        col_her2 = [c for c in raw.columns if '33RESULTADOULTIMOHER2' in c or 'RESULTADOULTIMOHER2' in c]
        if col_her2:
            def clean_her2(val):
                v = str(val).upper().strip()
                if '+++' in v or 'POSITIVO' in v or v.startswith('1='): return 'HER2 Positivo (+++)'
                if 'CERO' in v or 'NEGATIVO' in v or v.startswith('4=') or v.startswith('3='): return 'HER2 Negativo'
                if 'EQUIVOCO' in v or 'INDETERMINADO' in v or v.startswith('2='): return 'HER2 Equívoco / Indeterminado'
                if 'NO APLICA' in v or v.startswith('98='): return 'No aplica (No es mama)'
                return 'Desconocido / Sin realizar'
            df['HER2_STATUS'] = raw[col_her2[0]].apply(clean_her2)
        else:
            df['HER2_STATUS'] = 'No aplica'

        # 7. Municipio de Residencia
        col_mun = [c for c in raw.columns if 'MUNICIPIO' in c]
        df['MUNICIPIO'] = raw[col_mun[0]].astype(str).str.strip().str.upper() if col_mun else 'CALI'

        # 8. Rango de Edad
        df['RANGO_EDAD'] = pd.cut(
            df['EDAD'],
            bins=EDAD_BINS,
            labels=EDAD_LABELS,
            right=False
        ).astype(str).replace({'nan': 'Sin dato'})

        self.df = df

        # Guardar dataset analítico en caché binario para reutilización instantánea
        if cache_path:
            try:
                with open(cache_path, 'wb') as f:
                    pickle.dump(self.df, f, protocol=pickle.HIGHEST_PROTOCOL)
                print(f"[CACHE GUARDADO] Dataset analítico indexado en disco ({cache_path}).")
            except Exception as e:
                print(f"Aviso guardando caché analítico: {e}")

    def get_filter_options(self):
        """Retorna todas las opciones únicas extraídas directamente de las columnas de la base."""
        eps_list = sorted([str(e) for e in self.df['EPS_CANONICA'].dropna().unique() if str(e).strip() and str(e) != 'SIN ASIGNAR'])
        agrupadores = sorted([str(a) for a in self.df['AGRUPADOR'].dropna().unique() if str(a).strip()])
        regimenes = sorted([str(r) for r in self.df['REGIMEN'].dropna().unique() if str(r).strip()])
        estadios = ['Todos', 'Temprano (Estadios I-II)', 'Tardío (Estadio III)', 'Metastásico (Estadio IV)', 'No Estadificado / Otro']
        deptos = sorted([str(d) for d in self.df['DEPARTAMENTO'].dropna().unique() if str(d).strip() and str(d) != 'NAN'])

        return {
            'eps': eps_list,
            'agrupadores': agrupadores,
            'prioridades': ['Todos', 'Priorizados CAC', 'No Priorizados'],
            'tipos_registro': ['Todos (Prevalencia + Incidencia)', 'Prevalencia (Casos Existentes)', 'Incidencia (Casos Nuevos)'],
            'regimenes': ['Todos'] + regimenes,
            'estadios': estadios,
            'sexos': ['Todos', 'Femenino (F)', 'Masculino (M)'],
            'rangos_edad': ['Todos'] + EDAD_LABELS,
            'departamentos': deptos,
            'mes_corte': self.engine.mes_corte,
            'ano_corte': self.engine.ano_corte,
            'poblaciones': self.engine.poblaciones
        }

    def filter_dataframe(self, filters=None):
        """Aplica filtros multidimensionales al DataFrame de pacientes."""
        if not filters:
            return self.df.copy()

        df_sub = self.df.copy()

        # 1. Filtro Aseguradora (EPS)
        eps = filters.get('eps')
        if eps and eps != 'ALL' and eps != 'Todos':
            df_sub = df_sub[df_sub['EPS_CANONICA'] == eps]

        # 2. Filtro Prioridad CAC
        prio = filters.get('prioridad')
        if prio == 'priorizados' or prio == 'Priorizados CAC':
            df_sub = df_sub[df_sub['ES_PRIORIZADO'] == True]
        elif prio == 'no_priorizados' or prio == 'No Priorizados':
            df_sub = df_sub[df_sub['ES_PRIORIZADO'] == False]

        # 3. Filtro Agrupador Tumoral
        agrup = filters.get('agrupador')
        if agrup and agrup != 'ALL' and agrup != 'Todos':
            df_sub = df_sub[df_sub['AGRUPADOR'] == agrup]

        # 4. Filtro Régimen
        reg = filters.get('regimen')
        if reg and reg != 'ALL' and reg != 'Todos':
            df_sub = df_sub[df_sub['REGIMEN'] == reg]

        # 5. Filtro Estadio Clínico
        est = filters.get('estadio')
        if est and est != 'ALL' and est != 'Todos':
            df_sub = df_sub[df_sub['ESTADIO_CLINICO'] == est]

        # 6. Filtro Sexo
        sexo = filters.get('sexo')
        if sexo and sexo != 'ALL' and sexo != 'Todos':
            cod_sexo = 'F' if 'F' in str(sexo).upper() else 'M'
            df_sub = df_sub[df_sub['SEXO'] == cod_sexo]

        # 7. Filtro Rango de Edad
        rango = filters.get('rango_edad')
        if rango and rango != 'ALL' and rango != 'Todos':
            df_sub = df_sub[df_sub['RANGO_EDAD'] == rango]

        # 8. Filtro Departamento
        depto = filters.get('depto')
        if depto and depto != 'ALL' and depto != 'Todos':
            df_sub = df_sub[df_sub['DEPARTAMENTO'] == depto]

        # 9. Filtro Registro Epidemiológico (Incidencia vs Prevalencia)
        tipo = filters.get('tipo_registro')
        if tipo and tipo != 'ALL' and tipo != 'Todos':
            if 'incidencia' in tipo.lower() or 'nuevo' in tipo.lower():
                df_sub = df_sub[df_sub['TIPO_REGISTRO'].str.contains('Incidencia', case=False, na=False)]
            elif 'prevalencia' in tipo.lower() or 'existente' in tipo.lower():
                df_sub = df_sub[df_sub['TIPO_REGISTRO'].str.contains('Prevalencia', case=False, na=False)]

        return df_sub

    def calculate_dashboard_metrics(self, filters=None):
        """
        Calcula de forma 100% DINÁMICA todas las métricas e indicadores de la cohorte
        exclusivamente a partir de los datos reales de la base cargada.
        """
        df_sub = self.filter_dataframe(filters)
        total_cohorte_completa = len(self.df)
        total_filtrados = len(df_sub)

        # Denominador poblacional oficial según EPS o Nacional
        eps_selected = filters.get('eps') if filters else None
        if eps_selected and eps_selected in self.engine.poblaciones:
            poblacion = float(self.engine.poblaciones[eps_selected])
            eps_label = eps_selected
        else:
            poblacion = float(self.engine.poblaciones.get('NACIONAL', 623321.0))
            eps_label = "Nacional Consolidado"

        # Tasa de Prevalencia x 100.000
        tasa_prevalencia = round((total_filtrados / poblacion) * 100000.0, 2) if poblacion > 0 else 0.0
        pct_cohorte = round((total_filtrados / total_cohorte_completa) * 100.0, 1) if total_cohorte_completa > 0 else 0.0

        # Priorizados vs No Priorizados
        prio_count = int(df_sub['ES_PRIORIZADO'].sum())
        noprio_count = int((~df_sub['ES_PRIORIZADO']).sum())
        prio_pct = round((prio_count / total_filtrados) * 100.0, 1) if total_filtrados > 0 else 0.0
        noprio_pct = round((noprio_count / total_filtrados) * 100.0, 1) if total_filtrados > 0 else 0.0

        # Prevalencia vs Incidencia (Casos Nuevos)
        prevalentes_count = int((df_sub['TIPO_REGISTRO'] == 'Prevalencia (Casos Existentes)').sum())
        incidentes_count = int((df_sub['TIPO_REGISTRO'] == 'Incidencia (Casos Nuevos)').sum())
        prevalentes_pct = round((prevalentes_count / total_filtrados) * 100.0, 1) if total_filtrados > 0 else 0.0
        incidentes_pct = round((incidentes_count / total_filtrados) * 100.0, 1) if total_filtrados > 0 else 0.0
        tasa_incidencia = round((incidentes_count / poblacion) * 100000.0, 2) if poblacion > 0 else 0.0

        # Demografía: Sexo y Edad
        sex_counts = df_sub['SEXO'].value_counts().to_dict()
        fem_count = int(sex_counts.get('F', 0))
        masc_count = int(sex_counts.get('M', 0))
        fem_pct = round((fem_count / total_filtrados) * 100.0, 1) if total_filtrados > 0 else 0.0
        masc_pct = round((masc_count / total_filtrados) * 100.0, 1) if total_filtrados > 0 else 0.0

        edad_valid = df_sub['EDAD'].dropna()
        edad_prom = round(float(edad_valid.mean()), 1) if len(edad_valid) > 0 else 0.0
        edad_min = int(edad_valid.min()) if len(edad_valid) > 0 else 0
        edad_max = int(edad_valid.max()) if len(edad_valid) > 0 else 0

        # ==========================================
        # 1. ESTADIFICACIÓN CLÍNICA (Calculada de la base)
        # ==========================================
        estadios_counts = df_sub['ESTADIO_CLINICO'].value_counts().to_dict()
        c_temprano = int(estadios_counts.get('Temprano (Estadios I-II)', 0))
        c_tardio = int(estadios_counts.get('Tardío (Estadio III)', 0))
        c_metastasico = int(estadios_counts.get('Metastásico (Estadio IV)', 0))
        c_no_est = int(estadios_counts.get('No Estadificado / Otro', 0))

        total_estadificados = c_temprano + c_tardio + c_metastasico
        pct_temprano = round((c_temprano / total_estadificados) * 100.0, 1) if total_estadificados > 0 else 0.0
        pct_tardio = round((c_tardio / total_estadificados) * 100.0, 1) if total_estadificados > 0 else 0.0
        pct_metastasico = round((c_metastasico / total_estadificados) * 100.0, 1) if total_estadificados > 0 else 0.0

        estadios_data = {
            'labels': ['Temprano (Estadios I-II)', 'Tardío (Estadio III)', 'Metastásico (Estadio IV)', 'No Estadificado / Otro'],
            'casos': [c_temprano, c_tardio, c_metastasico, c_no_est],
            'pcts_estadificados': [pct_temprano, pct_tardio, pct_metastasico, 0.0]
        }

        # ==========================================
        # 2. OPORTUNIDADES ASISTENCIALES REALES (Calculadas de fechas)
        # ==========================================
        dias_c = df_sub['DIAS_DX_A_CONSULTA'].dropna()
        if len(dias_c) > 0:
            mediana_consulta = round(float(dias_c.median()), 1)
            media_consulta = round(float(dias_c.mean()), 1)
            cumple_15d_pct = round(float((dias_c <= 15).mean()) * 100.0, 1)
            cumple_30d_pct = round(float((dias_c <= 30).mean()) * 100.0, 1)
        else:
            mediana_consulta = 0.0
            media_consulta = 0.0
            cumple_15d_pct = 0.0
            cumple_30d_pct = 0.0

        dias_pat = df_sub['DIAS_PATOLOGIA'].dropna()
        if len(dias_pat) > 0:
            mediana_pat = round(float(dias_pat.median()), 1)
            media_pat = round(float(dias_pat.mean()), 1)
            cumple_pat_10d = round(float((dias_pat <= 10).mean()) * 100.0, 1)
        else:
            mediana_pat = 0.0
            media_pat = 0.0
            cumple_pat_10d = 0.0

        # Histograma de Oportunidad de Consulta
        oportunidad_histogram = {
            'labels': ['<= 15 días (Meta CAC)', '16 - 30 días', '31 - 60 días', '> 60 días'],
            'casos': [
                int((dias_c <= 15).sum()),
                int(((dias_c > 15) & (dias_c <= 30)).sum()),
                int(((dias_c > 30) & (dias_c <= 60)).sum()),
                int((dias_c > 60).sum())
            ]
        }

        # ==========================================
        # 3. BENCHMARKING OFICIAL CAC / INC (Contraste Técnico)
        # ==========================================
        # Datos oficiales de consenso Cuenta de Alto Costo e Instituto Nacional de Cancerología
        benchmarking = {
            'estadios_tempranos': {
                'inoos_val': pct_temprano,
                'meta_cac': 60.0,          # Meta Consenso CAC (>= 60%)
                'promedio_nacional': 49.15, # Promedio Nacional Colombia CAC en cánceres priorizados
                'brecha_meta': round(pct_temprano - 60.0, 1),
                'supera_promedio': pct_temprano >= 49.15
            },
            'oportunidad_primera_consulta': {
                'inoos_mediana_dias': mediana_consulta,
                'meta_cac_dias': 15.0,     # Meta Consenso CAC (<= 15 días)
                'meta_intermedia_dias': 30.0,
                'promedio_nacional_cac': 38.0, # Promedio nacional Colombia reportado por la CAC
                'cumple_15d_pct': cumple_15d_pct,
                'cumple_30d_pct': cumple_30d_pct
            },
            'tiempo_patologia': {
                'inoos_mediana_dias': mediana_pat,
                'meta_inc_dias': 10.0,     # Estándar Instituto Nacional de Cancerología (<= 10 días)
                'cumple_pct': cumple_pat_10d
            },
            # Comparativo por Régimen (Contributivo vs Subsidiado) calculado de la base
            'comparativo_regimen': {}
        }

        # Calcular equidad por Régimen directamente sobre la base
        for reg_nombre in ['Contributivo', 'Subsidiado']:
            df_reg = df_sub[df_sub['REGIMEN'] == reg_nombre]
            if len(df_reg) > 0:
                reg_est = df_reg[df_reg['ESTADIO_CLINICO'].isin(['Temprano (Estadios I-II)', 'Tardío (Estadio III)', 'Metastásico (Estadio IV)'])]
                reg_temprano_pct = round(((reg_est['ESTADIO_CLINICO'] == 'Temprano (Estadios I-II)').sum() / len(reg_est) * 100.0), 1) if len(reg_est) > 0 else 0.0
                reg_dias_c = df_reg['DIAS_DX_A_CONSULTA'].dropna()
                reg_mediana_dias = round(float(reg_dias_c.median()), 1) if len(reg_dias_c) > 0 else 0.0

                benchmarking['comparativo_regimen'][reg_nombre] = {
                    'casos': len(df_reg),
                    'temprano_pct': reg_temprano_pct,
                    'mediana_dias_consulta': reg_mediana_dias
                }

        # ==========================================
        # 4. Biomarcador HER2 (Cáncer de Mama)
        # ==========================================
        df_mama = df_sub[df_sub['AGRUPADOR'].str.contains('Mama', case=False, na=False)]
        her2_counts = df_mama['HER2_STATUS'].value_counts().to_dict() if len(df_mama) > 0 else {}
        her2_pos = int(her2_counts.get('HER2 Positivo (+++)', 0))
        her2_neg = int(her2_counts.get('HER2 Negativo', 0))
        her2_evaluables = her2_pos + her2_neg
        her2_pos_pct = round((her2_pos / her2_evaluables) * 100.0, 1) if her2_evaluables > 0 else 0.0

        mama_biomarcadores = {
            'total_mama': len(df_mama),
            'her2_positivo': her2_pos,
            'her2_negativo': her2_neg,
            'her2_desconocido': int(her2_counts.get('Desconocido / Sin realizar', 0)),
            'her2_positividad_pct': her2_pos_pct,
            'rango_esperado_inc': '15% - 25%' # Rango epidemiológico INC Colombia
        }

        # ==========================================
        # 5. Distribución de los 25 Agrupadores Tumorales
        # ==========================================
        vc_agrup = df_sub['AGRUPADOR'].value_counts()
        agrupadores_data = []
        for ag, cnt in vc_agrup.items():
            tasa_ag = round((cnt / poblacion) * 100000.0, 2) if poblacion > 0 else 0.0
            pct_ag = round((cnt / total_filtrados) * 100.0, 1) if total_filtrados > 0 else 0.0
            agrupadores_data.append({
                'agrupador': ag,
                'casos': int(cnt),
                'tasa': tasa_ag,
                'pct': pct_ag
            })

        top10_agrupadores = {
            'labels': [x['agrupador'] for x in agrupadores_data[:10]],
            'casos': [x['casos'] for x in agrupadores_data[:10]],
            'tasas': [x['tasa'] for x in agrupadores_data[:10]]
        }

        # ==========================================
        # 6. Distribución por Asegurador (EPS)
        # ==========================================
        eps_counts = df_sub['EPS_CANONICA'].value_counts()
        eps_chart_data = {
            'labels': list(eps_counts.index),
            'casos': [int(c) for c in eps_counts.values],
            'pcts': [round((c / total_filtrados) * 100.0, 1) if total_filtrados > 0 else 0.0 for c in eps_counts.values]
        }

        # ==========================================
        # 7. Distribución por Régimen
        # ==========================================
        reg_counts = df_sub['REGIMEN'].value_counts()
        regimen_chart_data = {
            'labels': list(reg_counts.index),
            'casos': [int(c) for c in reg_counts.values],
            'pcts': [round((c / total_filtrados) * 100.0, 1) if total_filtrados > 0 else 0.0 for c in reg_counts.values]
        }

        # ==========================================
        # 8. Pirámide Poblacional (Rango Edad x Sexo)
        # ==========================================
        edad_sexo_data = {
            'labels': EDAD_LABELS,
            'femenino': [],
            'masculino': []
        }
        for lbl in EDAD_LABELS:
            f_c = len(df_sub[(df_sub['RANGO_EDAD'] == lbl) & (df_sub['SEXO'] == 'F')])
            m_c = len(df_sub[(df_sub['RANGO_EDAD'] == lbl) & (df_sub['SEXO'] == 'M')])
            edad_sexo_data['femenino'].append(f_c)
            edad_sexo_data['masculino'].append(m_c)

        # ==========================================
        # 9. Distribución Geográfica (Departamentos y Municipios)
        # ==========================================
        dept_counts = df_sub['DEPARTAMENTO'].value_counts()
        dept_data = {
            'labels': [d for d in dept_counts.index if str(d).strip() and str(d) != 'NAN'][:6],
            'casos': [int(c) for d, c in dept_counts.items() if str(d).strip() and str(d) != 'NAN'][:6]
        }

        mun_counts = df_sub['MUNICIPIO'].value_counts()
        top_municipios = {
            'labels': [m for m in mun_counts.index if str(m).strip() and str(m) != 'NAN'][:8],
            'casos': [int(c) for m, c in mun_counts.items() if str(m).strip() and str(m) != 'NAN'][:8]
        }

        # ==========================================
        # 10. Evolución Mensual (de las fechas de ingreso y diagnóstico)
        # ==========================================
        meses_nombres = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
        df_ano_ing = df_sub[df_sub['ANO_INGRESO'] == self.engine.ano_corte]
        ing_mes_counts = df_ano_ing['MES_INGRESO'].value_counts().to_dict()
        ingresos_serie = [int(ing_mes_counts.get(m, 0)) for m in range(1, 13)]

        df_ano_dx = df_sub[df_sub['ANO_DX'] == self.engine.ano_corte]
        dx_mes_counts = df_ano_dx['MES_DX'].value_counts().to_dict()
        incidencia_casos = [int(dx_mes_counts.get(m, 0)) for m in range(1, 13)]
        incidencia_tasas = [round((c / poblacion) * 100000.0, 2) if poblacion > 0 else 0.0 for c in incidencia_casos]

        # ==========================================
        # 11. Intención Inicial de Tratamiento (Columna 40)
        # ==========================================
        intencion_counts = df_sub['INTENCION_INICIAL'].value_counts()
        intencion_data = {
            'labels': list(intencion_counts.index),
            'casos': [int(c) for c in intencion_counts.values],
            'pcts': [round((c / total_filtrados) * 100.0, 1) if total_filtrados > 0 else 0.0 for c in intencion_counts.values]
        }

        # ==========================================
        # 12. Muestra de Pacientes para el Explorador
        # ==========================================
        cols_explorer = ['PACIENTE_ID', 'EPS_CANONICA', 'REGIMEN', 'AGRUPADOR', 'ES_PRIORIZADO', 'ESTADIO_CLINICO', 'EDAD', 'SEXO', 'DEPARTAMENTO', 'DIAS_DX_A_CONSULTA', 'INTENCION_INICIAL']
        cols_presentes = [c for c in cols_explorer if c in df_sub.columns]
        sample_df = df_sub[cols_presentes].head(100).copy()
        sample_df['PRIORIDAD_LABEL'] = sample_df['ES_PRIORIZADO'].apply(lambda x: 'Priorizado CAC' if x else 'No Priorizado')
        
        # Reemplazar explícitamente NaN y null en sample_df para evitar "CONSULTA": NaN
        sample_df = sample_df.where(pd.notnull(sample_df), None)
        raw_sample = sample_df.to_dict(orient='records')
        pacientes_sample = []
        for row in raw_sample:
            clean_row = {}
            for k, v in row.items():
                if v is None or (isinstance(v, float) and (np.isnan(v) or np.isinf(v))):
                    clean_row[k] = None
                else:
                    clean_row[k] = v
            pacientes_sample.append(clean_row)

        output_data = {
            'status': 'success',
            'filtros_aplicados': filters or {},
            'kpis': {
                'total_filtrados': total_filtrados,
                'total_general': total_cohorte_completa,
                'pct_cohorte': pct_cohorte,
                'poblacion_afiliada': int(poblacion),
                'poblacion_label': eps_label,
                'tasa_prevalencia': tasa_prevalencia,
                'tasa_incidencia': tasa_incidencia,
                'priorizados_count': prio_count,
                'priorizados_pct': prio_pct,
                'no_priorizados_count': noprio_count,
                'no_priorizados_pct': noprio_pct,
                'prevalentes_count': prevalentes_count,
                'prevalentes_pct': prevalentes_pct,
                'incidentes_count': incidentes_count,
                'incidentes_pct': incidentes_pct,
                'estadio_temprano_pct': pct_temprano,
                'estadio_tardio_pct': pct_tardio,
                'estadio_metastasico_pct': pct_metastasico,
                'oportunidad_mediana_dias': mediana_consulta,
                'oportunidad_cumple_15d_pct': cumple_15d_pct,
                'oportunidad_cumple_30d_pct': cumple_30d_pct,
                'patologia_mediana_dias': mediana_pat,
                'femenino_count': fem_count,
                'femenino_pct': fem_pct,
                'masculino_count': masc_count,
                'masculino_pct': masc_pct,
                'edad_promedio': edad_prom,
                'edad_min': edad_min,
                'edad_max': edad_max
            },
            'estadios': estadios_data,
            'oportunidades': {
                'mediana_consulta': mediana_consulta,
                'media_consulta': media_consulta,
                'cumple_15d_pct': cumple_15d_pct,
                'cumple_30d_pct': cumple_30d_pct,
                'mediana_patologia': mediana_pat,
                'histograma': oportunidad_histogram
            },
            'benchmarking_cac': benchmarking,
            'mama_biomarcadores': mama_biomarcadores,
            'agrupadores_todos': agrupadores_data,
            'top10_agrupadores': top10_agrupadores,
            'eps_distribucion': eps_chart_data,
            'regimen_distribucion': regimen_chart_data,
            'piramide_edad_sexo': edad_sexo_data,
            'departamentos': dept_data,
            'top_municipios': top_municipios,
            'evolucion_mensual': {
                'meses': meses_nombres,
                'ingresos': ingresos_serie,
                'incidencia_casos': incidencia_casos,
                'incidencia_tasas': incidencia_tasas
            },
            'intencion_tratamiento': intencion_data,
            'pacientes_sample': pacientes_sample
        }

        # Sanitizar estrictamente el 100% de la estructura para garantizar JSON válido sin NaN
        return sanitize_for_json(output_data)
