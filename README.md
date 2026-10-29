# INOOS | Plataforma de Inteligencia Clínica & Informes de Junta Directiva

[![Python Version](https://img.shields.io/badge/Python-3.13%2B-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/Framework-Flask%203.1-green.svg)](https://flask.palletsprojects.com/)
[![Charts](https://img.shields.io/badge/Charts-Chart.js%204.4-orange.svg)](https://www.chartjs.org/)
[![License](https://img.shields.io/badge/License-Proprietary%20%2F%20INOOS-purple.svg)]()

Plataforma integral de ingeniería de datos y visualización analítica oncológica desarrollada para el **Instituto Nacional de Oncología y Oportunidad en Salud (INOOS)**. Permite transformar bases de datos clínicas complejas en informes ejecutivos automatizados en PowerPoint para la Junta Directiva y en un tablero de mando interactivo en tiempo real con benchmarking oficial de la **Cuenta de Alto Costo (CAC)** y el **Instituto Nacional de Cancerología (INC)**.

---

## 🚀 Módulos Principales

### 1. 📊 Tablero de Control e Inteligencia Clínica (`/dashboard`)
* **Métricas 100% calculadas desde la base de datos**: Casos filtrados, prevalencia e incidencia, oportunidad diagnóstica a primera consulta (mediana en días y porcentaje $\le 15$ días), diagnóstico en estadios tempranos (I-II vs III-IV) y porcentaje de cánceres priorizados CAC.
* **Filtros Multidimensionales en Tiempo Real**: Filtrado cruzado por Aseguradora (EPS), Agrupador Tumoral (25 neoplasias), Régimen de Afiliación (Contributivo / Subsidiado / Especial / Particular), Estadio Clínico, Sexo, Rango de Edad y Departamento.
* **Benchmarking Oficial CAC & INC**: Contraste de indicadores de calidad institucional frente a los estándares de consenso de Colombia:
  * Diagnóstico temprano en estadios I y II (Meta CAC $\ge 60\%$).
  * Oportunidad diagnóstica a primera consulta (Meta CAC $\le 15$ días).
  * Oportunidad en reporte anatomopatológico (Estándar INC $\le 10$ días).
  * Distribución de positividad de biomarcador HER2 en cáncer de mama (Rango esperado INC $15\% - 25\%$).
  * Análisis de equidad en salud por régimen de afiliación.
* **Explorador Clínico de Casos**: Vista tabular navegable con exportación de la cohorte filtrada en formato CSV.
* **100% Offline**: Librerías visuales (`chart.umd.min.js`) empaquetadas localmente, sin dependencia de internet ni CDNs externos.

### 2. 📑 Generador Automatizado de Informes de Junta Directiva (`/`)
* **Ingesta y Validación de Datos**: Procesa archivos Excel oncológicos estructurados con más de 60 variables clínicas, sociodemográficas y temporales.
* **Inyección Dinámica en PowerPoint**: Actualiza automáticamente métricas, tablas, textos de análisis y gráficos nativos en el archivo maestro de PowerPoint (`template_junta.pptx`).
* **Sincronización de Mes y Año**: Detección inteligente del corte clínico en el nombre del archivo para generar reportes mensuales consistentes (Septiembre, Agosto, etc.).

---

## ⚡ Arquitectura y Rendimiento

* **Caché Binario Indexado en Disco (`.cache/`)**: Las bases de datos clínicas se normalizan e indexan automáticamente en un caché binario serializado. La carga pasa de **~5.8 segundos a 0.10 segundos (53x más rápido)**.
* **Caché en Memoria RAM**: Las consultas de filtros en el tablero responden en **< 1 milisegundo**.
* **Precalentamiento al Inicio**: El servidor web precalienta los índices analíticos al arrancar para garantizar tiempos de respuesta inmediatos.
* **Sanitización Estricta de JSON (RFC 8259)**: Protección contra valores `NaN` en registros incompletos, serializándolos como `null` estándar para evitar excepciones en el navegador.

---

## 🔒 Confidencialidad y Protección de Datos

> **IMPORTANTE**: En estricto cumplimiento de la normativa colombiana de **Habeas Data y Protección de Datos Personales (Ley 1581 de 2012 y normas de Historia Clínica)**, las bases de datos de pacientes reales (`.xlsx`, `.xls`, `.csv`), las carpetas de subida temporal (`uploads/`) y los cachés de pacientes (`.cache/`) están explícitamente **excluidos del control de versiones** a través del archivo `.gitignore`.
>
> Cada usuario debe incorporar su propia base de datos institucional en la carpeta raíz o cargarla a través de la interfaz web.

---

## 📦 Requisitos del Sistema

* **Python 3.10 o superior** (probado y optimizado en Python 3.13).
* **Git** instalado en el sistema.
* Navegador web moderno (Chrome, Edge, Firefox).

---

## 🛠️ Instalación y Puesta en Marcha

### 1. Clonar el Repositorio
```bash
git clone https://github.com/TU_USUARIO/TU_REPOSITORIO.git
cd TU_REPOSITORIO
```

### 2. Crear y Activar Entorno Virtual
En Windows (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
En Linux / macOS:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instalar Dependencias
```bash
pip install -r requirements.txt
```

### 4. Colocar la Base de Datos Clínica
Copia el archivo Excel del mes correspondiente en la carpeta raíz del proyecto, por ejemplo:
```text
BD pacientes Inoos SEPTIEMBRE 2026 .xlsx
```
*(También puedes cargar el archivo directamente desde la interfaz web en la pantalla inicial).*

### 5. Iniciar la Aplicación

#### Opción A (Recomendada en Windows - 1 Clic):
Haz doble clic en el archivo:
```text
iniciar_aplicacion.bat
```
O ejecuta desde PowerShell:
```powershell
.\iniciar_aplicacion.ps1
```

#### Opción B (Línea de Comandos):
```bash
python app.py --port 5050 --open
```

La aplicación se ejecutará por defecto en el puerto **5050** (con auto-asignación a 5051, 5052 si el puerto está ocupado por otros servicios):
* **Generador PPTX**: [http://localhost:5050/](http://localhost:5050/)
* **Tablero de Control**: [http://localhost:5050/dashboard](http://localhost:5050/dashboard)

---

## 📂 Estructura del Proyecto

```text
├── app.py                         # Servidor Flask principal y API REST
├── dashboard_engine.py            # Motor analítico, cálculo de KPIs y benchmarking CAC/INC
├── data_engine.py                 # Motor SSOT de lectura, normalización y caché de datos
├── generador_informe_junta.py     # Motor de generación e inyección en plantilla PowerPoint
├── template_junta.pptx            # Plantilla maestra de diapositivas para Junta Directiva
├── requirements.txt               # Dependencias de Python fijadas
├── .gitignore                     # Protección de datos de pacientes, cachés y binarios
├── iniciar_aplicacion.bat         # Lanzador rápido para Windows CMD
├── iniciar_aplicacion.ps1         # Lanzador para Windows PowerShell
├── templates/
│   ├── index.html                 # Vista del Generador PPTX
│   └── dashboard.html             # Vista del Tablero de Inteligencia Clínica
├── static/
│   ├── css/
│   │   ├── style.css              # Estilos compartidos y tema oscuro INOOS
│   │   └── dashboard.css          # Estilos del Tablero y ribbon de filtros
│   └── js/
│       ├── main.js                # Lógica del generador PPTX
│       ├── dashboard.js           # Lógica interactiva del Tablero y filtros
│       └── chart.umd.min.js       # Librería Chart.js 4.4 local para uso offline
└── uploads/                       # Directorio para archivos cargados por el usuario
```

---

## 👥 Créditos y Autoría

* **Organización**: Instituto Nacional de Oncología y Oportunidad en Salud (INOOS)
* **Desarrollo**: Área de Analítica de Datos & Dirección Médica
* **Año**: 2026
