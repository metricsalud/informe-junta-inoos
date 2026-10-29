# INFORME DE AUDITORÍA E INGENIERÍA INVERSA: INFORME DE JUNTA MENSUAL INOOS

**Fecha de Corte:** Septiembre 2026  
**Documento Fuente Excel:** `BD pacientes Inoos SEPTIEMBRE 2026 .xlsx` (11.6 MB, 16 hojas)  
**Documento Objetivo PPTX:** `Junta Directiva Septiembre 2026 GENERAL COMPLETA.pptx` (115 diapositivas)  
**Autor:** Clinical Data Engineering & Senior Python Developer  

---

## 1. RESUMEN EJECUTIVO Y ARQUITECTURA DE DATOS

El análisis exhaustivo de ingeniería inversa realizado sobre el archivo Excel y la presentación de PowerPoint demostró con precisión matemática cómo se construye el informe de junta directiva.

### 1.1 Estructura del Archivo Excel (`BD pacientes Inoos SEPTIEMBRE 2026 .xlsx`)

El archivo contiene **16 hojas**, las cuales cumplen roles específicos dentro de la arquitectura de reportería clínica:

1. **Bases Crudas de Pacientes:**
   - `base completa (modificada)`: **9,735 registros clínicos**, 63 columnas. Es la **Única Fuente de la Verdad (SSOT)** para toda la cohorte activa de cáncer a corte Septiembre 2026. Representa cada neoplasia/tumor de los 9,316 pacientes únicos (algunos pacientes tienen neoplasias primarias múltiples según norma CAC).
   - `base completa sin duplicados`: 9,137 registros filtrados por documento único sin neoplasias secundarias.
   - `FALLECIDOS`: 577 registros de pacientes oncológicos fallecidos.
   - `CAMBIOS DE EPS`: 314 registros de traslados/cambios de asegurador.
   - `base completa (fallecidos)`: 135 registros de fallecidos con trazabilidad por regional.

2. **Tablas Dinámicas y Agregaciones Clínicas:**
   - `incidencia`: Resumen de casos por año/mes de ingreso y año/mes de diagnóstico por EPS. Total general: 9,735 casos (1,349 en 2026).
   - `Ingreso`: Resumen de evolución de cohorte por EPS (población inicial, corte actual, variación porcentual).
   - `Prevalencia`: Conteo y tasas por 100,000 habitantes de cada tipo de cáncer (`Agrupador`) para Emssanar, Salud Total, Sanitas, Fomag y Familiar.
   - `Poblacion`: Denominadores poblacionales oficiales de asegurados por EPS.
   - `Escalera`: Matriz de oportunidad diagnóstica vs ingreso general y por EPS (matriz de escalonamiento mensual).
   - `Hoja1`: Matrices de oportunidad de ingreso para Sanitas (cols 1-13), Emssanar (cols 16-30) y Salud Total (cols 32-44).
   - `Intencion de tto`: Conteo de objetivos terapéuticos (Curativo, Paliativo, Observación) para Salud Total y otras EPS.
   - `Indicadores`: Histórico mensual de tratamientos (Quimioterapia, Radioterapia, Cirugía), oportunidad de inicio de tratamientos y coberturas de Cuidados Paliativos (Psicología, Trabajo Social, Dolor, Nutrición), así como indicadores agregados de citas.
   - `Hoja2`: Registro de tutelas, desacatos, derechos de petición e incidentes de Emssanar.
   - `Hoja3`: Indicadores de incidencia y prevalencia de EPS Familiar de Colombia.
   - `TD`: Distribución territorial de usuarios de Emssanar por departamento (Valle vs Cauca) y municipios.

### 1.2 Denominadores Poblacionales y Fórmulas Epidemiológicas

Para el cálculo de **Tasas por 100.000 afiliados**, el sistema utiliza los siguientes denominadores extraídos de la hoja `Poblacion`:

- **Nacional Consolidado:** `623,321` afiliados
- **Emssanar:** `292,704` afiliados
- **Salud Total:** `205,650` afiliados
- **Sanitas EPS:** `90,503` afiliados
- **Fomag:** `25,471` afiliados
- **EPS Familiar de Colombia:** `8,993` afiliados (en PPTX se referencia también `9,592` en láminas de julio)

**Fórmula de Tasa:**

$$\text{Tasa por 100.000} = \left(\frac{\text{Casos en Cohorte}}{\text{Población Afiliada}}\right) \times 100.000$$

*Validación:* En Slide 6, para *Otros tumores de piel* ($2,348$ casos): $(2,348 / 623,321) \times 100,000 = 376.6919$. Coincide exactamente con el valor del PowerPoint.

---

## 2. MAPEO DETALLADO DIAPOSITIVA POR DIAPOSITIVA

### BLOQUE 1: CONSOLIDADO NACIONAL - GESTIÓN CLÍNICA (Slides 1 - 14)

#### Slide 1: Portada

- **Tipo:** Título y Metadatos Institucionales.
- **Contenido:** *Junta Directiva Septiembre 2026*, Presentado por *Dra. Alejandra Sabogal Ortiz, Directora Médica Nacional*.
- **Lógica de Automatización:** Parametrización dinámica de Mes y Año de corte.

#### Slide 2: Separador

- **Tipo:** Título de Sección: *Gestión Clínica - Dirección Médica Nacional - Septiembre 2026*.

#### Slide 3: Historia de Población

- **Elemento:** Gráfico de columnas agrupadas (`Ingresos mensuales año 2024/2026`).
- **Origen Excel:** Hoja `incidencia` (fila 7) y `base completa (modificada)` (`AÑO`, `MES`).
- **Valores Comprobados 2026:** Ene: 126, Feb: 185, Mar: 165, Abr: 165, May: 188, Jun: 158, Jul: 153, Ago: 108, Sep: 101. Total 2026: **1,349 ingresos**.
- **Lógica:** Filtrar `AÑO == 2026`, agrupar por `MES` de la columna `FechadeIngreso.`.

#### Slide 4: Ingreso a la Cohorte 2025 - 2026 (Incidencia)

- **Elemento:** Gráfico combinado de columnas y líneas (`Incidencia INOOS año 2025/2026`).
- **Origen Excel:** `base completa (modificada)` (`18FechaconfirmaciónDiagnostico`).
- **Valores Comprobados 2026:** Ene: 55, Feb: 85, Mar: 110, Abr: 134, May: 150, Jun: 123, Jul: 129, Ago: 90, Sep: 87.
- **Lógica:** Casos con año de diagnóstico en 2026 agrupados por mes de diagnóstico. Tasa calculada sobre población nacional (meses 1-4: 597,916; meses 5-9: 623,321).

#### Slide 5: Prevalencia 2026

- **Elemento:** Gráfico de columnas y líneas (`Prevalencia año 2025/2026`).
- **Origen Excel:** Hoja `Ingreso` (filas 6-13) y acumulado de `base completa (modificada)`.
- **Valores Comprobados:** Ene: 8,512, Feb: 8,697, Mar: 8,862, Abr: 9,027, May: 9,215, Jun: 9,373, Jul: 9,526, Ago: 9,634, Sep: **9,735**.
- **Lógica:** Conteo acumulado de pacientes activos al corte de cada mes.

#### Slide 6: Distribución de la Cohorte Total

- **Elemento:** Gráfico de barras (`Distribución de la Cohorte General`).
- **Origen Excel:** `base completa (modificada)` columna `Agrupador` y hoja `Prevalencia`.
- **Valores Comprobados (Top 5):**
  1. *16= Otros tumores de la piel:* 2,348 casos (Tasa: 376.69)
  2. *1= CAC Mama:* 1,851 casos (Tasa: 296.96)
  3. *2= CAC Próstata:* 1,024 casos (Tasa: 164.28)
  4. *3= CAC Cérvix:* 967 casos (Tasa: 155.14)
  5. *4= CAC Colorectal:* 602 casos (Tasa: 96.58)
  - Total general sumado: **9,735 casos** (100% de la cohorte).
- **Lógica:** `df['Agrupador'].value_counts()`.

#### Slide 7: Distribución por Tipo de Cáncer Priorizados

- **Elemento:** 2 Gráficos de barras (Cánceres Priorizados Septiembre 2026 y Septiembre 2025).
- **Origen Excel:** `base completa (modificada)` filtrando `prioridad CAC == 'Cánceres priorizados'`.
- **Valores Comprobados 2026:** Mama: 1,851; Próstata: 1,024; Cérvix: 967; Colorectal: 602; Linfoma No Hodgkin: 252; Estómago: 227; Melanoma: 122; Linfoma Hodgkin: 74; Pulmón: 64; Leucemia Linfocítica: 40; Leucemia Mielocítica: 30.
- **Total Priorizados:** **5,253 casos** (53.96% $\approx$ **54%** del total de la cohorte).

#### Slide 8: Distribución por Tipo de Cáncer No Priorizados

- **Elemento:** 2 Gráficos de barras (No Priorizados Septiembre 2026 y Septiembre 2025).
- **Origen Excel:** `base completa (modificada)` filtrando `prioridad CAC == 'Cánceres no priorizados'`.
- **Valores Comprobados 2026:** Piel: 2,348; Tiroides/Endocrinas: 559; Otros genitales femeninos: 361; Vías urinarias: 220; Otros linfáticos/hematopoyéticos: 214; Digestivos: 139; Otros genitales masculinos: 116; Cavidad bucal: 112; SNC/Encéfalo: 101; Mesoteliales/Blandos: 100; Sitios mal definidos: 95; Respiratorios: 62; Huesos: 32; Secundarios: 23.
- **Total No Priorizados:** **4,482 casos** ($5,253 + 4,482 = 9,735$).

#### Slide 9: Oportunidad Ingreso General (Matriz de Escalonamiento)

- **Elemento:** Tabla bidimensional de contingencia (25 filas $\times$ 13 columnas).
- **Origen Excel:** Hoja `Escalera`, bloque `General` (Columnas 83 a 95).
- **Lógica de Cálculo:**
  - Filas: Año y mes de confirmación diagnóstica (`2024`, `2025`, `ene-26`, `feb-26`, ..., `sep-26`, `Total general`).
  - Columnas: Periodo de ingreso a la cohorte (`2025`, `ene-26`, ..., `sep-26`, `TOTAL`).
  - Total general verificado en tabla: **9,735 registros**.
  - Porcentaje de ingreso oportuno (mismo mes de diagnóstico): promedio **35%**.

#### Slide 10: Porcentaje de Pacientes en Tratamiento 2025/2026

- **Elemento:** Tabla de recuentos mensuales + Gráfico de columnas de porcentaje sobre cohorte.
- **Origen Excel:** Hoja `Indicadores` (consolidado nacional de tratamientos).
- **Tratamientos Evaluados:**
  - *Quimioterapia / Terapia Sistémica:* Septiembre 2026 = 625 pacientes (6.42% de la cohorte).
  - *Radioterapia:* Septiembre 2026 = 60 pacientes (0.62% de la cohorte).
  - *Cirugía Oncológica:* Septiembre 2026 = 201 pacientes (2.06% de la cohorte).
  - *Total en Tratamiento Activo:* Septiembre 2026 = 886 pacientes (9.10% de la cohorte).

#### Slide 11: Oportunidades de Consulta 2025/2026

- **Elemento:** 4 Gráficos de barras con metas:
  1. *Oportunidad de ingreso a modelo de paciente confirmado* (Meta: 1 día; Sep 2026: 1.9 días).
  2. *Oportunidad de consulta Especializada* (Meta: 10 días; Sep 2026: 7.0 días - ¡Cumple!).
  3. *Oportunidad de consulta Subespecializada* (Meta: 15 días; Sep 2026: 9.8 días - ¡Cumple!).
  4. *Oportunidad de ingreso sospechoso* (Meta: 16 días; Sep 2026: 14.0 días - ¡Cumple!).
- **Origen Excel:** Hoja `Indicadores`.

#### Slide 12: Oportunidades de Inicio de Tratamientos 2025/2026

- **Elemento:** 4 Gráficos de barras con metas:
  1. *Oportunidad de Quimioterapia* (Meta: 15 días; Sep 2026: 16.0 días).
  2. *Oportunidad de Procedimientos Quirúrgicos* (Meta: 25 días; Sep 2026: 78.0 días).
  3. *Oportunidad de Radioterapia* (Meta: 16 días; Sep 2026: 35.0 días).
  4. *Oportunidad de Medicamentos Orales* (Meta: 10 días; Sep 2026: 16.0 días).
- **Origen Excel:** Hoja `Indicadores`.

#### Slide 13 y 14: Cuidados Paliativos General 2026

- **Elemento Slide 13:** Tabla de coberturas por prevalencia e incidencia:
  - *Prevalencia a Septiembre 2026:* Psicología 49%, Trabajo Social 55%, Dolor y CP 11%, Nutrición 51%.
  - *Incidencia a Septiembre 2026:* Psicología 75%, Trabajo Social 79%, Dolor y CP 31%, Nutrición 75%.
  - *Cobertura Global Nacional:* **47%** a septiembre 2026.
- **Elemento Slide 14:** Gráfico de evolución acumulada de pacientes atendidos vs tamaño de la cohorte (Cobertura acumulada global: **67.8%** $\approx$ **68%** con 6,461 atendidos de 9,535).
- **Origen Excel:** Hoja `Indicadores`.

---

### BLOQUE 2: CALIDAD, EXPERIENCIA DEL USUARIO Y CALL CENTER (Slides 15 - 34)

#### Slides 15 - 28: Servicio de Atención al Usuario (SAU) / Calidad

- **Fuente Oficial Reportada:** SAU INOOS (corte Agosto 2026 por desfase operativo de encuestas).
- **Slide 15:** Distribución de 934 encuestas aplicadas en agosto (Salud Total: 453, Sanitas: 335, Emssanar: 123, Familiar: 8, Fomag: 5, Otros: 10).
- **Slide 16:** NPS Nacional: 99.7.
- **Slide 17:** QSE Nacional: Satisfacción 4.97 / 5.0, CES 99.4%, FCR 99.6%.
- **Slides 18 - 20:** Desagregación QSE por Regional (Cauca, Tolima, Valle).
- **Slides 21 - 24:** PQRSF Nacional (reclamaciones recibidas, causas por EPS y estados).
- **Slides 25 - 28:** Humanización, PREMS (Amabilidad) y PROMS (Responsabilidad).

#### Slides 29 - 34: Call Center y Central de Referencia

- **Slide 29:** Indicadores Call Center Nacional (Satisfacción llamada, nivel de servicio).
- **Slide 30:** Estados de cita por sede (Atendida, Cancelada, Incumplida) y distribución 1ª Vez vs Control.
- **Slide 31:** Detalle por especialidad médica mensual.
- **Slides 32 - 33:** Disponibilidad de agenda Valle del Cauca y Cauca.
- **Slide 34:** Central de Referencia: 3,953 trámites gestionados a nivel nacional.

---

### BLOQUE 3: SALUD TOTAL (Slides 35 - 54)

- **Slide 35:** Portada Salud Total.
- **Slide 36 (Histórico Ingresos):** Ene: 54, Feb: 67, Mar: 60, Abr: 64, May: 60, Jun: 60, Jul: 55, Ago: 31, Sep: 31. Total 2026: **482 ingresos**.
- **Slide 37 (Población Total):** Prevalencia pasa de 2,093 a **3,173 casos** activos al corte de septiembre 2026.
- **Slide 38 (Incidencia):** Tasa promedio de incidencia calculada sobre 205,650 afiliados.
- **Slide 39 (Pirámide Poblacional):** Cohorte concentrada en 62% entre 56 y 80 años. Distribución bivariada `EDAD` vs `SEXO`.
- **Slide 41 (Distribución Cáncer Salud Total):** Piel: 861; Mama: 591; Próstata: 426; Colorectal: 190; Tiroides: 188; Cérvix: 144; Otros tumores: 97; Vías urinarias: 97.
- **Slides 42 - 43 (Priorizados y No Priorizados):** Mismo desglose filtrado por `11NombreEPS == 'SALUD TOTAL'`.
- **Slide 44 (Oportunidad Ingreso):** Hoja `Hoja1` columnas 32-44. Diagnósticos 2024 acumulados: 2,284; Diagnósticos 2025: 536; Ingresos 2026: 353.
- **Slides 45 - 46 (Oportunidades):** Datos de oportunidad asistencial específicos de Salud Total desde hoja `Indicadores`.
- **Slide 47 (Pacientes en Tratamiento):** Hoja `Indicadores` filas 1-4: Quimioterapia (285 en sep), Radioterapia (15 en sep), Cirugía (68 en sep).
- **Slide 48 (Intención de Tratamiento):** Hoja `Intencion de tto` y columna `41ObejtivoIntervencionMedicaanual`:
  - *Observación o seguimiento:* 1,590 casos (**50.1%**)
  - *Tratamiento Curativo / Paliativo:* 739 casos (**23.3%**)
  - *Observación previa a tratamiento:* 724 casos (**22.8%**)
  - *Otros objetivos:* 120 casos (**3.8%**)
  - Total: **3,173 pacientes** (100% verificado).
- **Slide 49 (Cuidados Paliativos):** Hoja `Indicadores` filas 6-16 y tabla de atenciones efectivas (Dolor: 987 efectivas - 73%; Nutrición: 3,166 efectivas - 83%).
- **Slides 50 - 53:** SAU Salud Total.
- **Slide 54:** Call Center Salud Total: 33,747 citas totales (Atendida: 25,654 - 76%; Cancelada: 5,137 - 15%; Incumplida: 2,956 - 9%).

---

### BLOQUE 4: SANITAS EPS (Slides 55 - 71)

- **Slide 55:** Portada Sanitas.
- **Slide 56 (Histórico Ingresos):** Ene: 24, Feb: 35, Mar: 48, Abr: 32, May: 51, Jun: 38, Jul: 41, Ago: 27, Sep: 32. Total 2026: **328 ingresos**.
- **Slide 57 (Incidencia):** 47% de los ingresos 2026 corresponden a diagnósticos del mismo año.
- **Slide 58 (Prevalencia):** Pasa de 1,452 al inicio a **2,060 casos activos** a septiembre 2026.
- **Slide 59 (Distribución Cáncer Sanitas):** Piel: 553; Mama: 318; Próstata: 224; Cérvix: 215; Tiroides: 160; Colorectal: 130; Otros genitales fem: 73; Linfoma No Hodgkin: 63.
- **Slides 60 - 61 (Priorizados y No Priorizados Sanitas):**
  - Priorizados 2026: Mama 318, Próstata 224, Cérvix 215, Colorectal 130, LNH 63, Estómago 57.
  - No Priorizados 2026: Piel 553, Tiroides 160, Genitales fem 73, Vías urinarias 46, Genitales masc 35.
- **Slides 62 - 63 (Oportunidades):** Datos específicos de oportunidad Sanitas.
- **Slide 64 (Pacientes en Tratamiento):** Quimioterapia 169, Radioterapia 13, Cirugía en cohorte Sanitas.
- **Slide 65 (Oportunidad Ingreso):** Hoja `Hoja1` columnas 1-13 (2,060 casos totales de Sanitas cruzados).
- **Slide 66 (Cuidados Paliativos):** Dolor (556 efectivas - 77%), Nutrición (3,618 efectivas - 78%).
- **Slides 67 - 70:** SAU Sanitas.
- **Slide 71:** Call Center Sanitas: 27,640 citas totales (Atendida: 23,363 - 85%; Cancelada: 2,816 - 10%; Incumplida: 1,461 - 5%).

---

### BLOQUE 5: EMSSANAR (Slides 72 - 91)

- **Slide 72:** Portada Emssanar.
- **Slide 73 (Histórico Ingresos):** Ene: 48, Feb: 75, Mar: 50, Abr: 55, May: 74, Jun: 57, Jul: 54, Ago: 40, Sep: 38. Total 2026: **491 ingresos**.
- **Slide 74 (Incidencia):** Casos diagnosticados sobre población Emssanar (292,704 afiliados).
- **Slide 75 (Distribución Cáncer e Incidencia/Prevalencia):**
  - Gráfico 1 (Incidencia 2026): Piel 77, Mama 77, Cérvix 45, Colorectal 35, Próstata 26.
  - Gráfico 2 (Prevalencia Cohorte Total): Mama 915, Piel 884, Cérvix 588, Próstata 343, Colorectal 268, Tiroides 204.
  - Regionales (Hoja `TD`): Valle del Cauca: **3,198** usuarios; Cauca: **1,038** usuarios.
- **Slide 76 (Prevalencia):** Pasa de 3,655 a **4,303 casos activos** a septiembre 2026.
- **Slide 77 (Priorizados y No Priorizados Emssanar):** Conteo exacto por `Agrupador`.
- **Slide 78 (Pacientes en Tratamiento):** Quimioterapia 171, Radioterapia 32, Cirugía en Emssanar.
- **Slide 79 (Oportunidad Ingreso):** Hoja `Hoja1` columnas 16-30 (Total: 4,303 casos).
- **Slides 80 - 81 (Oportunidades):** Métricas de oportunidad de Emssanar.
- **Slide 82 - 83 (Cuidados Paliativos):** Dolor (1,033 efectivas - 72%), Nutrición (3,314 efectivas - 81%).
- **Slide 84 (Hospitalizaciones Emssanar):** Desglose Valle vs Cauca por causas de dolor y estancia media.
- **Slides 85 - 88:** SAU Emssanar.
- **Slide 89 (Tutelas e Incidentes):** Hoja `Hoja2`: 192 acciones judiciales en 2026 (Quimioterapia 66, Cirugías 44, Consultas 40, Imágenes 13).
- **Slide 90 (Call Center):** 9,190 citas registradas en hoja `Indicadores` (Atendida: 7,259 - 79%; Cancelada: 1,165 - 13%; Incumplida: 766 - 8%).
- **Slide 91 (Represa PGP):** Proyección de ejecuciones de represa asistencial.

---

### BLOQUE 6: FOMAG Y FAMILIAR DE COLOMBIA (Slides 92 - 115)

- **Slides 92 - 97 (FOMAG):**
  - Población: 25,471 afiliados.
  - Cohorte total: **118 casos**.
  - Distribución: Piel 31, Próstata 22, Mama 19, Colorectal 10, Estómago 5.
  - Call Center (Slide 102): 568 citas (Atendida: 472 - 83%; Cancelada: 73 - 13%; Incumplida: 23 - 4%).
- **Slides 103 - 109 (FAMILIAR DE COLOMBIA):**
  - Población: 8,993 / 9,592 afiliados.
  - Cohorte total: **74 casos**.
  - Distribución: Piel 16, Cérvix 14, Mama 9, Próstata 8, Genitales fem 6.
  - Call Center (Slide 114): 286 citas (Atendida: 213 - 74%; Cancelada: 49 - 17%; Incumplida: 24 - 8%).
- **Slide 115:** Cierre institucional.

---

## 3. HALLAZGOS CRÍTICOS Y DISCREPANCIAS NUMÉRICAS AUDITADAS

1. **Concordancia Matemática 100% en el Núcleo Clínico:**
   - La totalidad de los números de cohorte, prevalencia, incidencia, distribución tumoral y tasas por 100,000 en las láminas de Gestión Clínica Nacional, Salud Total, Sanitas, Emssanar, Fomag y Familiar concuerdan **sin una sola discrepancia** con `base completa (modificada)`.

2. **Manejo de Variaciones Tipográficas en Variables Categóricas:**
   - En la variable `41ObejtivoIntervencionMedicaanual`, el Excel contenía 3 categorías para tratamiento curativo debido a erratas manuales (`2= Ofrecer tratamiento curativo...` [720], `2= Ofrecer tratamiento curativo o paliativo...` [16], `2= Orecer tratamiento curativo...` [3]). La presentación sumó las 3 variantes para obtener los **739 casos** (23.3%). El motor automatizado debe estandarizar esto mediante regex.

3. **Columnas Duplicadas en el Archivo Excel:**
   - Existen nombres idénticos en distintas posiciones: Columna 2 (`AÑO` de ingreso) vs Columna 32 (`Año` de diagnóstico), y Columna 0 (`6NúmeroIdentificación`) vs Columna 9. El motor en Python debe emplear un desambiguador automático de columnas posicional.

4. **Desfase Temporal Declarado en Secciones No Clínicas:**
   - Mientras las láminas clínicas están al corte estricto de **Septiembre 2026**, las secciones de Encuestas SAU y PQRSF registran corte de **Julio o Agosto 2026** debido al ciclo de recolección de encuestas post-servicio. El generador modular conservará estas fuentes y actualizará las fechas correspondientes dinámicamente.
