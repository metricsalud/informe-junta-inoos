#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generador_informe_junta.py
Motor de Automatización de Informes de Junta Directiva Mensual INOOS
Genera presentaciones PowerPoint editables (.pptx) de 115 diapositivas a partir
de cualquier base de datos mensual en Excel (.xlsx) de la cohorte oncológica.
"""

import os
import sys
import argparse
import copy
import re
from datetime import datetime
import lxml.etree as etree

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt

from data_engine import ClinicalDataEngine

# Constantes de Identidad Visual Institucional
COLOR_LILA = RGBColor(129, 88, 161)       # #8158A1 Principal
COLOR_TURQUESA = RGBColor(71, 169, 161)   # #47A9A1 Secundario
COLOR_GRIS = RGBColor(146, 148, 150)      # #929496 Neutro
COLOR_BLANCO = RGBColor(255, 255, 255)

NS = {
    'c': 'http://schemas.openxmlformats.org/drawingml/2006/chart',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
}

def update_chart_xml(chart, new_categories=None, series_values=None):
    """
    Actualiza directamente el OpenXML de los gráficos preservando estilos, fuentes,
    posicionamiento y aplanando las series a través de todos los sub-plots (para gráficos combinados).
    """
    # 1. Actualizar Categorías
    if new_categories is not None:
        for plot in chart.plots:
            for series in plot.series:
                cat_elem = series._element.find('c:cat', NS)
                if cat_elem is not None:
                    str_cache = cat_elem.find('.//c:strCache', NS)
                    if str_cache is not None:
                        for old_pt in str_cache.findall('c:pt', NS):
                            str_cache.remove(old_pt)
                        pt_count = str_cache.find('c:ptCount', NS)
                        if pt_count is not None:
                            pt_count.set('val', str(len(new_categories)))
                        for idx, cat_val in enumerate(new_categories):
                            pt = etree.SubElement(str_cache, '{http://schemas.openxmlformats.org/drawingml/2006/chart}pt')
                            pt.set('idx', str(idx))
                            v = etree.SubElement(pt, '{http://schemas.openxmlformats.org/drawingml/2006/chart}v')
                            v.text = str(cat_val)

    # 2. Actualizar Valores Numéricos aplanando series en todos los plots
    if series_values is not None:
        all_series = [s for plot in chart.plots for s in plot.series]
        for s_idx, series in enumerate(all_series):
            if s_idx < len(series_values):
                vals_list = series_values[s_idx]
                if vals_list is not None:
                    val_elem = series._element.find('c:val', NS)
                    if val_elem is not None:
                        num_cache = val_elem.find('.//c:numCache', NS)
                        if num_cache is not None:
                            for old_pt in num_cache.findall('c:pt', NS):
                                num_cache.remove(old_pt)
                            pt_count = num_cache.find('c:ptCount', NS)
                            if pt_count is not None:
                                pt_count.set('val', str(len(vals_list)))
                            for idx, num_val in enumerate(vals_list):
                                if num_val is not None:
                                    pt = etree.SubElement(num_cache, '{http://schemas.openxmlformats.org/drawingml/2006/chart}pt')
                                    pt.set('idx', str(idx))
                                    v = etree.SubElement(pt, '{http://schemas.openxmlformats.org/drawingml/2006/chart}v')
                                    v.text = f"{num_val:.4f}" if isinstance(num_val, float) else str(num_val)


class GeneradorInformeJunta:
    def __init__(self, excel_path, template_path="template_junta.pptx", output_path=None, mes_corte="Septiembre", ano_corte=2026):
        self.excel_path = excel_path
        self.template_path = template_path if os.path.exists(template_path) else "Junta Directiva Septiembre 2026 GENERAL COMPLETA.pptx"
        self.mes_corte = mes_corte
        self.ano_corte = int(ano_corte)
        
        if not output_path:
            self.output_path = f"Informe_Junta_Directiva_{self.mes_corte}_{self.ano_corte}.pptx"
        else:
            self.output_path = output_path
            
        self.engine = ClinicalDataEngine(self.excel_path, self.mes_corte, self.ano_corte)
        self.prs = None

    def generar(self):
        print(f"\n========================================================")
        print(f"GENERANDO INFORME DE JUNTA DIRECTIVA INOOS")
        print(f"Mes de Corte: {self.mes_corte} {self.ano_corte}")
        print(f"Entrada Excel: {self.excel_path}")
        print(f"Plantilla PPTX: {self.template_path}")
        print(f"Salida PPTX: {self.output_path}")
        print(f"========================================================\n")
        
        self.prs = Presentation(self.template_path)
        print(f"Plantilla cargada exitosamente: {len(self.prs.slides)} diapositivas.")
        
        # 1. Actualizar textos de fechas y encabezados en toda la presentación
        self._actualizar_textos_globales()
        
        # 2. Actualizar Diapositivas Clínicas Nacionales (Slides 1 - 14)
        self._actualizar_slides_nacionales()
        
        # 3. Actualizar Diapositivas Salud Total (Slides 35 - 49)
        self._actualizar_slides_salud_total()
        
        # 4. Actualizar Diapositivas Sanitas EPS (Slides 55 - 66)
        self._actualizar_slides_sanitas()
        
        # 5. Actualizar Diapositivas Emssanar (Slides 72 - 84)
        self._actualizar_slides_emssanar()
        
        # 6. Actualizar Diapositivas Fomag (Slides 92 - 97)
        self._actualizar_slides_fomag()
        
        # 7. Actualizar Diapositivas Familiar de Colombia (Slides 103 - 109)
        self._actualizar_slides_familiar()
        
        # 8. Guardar archivo final
        print(f"\nGuardando informe generado en: {self.output_path}...")
        self.prs.save(self.output_path)
        size_mb = os.path.getsize(self.output_path) / (1024 * 1024)
        print(f"Informe de Junta generado con éxito! Tamaño: {size_mb:.2f} MB")
        return self.output_path

    def _actualizar_textos_globales(self):
        meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
        
        for s_idx, slide in enumerate(self.prs.slides):
            # Portada principal (Slide 1)
            if s_idx == 0:
                for shape in slide.shapes:
                    if shape.has_text_frame:
                        for p in shape.text_frame.paragraphs:
                            if "Junta Directiva" in p.text:
                                p.text = f"Junta Directiva {self.mes_corte} {self.ano_corte}"
            
            # Portada Sección (Slide 2)
            elif s_idx == 1:
                for shape in slide.shapes:
                    if shape.has_text_frame:
                        for p in shape.text_frame.paragraphs:
                            if "Septiembre 2026" in p.text:
                                p.text = p.text.replace("Septiembre 2026", f"{self.mes_corte} {self.ano_corte}")

            # Reemplazar menciones en textos y fuentes clínicas
            for shape in slide.shapes:
                if shape.has_text_frame:
                    for p in shape.text_frame.paragraphs:
                        if "Cohorte oncológica INOOS" in p.text or "Cohorte oncologica INOOS" in p.text:
                            for m in meses:
                                p.text = re.sub(rf"Cohorte oncol[óo]gica INOOS {m} \d{{4}}", f"Cohorte oncológica INOOS {self.mes_corte} {self.ano_corte}", p.text, flags=re.IGNORECASE)

    def _actualizar_slides_nacionales(self):
        print("Actualizando láminas clínicas nacionales (Slides 3 - 14)...")
        
        # Slide 3: Ingresos mensuales 2024/2026
        s3 = self.prs.slides[2]
        for shape in s3.shapes:
            if shape.has_chart:
                meses, ingresos_ano = self.engine.get_ingresos_mensuales()
                update_chart_xml(shape.chart, series_values=[None, None, ingresos_ano])
                
        # Slide 4: Incidencia INOOS año 2025/2026
        s4 = self.prs.slides[3]
        for shape in s4.shapes:
            if shape.has_chart:
                meses, incid_casos, incid_tasas = self.engine.get_incidencia_mensual()
                update_chart_xml(shape.chart, series_values=[None, incid_casos, None, incid_tasas])

        # Slide 5: Prevalencia año 2025/2026
        s5 = self.prs.slides[4]
        for shape in s5.shapes:
            if shape.has_chart:
                meses, acum_casos, acum_tasas = self.engine.get_prevalencia_mensual()
                update_chart_xml(shape.chart, series_values=[None, acum_casos, None, acum_tasas])

        # Slide 6: Distribución de la Cohorte General
        s6 = self.prs.slides[5]
        for shape in s6.shapes:
            if shape.has_chart:
                cats, casos, tasas = self.engine.get_distribucion_agrupador()
                update_chart_xml(shape.chart, new_categories=cats, series_values=[casos, tasas])

        # Slide 7: Cánceres Priorizados
        s7 = self.prs.slides[6]
        for shape in s7.shapes:
            if shape.has_chart:
                t = shape.chart.chart_title.text_frame.text if shape.chart.has_title else ""
                if str(self.ano_corte - 1) not in t:
                    cats, casos, tasas = self.engine.get_distribucion_agrupador(prioridad='priorizados')
                    update_chart_xml(shape.chart, new_categories=cats, series_values=[casos, tasas])

        # Slide 8: Cánceres No Priorizados
        s8 = self.prs.slides[7]
        for shape in s8.shapes:
            if shape.has_chart:
                t = shape.chart.chart_title.text_frame.text if shape.chart.has_title else ""
                if str(self.ano_corte - 1) not in t:
                    cats, casos, tasas = self.engine.get_distribucion_agrupador(prioridad='no_priorizados')
                    update_chart_xml(shape.chart, new_categories=cats, series_values=[casos, tasas])

    def _actualizar_slides_salud_total(self):
        print("Actualizando láminas Salud Total (Slides 36 - 48)...")
        
        # Slide 36: Histórico Ingresos Salud Total
        s36 = self.prs.slides[35]
        for shape in s36.shapes:
            if shape.has_chart:
                meses, ingresos_ano = self.engine.get_ingresos_mensuales(eps='SALUD TOTAL')
                update_chart_xml(shape.chart, series_values=[None, None, ingresos_ano])

        # Slide 37: Prevalencia Salud Total
        s37 = self.prs.slides[36]
        for shape in s37.shapes:
            if shape.has_chart:
                meses, casos_prev, tasas_prev = self.engine.get_prevalencia_mensual(eps='SALUD TOTAL')
                update_chart_xml(shape.chart, series_values=[None, casos_prev, None, tasas_prev])

        # Slide 38: Incidencia Salud Total
        s38 = self.prs.slides[37]
        for shape in s38.shapes:
            if shape.has_chart:
                meses, incid_casos, incid_tasas = self.engine.get_incidencia_mensual(eps='SALUD TOTAL')
                update_chart_xml(shape.chart, series_values=[None, incid_casos, None, incid_tasas])

        # Slide 41: Distribución Cáncer Salud Total
        s41 = self.prs.slides[40]
        for shape in s41.shapes:
            if shape.has_chart:
                cats, casos, tasas = self.engine.get_distribucion_agrupador(eps='SALUD TOTAL')
                update_chart_xml(shape.chart, new_categories=cats, series_values=[casos, tasas])

        # Slide 42: Priorizados Salud Total
        s42 = self.prs.slides[41]
        for shape in s42.shapes:
            if shape.has_chart:
                t = shape.chart.chart_title.text_frame.text if shape.chart.has_title else ""
                if str(self.ano_corte - 1) not in t:
                    cats, casos, tasas = self.engine.get_distribucion_agrupador(eps='SALUD TOTAL', prioridad='priorizados')
                    update_chart_xml(shape.chart, new_categories=cats, series_values=[casos, tasas])

        # Slide 43: No Priorizados Salud Total
        s43 = self.prs.slides[42]
        for shape in s43.shapes:
            if shape.has_chart:
                t = shape.chart.chart_title.text_frame.text if shape.chart.has_title else ""
                if str(self.ano_corte - 1) not in t:
                    cats, casos, tasas = self.engine.get_distribucion_agrupador(eps='SALUD TOTAL', prioridad='no_priorizados')
                    update_chart_xml(shape.chart, new_categories=cats, series_values=[casos, tasas])

        # Slide 48: Intención de Tratamiento Salud Total
        s48 = self.prs.slides[47]
        for shape in s48.shapes:
            if shape.has_table:
                table = shape.table
                intencion_datos, total_st = self.engine.get_intencion_tratamiento_salud_total()
                for cell in table.rows[0].cells:
                    cell.fill.solid()
                    cell.fill.fore_color.rgb = COLOR_LILA
                    for p in cell.text_frame.paragraphs:
                        p.font.color.rgb = COLOR_BLANCO
                        p.font.bold = True
                for r_idx, (cat_nombre, conteo, pct) in enumerate(intencion_datos, start=1):
                    if r_idx < len(table.rows):
                        table.rows[r_idx].cells[0].text = cat_nombre
                        table.rows[r_idx].cells[1].text = str(conteo)
                        table.rows[r_idx].cells[2].text = f"{pct:.1f}%"

    def _actualizar_slides_sanitas(self):
        print("Actualizando láminas Sanitas EPS (Slides 56 - 61)...")
        
        # Slide 56: Ingresos Sanitas
        s56 = self.prs.slides[55]
        for shape in s56.shapes:
            if shape.has_chart:
                meses, ingresos_ano = self.engine.get_ingresos_mensuales(eps='SANITAS EPS')
                tasas_ano = [(c / self.engine.poblaciones['SANITAS EPS']) * 100000.0 if c is not None else None for c in ingresos_ano]
                update_chart_xml(shape.chart, series_values=[None, ingresos_ano, None, tasas_ano])

        # Slide 57: Incidencia Sanitas
        s57 = self.prs.slides[56]
        for shape in s57.shapes:
            if shape.has_chart:
                meses, incid_casos, incid_tasas = self.engine.get_incidencia_mensual(eps='SANITAS EPS')
                update_chart_xml(shape.chart, series_values=[None, incid_casos, None, incid_tasas])

        # Slide 58: Prevalencia Sanitas
        s58 = self.prs.slides[57]
        for shape in s58.shapes:
            if shape.has_chart:
                meses, casos_prev, tasas_prev = self.engine.get_prevalencia_mensual(eps='SANITAS EPS')
                update_chart_xml(shape.chart, series_values=[None, casos_prev, None, tasas_prev])

        # Slide 59: Distribución Cáncer Sanitas
        s59 = self.prs.slides[58]
        for shape in s59.shapes:
            if shape.has_chart:
                cats, casos, tasas = self.engine.get_distribucion_agrupador(eps='SANITAS EPS')
                update_chart_xml(shape.chart, new_categories=cats, series_values=[casos, tasas])

        # Slide 60: Priorizados Sanitas
        s60 = self.prs.slides[59]
        for shape in s60.shapes:
            if shape.has_chart:
                t = shape.chart.chart_title.text_frame.text if shape.chart.has_title else ""
                if str(self.ano_corte - 1) not in t:
                    cats, casos, tasas = self.engine.get_distribucion_agrupador(eps='SANITAS EPS', prioridad='priorizados')
                    update_chart_xml(shape.chart, new_categories=cats, series_values=[casos, tasas])

        # Slide 61: No Priorizados Sanitas
        s61 = self.prs.slides[60]
        for shape in s61.shapes:
            if shape.has_chart:
                t = shape.chart.chart_title.text_frame.text if shape.chart.has_title else ""
                if str(self.ano_corte - 1) not in t:
                    cats, casos, tasas = self.engine.get_distribucion_agrupador(eps='SANITAS EPS', prioridad='no_priorizados')
                    update_chart_xml(shape.chart, new_categories=cats, series_values=[casos, tasas])

    def _actualizar_slides_emssanar(self):
        print("Actualizando láminas Emssanar (Slides 73 - 77)...")
        
        # Slide 73: Ingresos Emssanar
        s73 = self.prs.slides[72]
        for shape in s73.shapes:
            if shape.has_chart:
                meses, ingresos_ano = self.engine.get_ingresos_mensuales(eps='EMSSANAR')
                tasas_ano = [(c / self.engine.poblaciones['EMSSANAR']) * 100000.0 if c is not None else None for c in ingresos_ano]
                update_chart_xml(shape.chart, series_values=[None, ingresos_ano, None, tasas_ano])

        # Slide 74: Incidencia Emssanar
        s74 = self.prs.slides[73]
        for shape in s74.shapes:
            if shape.has_chart:
                meses, incid_casos, incid_tasas = self.engine.get_incidencia_mensual(eps='EMSSANAR')
                update_chart_xml(shape.chart, series_values=[None, incid_casos, None, incid_tasas])

        # Slide 75: Distribución Cáncer Emssanar (Incidencia y Prevalencia)
        s75 = self.prs.slides[74]
        for c_idx, shape in enumerate([sh for sh in s75.shapes if sh.has_chart]):
            if c_idx == 0:
                # Gráfico 1: Tasa de incidencia de cánceres Emssanar (Año actual 2026)
                cats, casos, tasas = self.engine.get_distribucion_incidencia_agrupador(eps='EMSSANAR', ano=self.ano_corte)
                update_chart_xml(shape.chart, new_categories=cats, series_values=[casos, tasas])
            elif c_idx == 1:
                # Gráfico 2: Tasa de prevalencia de cánceres Emssanar (Cohorte acumulada)
                cats, casos, tasas = self.engine.get_distribucion_agrupador(eps='EMSSANAR')
                update_chart_xml(shape.chart, new_categories=cats, series_values=[casos, tasas])

        # Slide 76: Prevalencia Emssanar
        s76 = self.prs.slides[75]
        for shape in s76.shapes:
            if shape.has_chart:
                meses, casos_prev, tasas_prev = self.engine.get_prevalencia_mensual(eps='EMSSANAR')
                update_chart_xml(shape.chart, series_values=[None, casos_prev, None, tasas_prev])

        # Slide 77: Priorizados y No Priorizados Emssanar
        s77 = self.prs.slides[76]
        for c_idx, shape in enumerate([sh for sh in s77.shapes if sh.has_chart]):
            t = shape.chart.chart_title.text_frame.text if shape.chart.has_title else ""
            if "no priorizados" in t.lower():
                cats, casos, tasas = self.engine.get_distribucion_agrupador(eps='EMSSANAR', prioridad='no_priorizados')
                update_chart_xml(shape.chart, new_categories=cats, series_values=[casos, tasas])
            elif "priorizados" in t.lower():
                cats, casos, tasas = self.engine.get_distribucion_agrupador(eps='EMSSANAR', prioridad='priorizados')
                update_chart_xml(shape.chart, new_categories=cats, series_values=[casos, tasas])

    def _actualizar_slides_fomag(self):
        print("Actualizando láminas Fomag (Slides 93 - 95)...")
        s93 = self.prs.slides[92]
        for shape in s93.shapes:
            if shape.has_chart:
                meses, ingresos_ano = self.engine.get_ingresos_mensuales(eps='FOMAG')
                update_chart_xml(shape.chart, series_values=[None, None, ingresos_ano])

        s94 = self.prs.slides[93]
        for shape in s94.shapes:
            if shape.has_chart:
                meses, casos_prev, tasas_prev = self.engine.get_prevalencia_mensual(eps='FOMAG')
                update_chart_xml(shape.chart, series_values=[None, casos_prev, None, tasas_prev])

        s95 = self.prs.slides[94]
        for shape in s95.shapes:
            if shape.has_chart:
                cats, casos, tasas = self.engine.get_distribucion_agrupador(eps='FOMAG')
                update_chart_xml(shape.chart, new_categories=cats, series_values=[casos, tasas])

    def _actualizar_slides_familiar(self):
        print("Actualizando láminas Familiar de Colombia (Slides 104 - 106)...")
        s104 = self.prs.slides[103]
        for shape in s104.shapes:
            if shape.has_chart:
                meses, incid_casos, incid_tasas = self.engine.get_incidencia_mensual(eps='EPS FAMILIAR')
                update_chart_xml(shape.chart, series_values=[incid_casos, incid_tasas])

        s105 = self.prs.slides[104]
        for shape in s105.shapes:
            if shape.has_chart:
                meses, casos_prev, tasas_prev = self.engine.get_prevalencia_mensual(eps='EPS FAMILIAR')
                update_chart_xml(shape.chart, series_values=[casos_prev, tasas_prev])

        s106 = self.prs.slides[105]
        for shape in s106.shapes:
            if shape.has_chart:
                cats, casos, tasas = self.engine.get_distribucion_agrupador(eps='EPS FAMILIAR')
                update_chart_xml(shape.chart, new_categories=cats, series_values=[casos, tasas])


def main():
    parser = argparse.ArgumentParser(description="Generador Automatizado de Informes de Junta Directiva INOOS")
    parser.add_argument("--excel", default="BD pacientes Inoos SEPTIEMBRE 2026 .xlsx", help="Ruta de la base de datos Excel")
    parser.add_argument("--template", default="template_junta.pptx", help="Ruta de la plantilla PowerPoint")
    parser.add_argument("--output", default="Informe_Junta_Directiva_Generado.pptx", help="Ruta de salida del informe PPTX")
    parser.add_argument("--mes", default="Septiembre", help="Mes de corte del informe (ej. Septiembre)")
    parser.add_argument("--ano", default=2026, type=int, help="Año de corte del informe (ej. 2026)")
    
    args = parser.parse_args()
    
    generador = GeneradorInformeJunta(
        excel_path=args.excel,
        template_path=args.template,
        output_path=args.output,
        mes_corte=args.mes,
        ano_corte=args.ano
    )
    generador.generar()

if __name__ == "__main__":
    main()
